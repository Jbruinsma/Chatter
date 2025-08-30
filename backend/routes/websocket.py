from typing import Annotated, Dict

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

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

async def handle_chat_creation(request_websocket: WebSocket, current_user_uuid: str, new_chat_info):
    owner_uuid = new_chat_info.get("owner_id")
    if owner_uuid != current_user_uuid:
        await send_websocket_error(request_websocket, "create_chat", "invalid_owner_id", "Invalid owner ID")
        return

    participant_ids = new_chat_info.get("participant_ids", [])
    if not participant_ids:
        await send_websocket_error(request_websocket, "create_chat", "missing_participant_ids", "Missing participant IDs")
        return

    chat_name = new_chat_info.get("chat_name", "")
    chat_cover = new_chat_info.get("chat_cover", "")
    chat_type = new_chat_info.get("chat_type", "")

    if len(participant_ids) == 2:
        chat_type = "direct"
        chat_name = f"@{participant_ids[0]} and @{participant_ids[1]}"
        for participant_uuid in participant_ids:
            if participant_uuid != owner_uuid:
                direct_chat_exists, direct_chat_id = find_direct_chat_with_user(owner_uuid, participant_uuid)
                if direct_chat_exists:
                    await send_websocket_error(request_websocket, "create_chat", "direct_chat_exists", "Direct chat already exists", {"chat_id": direct_chat_id})
                    return

    participant_permissions = new_chat_info.get("participant_permissions", {})
    if not participant_permissions or set(participant_permissions.keys()) != set(participant_ids):
        await send_websocket_error(request_websocket, "create_chat", "invalid_participant_permissions", "Invalid participant permissions")

    try:

        new_chat_id, new_chat_obj = create_chat(
            chat_name= chat_name,
            chat_cover=chat_cover,
            owner_id=owner_uuid,
            participant_ids=participant_ids,
            participant_permissions=participant_permissions,
            chat_type=chat_type
        )

        new_chat_obj.add_system_message(system_message= f"Chat created by {user_uuid_to_username(owner_uuid)}")
        save_all_databases()

        for participant_uuid in list(new_chat_obj.participants) + list(new_chat_obj.invited_users):
            await attach_user_to_chat(new_chat_id, participant_uuid)

        await broadcast_to_chat(new_chat_id,{
            "operation": "create_chat",
            "chat_id": new_chat_id
        })
        await send_websocket_acknowledgement(request_websocket, "create_chat", {
            "chat_id": new_chat_id,
            "Message": f"Chat '{new_chat_obj.chat_name}' created successfully."
        })

    except Exception as e:
        print(f"Error creating chat: {e}")
        await send_websocket_error(request_websocket, "create_chat", "error", "Error creating chat", {"detail": str(e)})

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
        "operation": "send_message",
        "messageInfo": format_message_dict_for_json(**message_info),
        "hasUnreadMessages": True
    })

    await send_websocket_acknowledgement(request_websocket, "message_delivered", {
        "chat_id": chat_id,
        "message_id": message_info.get("message_id")
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
        await send_websocket_error(request_websocket, "leave_chat", "invalid_chat_id", "Invalid chat ID")

    ensure_chat_bucket(chat_id)

    is_owner = chat_obj.owner_id == user_uuid

    chat_obj.participant_ids.discard(user_uuid)
    chat_obj.participant_permissions.pop(user_uuid, None)
    user_obj.chat_ids["main"].discard(chat_id)
    chat_obj.add_system_message(system_message= f"{user_uuid_to_username(user_uuid)} left")

    broadcast_to_chat(chat_id, {
        "operation": "send_message",
        "messageInfo": format_message_dict_for_json(**chat_obj.last_message_to_dict()),
        "hasUnreadMessages": True
    })

    if is_owner:
        participant_ids_list = list(chat_obj.participant_ids)
        random_new_owner_index = randint(0, len(participant_ids_list) - 1)
        new_owner_id = participant_ids_list[random_new_owner_index]
        chat_obj.owner_id = new_owner_id
        chat_obj.participant_permissions[new_owner_id]["can_edit"] = True
        chat_obj.add_system_message(system_message= f"{user_uuid_to_username(new_owner_id)} has been made owner")

        broadcast_to_chat(chat_id, {
            "operation": "send_message",
            "MessageInfo": format_message_dict_for_json(**chat_obj.last_message_to_dict()),
            "hasUnreadMessages": True
        })

    await detach_user_from_chat(chat_id, user_uuid)
    save_all_databases()
    await send_websocket_acknowledgement(request_websocket, "leave_chat", {
        "chat_id": chat_id,
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
        "chat_id": chat_id,
        "hasUnreadMessages": False
    })

async def handle_typing_receipt():
    pass

async def handle_chat_update(request_websocket: WebSocket, user_uuid: UserUUID, update_info: dict):
    removed_participant_ids_list = payload.get("removed_participant_ids", [])
    added_participant_ids_list = payload.get("added_participants", [])
    updated_permissions = payload.get("updated_permissions", {})
    updated_chat_name = payload.get("chat_name", None)
    updated_chat_cover = payload.get("chat_cover", None)

    unadded_users = []

    chat_id = update_info.get("chat_id")
    if not chat_id:
        await send_websocket_error(request_websocket, "update_chat", "missing_chat_id", "Missing chat ID")
        return

    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        await send_websocket_error(request_websocket, "update_chat", "invalid_chat_id", "Invalid chat ID")

    ensure_chat_bucket(chat_id)

    for participant_uuid in updated_permissions:
        if participant_uuid in removed_participant_ids_list or participant_uuid in added_participant_ids_list: continue
        chat_obj.participant_permissions[participant_uuid] = updated_permissions[participant_uuid]

    for participant_uuid in removed_participant_ids_list:
        user_status, user_obj = find_user(participant_uuid)
        invited_user: bool = participant_uuid in chat_obj.invited_users
        if invited_user: chat_obj.invited_users.discard(participant_uuid)
        else: chat_obj.participant_ids.discard(participant_uuid)
        if not invited_user:
            chat_obj.add_system_message(system_message= f"@{user_uuid_to_username(participant_uuid)} has been removed by @{user_uuid_to_username(user_uuid)}")
            await broadcast_to_chat(chat_id, {
                "operation": "send_message",
                "MessageInfo": format_message_dict_for_json(**chat_obj.last_message_to_dict()),
                "hasUnreadMessages": True
            })
        if not user_status or user_obj is None: continue
        if invited_user: user_obj.chat_ids["requests"].discard(chat_id)
        else: user_obj.chat_ids["requests"].discard(chat_id)

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
                "MessageInfo": format_message_dict_for_json(**chat_obj.last_message_to_dict()),
                "hasUnreadMessages": True
            })
            await attach_user_to_chat(chat_id, participant_uuid)

    if updated_chat_name: chat_obj.chat_name = updated_chat_name

    if updated_chat_cover: chat_obj.chat_cover = updated_chat_cover

    chat_obj.add_system_message(system_message= f"{user_uuid_to_username(user_uuid)} made updates to the chat")
    await broadcast_to_chat(chat_id, {
        "operation": "send_message",
        "MessageInfo": format_message_dict_for_json(**chat_obj.last_message_to_dict()),
        "hasUnreadMessages": True
    })

    save_all_databases()

    await broadcast_to_chat(chat_id, {
        "operation": "update_chat",
        "chat_id": chat_id,
        "participantIdsList": list(chat_obj.participant_ids),
        "invitedIdsList": list(chat_obj.invited_users),
    })

    for participant_uuid in removed_participant_ids_list:
        await detach_user_from_chat(chat_id, participant_uuid)

    await send_websocket_acknowledgement(request_websocket, "update_chat_confirmation", {
        "chat_id": chat_id,
        "message": "Chat updated successfully.",
        "unadded_users": unadded_users
    })


async def handle_chat_request_acceptance():
    pass

async def handle_chat_request_decline():
    pass

async def handle_username_update():
    pass

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
        except Exception:
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

            elif operation == "send_message":
                print(f"Received send_message from {user_uuid}")
                await handle_new_message(websocket, data)

            elif operation == "leave_chat":
                print(f"Received leave_chat request from {user_uuid}")
                await handle_chat_leave(websocket, user_uuid, data)

            elif operation == "read_receipt":
                pass

            elif operation == "typing_receipt":
                pass

            elif operation == "update_chat":
                pass

            elif operation == "accept_chat_request":
                pass

            elif operation == "decline_chat_request":
                pass

            elif operation == "update_username" or operation == "update_profile_picture":
                pass

            else:
                await send_websocket_error(websocket, operation or "unknown", "unsupported_operation", "Unsupported operation")

    finally:
        await remove_user_from_active_connections(user_uuid)
        for chat_id, chat_map in list(active_chat_connections.items()):
            if user_uuid in chat_map:
                chat_map.pop(user_uuid, None)
                if not chat_map:
                    active_chat_connections.pop(chat_id, None)
