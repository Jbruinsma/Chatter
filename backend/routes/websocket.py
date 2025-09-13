from typing import Annotated, Dict

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from backend.instances import CHAT_MANAGER

from backend.utils.user_utils import find_user, user_uuid_to_username
from backend.utils.chat_utils import create_chat, find_direct_chat_with_user, add_user_to_chat, find_chat
from backend.utils.database_utils import save_all_databases
from backend.utils.formatting import format_message_dict_for_json

from random import randint

router = APIRouter()

ChatId = Annotated[str, "chat_id"]
UserUUID = Annotated[str, "user_uuid"]

active_user_connections: Dict[str, WebSocket] = {}
active_chat_connections: Dict[ChatId, Dict[UserUUID, WebSocket]] = {}

async def add_user_to_active_connections(user_uuid: UserUUID, websocket: WebSocket) -> None:
    active_user_connections[user_uuid] = websocket

async def remove_user_from_active_connections(user_uuid: str):
    active_user_connections.pop(user_uuid, None)

async def attach_user_to_chat(chat_id: ChatId, user_uuid: UserUUID) -> None:
    user_websocket: WebSocket | None = get_user_connection(user_uuid)
    if user_websocket is None:
        return
    ensure_chat_bucket(chat_id)
    active_chat_connections[chat_id][user_uuid] = user_websocket

async def detach_user_from_chat(chat_id: ChatId, user_uuid: UserUUID) -> None:
    chat_map = active_chat_connections.get(chat_id)
    if not chat_map:
        return
    chat_map.pop(user_uuid, None)
    if not chat_map:
        active_chat_connections.pop(chat_id, None)

def get_user_connection(user_uuid: UserUUID) -> WebSocket | None:
    return active_user_connections.get(user_uuid)

def ensure_chat_bucket(chat_id: ChatId) -> None:
    if chat_id not in active_chat_connections:
        active_chat_connections[chat_id] = {}

def add_notification(user_obj, message, notification_type, extra_data=None):
    user_obj.add_notification(message, notification_type, extra_data)
    save_all_databases()

async def send_error(user_websocket, user_obj, operation, code, message, extra_data=None):
    add_notification(user_obj, message, "error")
    await send_websocket_error(user_websocket, operation, code, message, extra_data)

async def send_acknowledgement(user_websocket, user_obj, operation, message,extra_data=None):
    add_notification(user_obj, message, "success", extra_data)
    await send_websocket_acknowledgement(user_websocket, operation, extra_data)

async def handle_chat_creation(request_websocket: WebSocket, current_user_uuid: str, new_chat_info):
    if 'data' in new_chat_info:
        new_chat_info = new_chat_info.get("data", {})

    owner_uuid = new_chat_info.get("owner_id")
    if owner_uuid != current_user_uuid:
        await send_websocket_error(request_websocket, "create_chat", "invalid_owner_id", "Invalid owner ID")
        return

    owner_status, owner_obj = find_user(owner_uuid)
    if not owner_status or owner_obj is None:
        await send_websocket_error(request_websocket, "create_chat", "invalid_owner_id", "Invalid owner ID")
        return

    participant_ids = new_chat_info.get("participant_ids", [])
    if not participant_ids:
        await send_error(request_websocket, owner_obj, "create_chat", "missing_participant_ids", "Failed Creating Chat: Missing participant IDs")
        return

    chat_name = new_chat_info.get("chat_name", "")
    chat_cover = new_chat_info.get("chat_cover", "")
    chat_type = new_chat_info.get("chat_type", "")

    if len(participant_ids) == 2:
        chat_type = "direct"
        for participant_uuid in participant_ids:
            if participant_uuid != owner_uuid:
                direct_chat_exists, direct_chat_id = find_direct_chat_with_user(owner_uuid, participant_uuid)
                if direct_chat_exists:
                    await send_websocket_error(request_websocket, "create_chat", "direct_chat_exists", "Direct chat already exists", {"chat_id": direct_chat_id})
                    return

    participant_permissions = new_chat_info.get("participant_permissions", {})
    if not participant_permissions or set(participant_permissions.keys()) != set(participant_ids):
        await send_error(request_websocket, owner_obj, "create_chat", "invalid_participant_permissions", "Failed Creating Chat: Invalid participant permissions")
        return

    try:

        new_chat_id, new_chat_obj = create_chat(
            chat_name= chat_name,
            chat_cover=chat_cover,
            owner_id=owner_uuid,
            participant_ids=participant_ids,
            participant_permissions=participant_permissions,
            chat_type=chat_type
        )

        new_chat_obj.add_system_message(system_message= f"Chat created by @{user_uuid_to_username(owner_uuid)}")
        save_all_databases()

        for participant_uuid in list(new_chat_obj.participants) + list(new_chat_obj.invited_users):
            await attach_user_to_chat(new_chat_id, participant_uuid)

        await broadcast_to_chat(new_chat_id,{
            "operation": "create_chat",
            "chatId": new_chat_id
        })

        if chat_type == "direct":
            message = f"Direct chat between @{user_uuid_to_username(participant_ids[0])} and @{user_uuid_to_username(participant_ids[1])} created successfully."
        else:
            message = f"Chat '{new_chat_obj.chat_name}' created successfully."

        message = f"Chat '{new_chat_obj.chat_name}' created successfully."
        await send_acknowledgement(request_websocket, owner_obj, "create_chat_confirmation", message, {
            "chatId": new_chat_id,
            "message": message
        })

    except Exception as e:
        print(f"Error creating chat: {e}")
        await send_error(request_websocket, owner_obj, "create_chat", "error", "Error creating chat", {"detail": str(e)})

async def handle_direct_chats(request_websocket: WebSocket, user_uuid: UserUUID, chat_info: dict):
    target_user_uuid = chat_info.get("target_user_id")
    if not target_user_uuid:
        await send_websocket_error(request_websocket, "direct_chat", "missing_target_user_id", "Missing target user ID")
        return

    target_user_status, target_user_obj = find_user(target_user_uuid)
    if not target_user_status or target_user_obj is None:
        await send_websocket_error(request_websocket, "direct_chat", "invalid_target_user_id", "Invalid target user ID")
        return

    chat_status, chat_obj = find_direct_chat_with_user(user_uuid, target_user_uuid)
    if chat_status and chat_obj is not None:
        print("DIRECT CHAT EXISTS")
        return {
            "chatId": chat_obj.chat_id
        }
    else:
        print("DIRECT CHAT DOES NOT EXIST")

async def handle_new_message(request_websocket: WebSocket, message_info: dict):
    chat_id = message_info.get("chat_id")
    if not chat_id:
        await send_websocket_error(request_websocket, "send_message", "missing_chat_id", "Missing chat ID")
        return

    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        await send_websocket_error(request_websocket, "send_message", "invalid_chat_id", "Invalid chat ID")

    ensure_chat_bucket(chat_id)
    chat_obj.add_message(message_info)
    save_all_databases()

    await broadcast_to_chat(chat_id, {
        "operation": "receive_message",
        "messageInfo": format_message_dict_for_json(**message_info),
        "hasUnreadMessages": True
    })

    await send_websocket_acknowledgement(request_websocket, "message_delivered", {
        "chatId": chat_id,
        "messageId": message_info.get("message_id")
    })

async def handle_chat_leave(request_websocket: WebSocket, user_uuid: UserUUID, exit_event_info: dict):
    chat_id = exit_event_info.get("chat_id")
    if not chat_id:
        await send_websocket_error(request_websocket, "leave_chat", "missing_chat_id", "Missing chat ID")
        return

    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        await send_websocket_error(request_websocket, "leave_chat", "invalid_user_id", "Invalid user ID")

    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        await send_error(request_websocket, user_obj, "leave_chat", "invalid_chat_id", "Error leaving Chat: Invalid chat ID")
    message = f"You left '{chat_obj.chat_name}' successfully."

    if len(chat_obj.participants) == 1:

        try:

            chat_invited_users = tuple(chat_obj.invited_users)

            for participant_uuid in chat_invited_users:

                invitee_status, invitee_obj = find_user(participant_uuid)
                if not invitee_status or invitee_obj is None: continue

                await broadcast_to_user_in_chat(chat_id, participant_uuid, {
                    "operation": "deleted_chat",
                    "chatId": chat_id
                })

                chat_obj.invited_users.remove(participant_uuid)
                invitee_obj.chat_ids["requests"].discard(chat_id)
                await detach_user_from_chat(chat_id, participant_uuid)

            user_obj.chat_ids["main"].discard(chat_id)
            await detach_user_from_chat(chat_id, user_uuid)

            CHAT_MANAGER.delete_chat(chat_id)
            save_all_databases()

            await send_acknowledgement(request_websocket, user_obj, "leave_chat_confirmation", message, {
                "chatId": chat_id,
                "message": message
            })

        except Exception as e:
            await send_error(request_websocket, user_obj, "leave_chat", "error", f"Error leaving chat: (Internal Error) {str(e)}")

        return

    is_owner = chat_obj.owner_id == user_uuid

    chat_obj.participants.discard(user_uuid)
    chat_obj.participant_permissions.pop(user_uuid, None)
    user_obj.chat_ids["main"].discard(chat_id)
    chat_obj.add_system_message(system_message= f"@{user_uuid_to_username(user_uuid)} left")

    await broadcast_to_chat(chat_id, {
        "operation": "receive_message",
        "messageInfo": chat_obj.last_message_to_dict(),
        "hasUnreadMessages": True
    })

    if is_owner:
        participant_ids_list = list(chat_obj.participants)
        random_new_owner_index = randint(0, len(participant_ids_list) - 1)
        new_owner_id = participant_ids_list[random_new_owner_index]
        chat_obj.owner_id = new_owner_id
        chat_obj.participant_permissions[new_owner_id]["can_edit"] = True
        chat_obj.add_system_message(system_message= f"@{user_uuid_to_username(new_owner_id)} has been made owner")

        await broadcast_to_chat(chat_id, {
            "operation": "receive_message",
            "messageInfo": chat_obj.last_message_to_dict(),
            "hasUnreadMessages": True
        })

    await detach_user_from_chat(chat_id, user_uuid)

    save_all_databases()

    await send_acknowledgement(request_websocket, user_obj, "leave_chat_confirmation", message, {
        "chatId": chat_id,
        "message": message
    })

async def handle_read_receipt(request_websocket: WebSocket, user_uuid: UserUUID, read_receipt_info: dict):
    chat_id = read_receipt_info.get("chat_id")
    if not chat_id:
        await send_websocket_error(request_websocket, "read_receipt", "missing_chat_id", "Missing chat ID")
        return

    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        await send_websocket_error(request_websocket, "read_receipt", "invalid_chat_id", "Invalid chat ID")


    chat_obj.unread_messages_by.discard(user_uuid)

    save_all_databases()

    await send_websocket_acknowledgement(request_websocket, "read_receipt", {
        "chatId": chat_id,
        "hasUnreadMessages": False
    })

async def handle_typing_receipt():
    pass

async def handle_chat_update(request_websocket: WebSocket, user_uuid: UserUUID, chat_update_info: dict):

    chat_updates = chat_update_info.get("changes", {})
    chat_id = chat_update_info.get("chat_id")

    if chat_id is None:
        await send_websocket_error(request_websocket, "update_chat", "missing_chat_id", "Internal Error: Missing chat ID")
        return

    updated_chat_cover = chat_updates.get('chat_cover', None)
    updated_chat_name = chat_updates.get('chat_name', None)
    added_participant_ids_list = chat_updates.get('added_participant', [])
    removed_participant_ids_list = chat_updates.get('removed_participant', [])
    updated_permissions = chat_updates.get('participant_permissions', {})
    uninvited_users = chat_updates.get('uninvited_ids', [])

    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        await send_websocket_error(request_websocket, "update_chat", "invalid_user_id", "Invalid user ID")
        return

    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        await send_websocket_error(request_websocket, "update_chat", "invalid_chat_id", "Invalid chat ID")
        return
    error_message_base = f"Error updating {chat_obj.chat_name}: "
    success_message_base = f"Successfully updated {chat_obj.chat_name}: "

    ensure_chat_bucket(chat_id)

    try:

        if updated_chat_cover: chat_obj.chat_cover = updated_chat_cover
        if updated_chat_name: chat_obj.chat_name = updated_chat_name

        if len(removed_participant_ids_list) > 0:
            for participant_uuid in removed_participant_ids_list:
                user_status, user_obj = find_user(participant_uuid)
                if not user_status or user_obj is None: continue
                if participant_uuid in chat_obj.participants:
                    chat_obj.participants.remove(participant_uuid)
                    chat_obj.add_system_message(system_message= f"@{user_uuid_to_username(participant_uuid)} has been removed by @{user_uuid_to_username(user_uuid)}")
                    await broadcast_to_chat(chat_id, {
                        "operation": "send_message",
                        "MessageInfo": format_message_dict_for_json(chat_obj.last_message_to_dict()),
                        "hasUnreadMessages": True
                    })
                if chat_obj.chat_id in user_obj.chat_ids["main"]: user_obj.chat_ids["main"].remove(chat_id)
                if participant_uuid in chat_obj.invited_users: chat_obj.invited_users.remove(participant_uuid)

        unadded_users = []

        if len(added_participant_ids_list) > 0:
            for participant_uuid in added_participant_ids_list:
                user_status, user_obj = find_user(participant_uuid)
                if not user_status or user_obj is None:
                    unadded_users.append(user_uuid_to_username(participant_uuid))
                    continue
                participant_permissions = updated_permissions.get(participant_uuid, {})
                add_status: bool = add_user_to_chat(chat_obj= chat_obj, user_obj= user_obj, permissions= participant_permissions)
                if add_status:
                    chat_obj.add_system_message(system_message= f"@{user_uuid_to_username(participant_uuid)} has been added by @{user_uuid_to_username(user_uuid)}")
                    await broadcast_to_chat(chat_id, {
                        "operation": "send_message",
                        "MessageInfo": chat_obj.last_message_to_dict(),
                        "hasUnreadMessages": True
                    })
                    await attach_user_to_chat(chat_id, participant_uuid)

        if len(updated_permissions) > 0:
            for participant_uuid in updated_permissions.keys():
                if participant_uuid in removed_participant_ids_list or participant_uuid in added_participant_ids_list: continue
                chat_obj.participant_permissions[participant_uuid] = updated_permissions[participant_uuid]

        chat_obj.add_system_message(system_message= f"@{user_uuid_to_username(user_uuid)} made updates to the chat")
        await broadcast_to_chat(chat_id, {
            "operation": "send_message",
            "MessageInfo": chat_obj.last_message_to_dict(),
            "hasUnreadMessages": True
        })

        save_all_databases()

        await broadcast_to_chat(chat_id, {
            "operation": "update_chat",
            "chatId": chat_id
        })

        await send_acknowledgement(request_websocket, user_obj, "update_chat_confirmation", success_message_base, {
            "chatId": chat_id,
            "message": success_message_base + "Chat updated successfully.",
            "unaddedUsers": unadded_users
        })

    except Exception as e:

        await send_error(request_websocket, user_obj, "update_chat", "update_chat_error", error_message_base + str(e))
        return

async def handle_chat_request_acceptance(request_websocket: WebSocket, user_uuid: UserUUID, acceptance_info: dict):
    chat_id = acceptance_info.get("chat_id")
    if not chat_id:
        await send_websocket_error(request_websocket, "accept_chat_request", "missing_chat_id", "Missing chat ID")
        return

    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        await send_websocket_error(request_websocket, "accept_chat_request", "invalid_chat_id", "Invalid chat ID")

    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        await send_websocket_error(request_websocket, "accept_chat_request", "invalid_user_id", "Invalid user ID")
        return

    if chat_obj.owner_id == user_uuid:
        await send_websocket_error(request_websocket, "accept_chat_request", "invalid_chat_id", "Cannot accept request from chat owner")

    if chat_id not in user_obj.chat_ids["requests"]:
        await send_websocket_error(request_websocket, "accept_chat_request", "invalid_chat_id", "User not invited to chat")
        return
    if chat_id in user_obj.chat_ids["main"]:
        await send_websocket_error(request_websocket, "accept_chat_request", "invalid_chat_id", "User already in chat")
        return

    chat_participant_ids_list = list(chat_obj.participants)
    chat_invited_users_list = list(chat_obj.invited_users)
    chat_participant_permissions_dict = chat_obj.participant_permissions

    if user_uuid not in chat_invited_users_list:
        await send_websocket_error(request_websocket, "accept_chat_request", "invalid_chat_id", "User not invited to chat")
        return
    if user_uuid in chat_participant_ids_list:
        await send_websocket_error(request_websocket, "accept_chat_request", "invalid_chat_id", "User already in chat")
        return

    chat_obj.participants.add(user_uuid)
    chat_obj.invited_users.discard(user_uuid)

    if user_uuid not in chat_participant_permissions_dict:
        chat_obj.participant_permissions[user_uuid] = {"can_edit": False}

    chat_obj.add_system_message(system_message= f"@{user_uuid_to_username(user_uuid)} has accepted the request to join the chat")
    await broadcast_to_chat(chat_id, {
        "operation": "send_message",
        "MessageInfo": chat_obj.last_message_to_dict(),
        "hasUnreadMessages": True
    })

    user_obj.chat_ids["main"].add(chat_id)
    user_obj.chat_ids["requests"].discard(chat_id)

    ensure_chat_bucket(chat_id)
    save_all_databases()

    await broadcast_to_chat(chat_id, {
        "operation": "update_chat",
        "chatId": chat_id
    })

    success_message = f"You accepted the request to join '{chat_obj.chat_name}'."

    await send_acknowledgement(request_websocket, user_obj, "accept_chat_request", success_message, {
        "chatId": chat_id,
        "message": "Chat request accepted successfully.",
    })

async def handle_chat_request_decline(request_websocket: WebSocket, user_uuid: UserUUID, acceptance_info: dict):
    chat_id = acceptance_info.get("chat_id")
    if not chat_id:
        await send_websocket_error(request_websocket, "decline_chat_request", "missing_chat_id", "Missing chat ID")
        return

    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        await send_websocket_error(request_websocket, "decline_chat_request", "invalid_chat_id", "Invalid chat ID")

    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        await send_websocket_error(request_websocket, "decline_chat_request", "invalid_user_id", "Invalid user ID")
        return

    if chat_obj.owner_id == user_uuid:
        await send_websocket_error(request_websocket, "decline_chat_request", "invalid_chat_id","You are the chat owner.")
        return

    if chat_id not in user_obj.chat_ids["requests"]:
        await send_websocket_error(request_websocket, "decline_chat_request", "invalid_chat_id","User not invited to chat")
        return
    if chat_id in user_obj.chat_ids["main"]:
        await send_websocket_error(request_websocket, "decline_chat_request", "invalid_chat_id", "User already in chat")
        return

    chat_participant_ids_list = list(chat_obj.participants)
    chat_invited_users_list = list(chat_obj.invited_users)
    chat_participant_permissions_dict = chat_obj.participant_permissions

    if user_uuid not in chat_invited_users_list:
        await send_websocket_error(request_websocket, "decline_chat_request", "invalid_chat_id", "User not invited to chat")
        return
    elif user_uuid in chat_participant_ids_list:
        await send_websocket_error(request_websocket, "decline_chat_request", "invalid_chat_id", "User already in chat")
        return

    chat_obj.invited_users.discard(user_uuid)
    user_obj.chat_ids["requests"].discard(chat_id)
    if user_uuid in chat_participant_permissions_dict:
        chat_obj.participant_permissions.pop(user_uuid, None)

    ensure_chat_bucket(chat_id)
    detach_user_from_chat(chat_id, user_uuid)

    save_all_databases()
    await send_websocket_acknowledgement(request_websocket, "decline_chat_request", {
        "chatId": chat_id,
        "message": "Chat request declined successfully.",
    })

    await broadcast_to_chat(chat_id, {
        "operation": "update_chat",
        "chatId": chat_id,
    })

async def handle_profile_update(request_websocket: WebSocket, user_uuid: UserUUID):
    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        await send_websocket_error(request_websocket, "update_profile", "invalid_user_id", "Invalid user ID")
        return

    main_chat_ids = list(user_obj.chat_ids["main"])
    request_chat_ids = list(user_obj.chat_ids["requests"])

    for chat_id in main_chat_ids:
        await broadcast_to_chat(chat_id, {
            "operation": "update_chat",
            "chatId": chat_id
        })

    for chat_id in request_chat_ids:
        await broadcast_to_chat(chat_id, {
            "operation": "update_chat",
        })

    save_all_databases()
    await send_websocket_acknowledgement(request_websocket, "success", {
        "message": "Profile updated successfully.",
    })

async def handle_notification(notification_info: dict):
    recipient_uuid = notification_info.get('recipient_uuid')
    frontend_notification_payload = notification_info.get('frontend_notification_payload')

    if recipient_uuid is None or frontend_notification_payload is None:
        print("Notification info is missing required fields.")
        return

    recipient_status, recipient_obj = find_user(recipient_uuid)
    if not recipient_status or recipient_obj is None:
        print(f"Recipient {recipient_uuid} does not exist.")
        return

    await broadcast_to_user_out_of_chat(recipient_uuid, {
        "operation": "notification",
        "notification": frontend_notification_payload
    })

async def send_websocket_error(websocket: WebSocket, operation: str, code: str, message: str, extra: dict | None = None) -> None:
    payload = {"type": "error", "operation": operation, "code": code, "message": message}
    if extra:
        payload["data"] = extra
    await websocket.send_json(payload)

async def send_websocket_acknowledgement(websocket: WebSocket, operation: str, extra: dict | None = None) -> None:
    payload = {"type": "acknowledgement", "operation": operation}
    if extra:
        payload["data"] = extra
    await websocket.send_json(payload)

async def broadcast_to_chat(chat_id: ChatId, payload: dict):
    chat_map = active_chat_connections.get(chat_id, {})
    for user_uuid, websocket in list(chat_map.items()):
        try:
            await websocket.send_json(payload)
        except Exception as e:
            print(f"Error sending message to {user_uuid}: {e}")
            pass

async def broadcast_to_user_in_chat(chat_id: ChatId, user_uuid: UserUUID, payload: dict):
    chat_map = active_chat_connections.get(chat_id, {})
    for user_uuid_to_broadcast, websocket in list(chat_map.items()):
        if user_uuid_to_broadcast == user_uuid:
            print("found user connection to broadcast to.")
            try:
                await websocket.send_json(payload)
                print("sent message to user.")
            except Exception as e:
                print(f"Error sending message to {user_uuid}: {e}")
                pass
            break

async def broadcast_to_user_out_of_chat(user_uuid: UserUUID, payload: dict):
    user_websocket = get_user_connection(user_uuid)
    if user_websocket:
        try:
            await user_websocket.send_json(payload)
        except Exception as e:
            print(f"Error sending message to {user_uuid}: {e}")
            pass

@router.websocket('/{user_uuid}')
async def websocket_endpoint(websocket: WebSocket, user_uuid: UserUUID):
    user_status, user_obj = find_user(user_uuid)

    if not user_status or user_obj is None:
        await websocket.close(1008, "User does not exist.")
        return

    await websocket.accept()
    await add_user_to_active_connections(user_uuid, websocket)

    user_chat_ids = list(user_obj.chat_ids.get("main", set()) | user_obj.chat_ids.get("requests", set()))

    for chat_id in user_chat_ids:
        await attach_user_to_chat(chat_id, user_uuid)

    try:

        while True:
            try:

                incoming_json = await websocket.receive_json()

            except WebSocketDisconnect:
                break

            except Exception as e:
                await send_websocket_error(websocket, "unknown", "bad_json", "Invalid JSON", {"detail": str(e)})
                continue

            operation = (incoming_json or {}).get("operation")
            data = (incoming_json or {}).get("data") or {}

            if operation == "ping":
                print(f"Received ping from {user_uuid}")
                await send_websocket_acknowledgement(websocket, "pong")

            elif operation == "create_chat":
                print(f"Received create_chat from {user_uuid}")
                await handle_chat_creation(websocket, user_uuid, data)

            elif operation == "find_or_create_direct_chat":
                print(f"Received find_or_create_direct_chat from {user_uuid}")
                await handle_direct_chats(websocket, user_uuid, data)

            elif operation == "send_message":
                print(f"Received send_message from {user_uuid}")
                await handle_new_message(websocket, data)

            elif operation == "leave_chat":
                print(f"Received leave_chat request from {user_uuid}")
                await handle_chat_leave(websocket, user_uuid, data)

            elif operation == "read_receipt":
                print(f"Received read_receipt from {user_uuid}")
                await handle_read_receipt(websocket, user_uuid, data)

            elif operation == "typing_receipt":
                pass

            elif operation == "update_chat":
                print(f"Updating chat from {user_uuid}")
                await handle_chat_update(websocket, user_uuid, data)

            elif operation == "accept_chat_request":
                print(f"Received accept_chat_request from {user_uuid}")
                await handle_chat_request_acceptance(websocket, user_uuid, data)

            elif operation == "decline_chat_request":
                print(f"Received decline_chat_request from {user_uuid}")
                await handle_chat_request_decline(websocket, user_uuid, data)

            elif operation == "update_profile":
                print(f"Received profile update from {user_uuid}")
                await handle_profile_update(websocket, user_uuid)

            elif operation == "send_notification":
                print(f"Received notification from {user_uuid}")
                await handle_notification(data)

            else:
                await send_websocket_error(websocket, operation or "unknown", "unsupported_operation", "Unsupported operation")

    finally:
        await remove_user_from_active_connections(user_uuid)
        for chat_id, chat_map in list(active_chat_connections.items()):
            if user_uuid in chat_map:
                chat_map.pop(user_uuid, None)
                if not chat_map:
                    active_chat_connections.pop(chat_id, None)
