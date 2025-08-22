from random import random, randint

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect
from typing import Dict, Any, List
from datetime import datetime, date, timezone
from uuid import UUID

from backend.instances import USER_MANAGER, CHAT_MANAGER
from backend.models.user import User
from backend.routes.chat_routes import user_websocket_endpoint
from backend.utils.chat_utils import find_chat
from backend.utils.formatting import format_chat_dict, format_chat_dict_for_json
from backend.utils.user_utils import find_user

router = APIRouter()


active_user_connections: Dict[str, WebSocket] = {}
active_chat_connections: Dict[str, Dict[str, Dict[str, Any]]] = {}


async def update_active_connection_username(old_username : str, new_username : str):
    # ACTIVE USER CONNECTIONS: {'test': < starlette.websockets.WebSocket object at 0x000001CB8ACCA480 >}
    active_user_connections[new_username] = active_user_connections.pop(old_username, None)

async def update_chat_connection_username(old_username : str, new_username : str, chat_ids : List[str]):
    # ACTIVE CHAT CONNECTIONS: {'56d00d2b-6f93-42f9-95a2-ef4687a25aa5': {'test': {'websocket': < starlette.websockets.WebSocket object at 0x000001CB8ACCA480 >, 'subscription_type': None}}}
    for chat_id in chat_ids:
        chat_map = active_chat_connections.get(chat_id)
        if not chat_map: continue
        chat_map[new_username] = chat_map.pop(old_username, None)

async def username_to_object(username: str) -> User | Dict[str, str]:
    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return {"error": "User not found."}
    return user_node.value

async def add_user_to_active_connections(username: str, websocket: WebSocket):
    active_user_connections[username] = websocket

async def remove_user_from_active_connections(username: str):
    active_user_connections.pop(username, None)

def attach_user_to_chat(chat_id: str, username: str):
    user_websocket = get_user_connection(username)
    if user_websocket is None:
        return
    ensure_chat_bucket(chat_id)
    active_chat_connections[chat_id][username] = format_connection(user_websocket)

def remove_user_from_chat(chat_id: str, username: str) -> None:
    chat_map = active_chat_connections.get(chat_id)
    if not chat_map:
        return

    chat_map.pop(username, None)

    if not chat_map:
        active_chat_connections.pop(chat_id, None)

def get_user_connection(username: str) -> WebSocket | None:
    return active_user_connections.get(username)

def ensure_chat_bucket(chat_id: str):
    if chat_id not in active_chat_connections:
        active_chat_connections[chat_id] = {}

def format_connection(ws: WebSocket) -> Dict[str, Any]:
    return {"websocket": ws, "subscription_type": None}

def update_subscription_type(subscription_type: str, user_info: Dict[str, Any]):
    user_info["subscription_type"] = subscription_type

def update_active_chat_status(subscription_type, chat_id, username):
    chat_map = active_chat_connections.get(chat_id)
    if not chat_map: return
    user_info = chat_map.get(username)
    if not user_info: return
    update_subscription_type(subscription_type, user_info)

async def handle_create_chat(request_websocket : WebSocket, creator_obj : User, payload : Dict[str, str | list[str]]):

    print(f"Payload: {payload}")

    chat_name = payload.get("chat_name")
    print(f"Chat name: {chat_name}")

    chat_creator_username = creator_obj.username

    participants = payload.get("participants", [])
    print(f"Participants: {participants}")

    participant_permissions = payload.get("permissions", {})

    participant_objects = []

    for participant in participants:
        participant_obj = await username_to_object(participant)
        if isinstance(participant_obj, User):
            participant_objects.append(participant_obj)

    try:

        chat_id, chat_obj = CHAT_MANAGER.add_chat(owner= creator_obj, participants= participant_objects, chat_name= chat_name, participant_permissions= participant_permissions)

        for participant in participant_objects:
            participant.add_chat_id(chat_id)
        creator_obj.add_chat_id(chat_id)

        chat_obj.add_system_message(f"[=== {', '.join(chat_obj.participants.keys())} ===]")
        chat_obj.add_system_message(f"Chat created by {chat_creator_username}")
        print(f"CHAT OBJECT CREATED: {chat_obj}")

        time_created = getattr(chat_obj, "time_created", None)
        if isinstance(time_created, (datetime, date)):
            time_created = time_created.isoformat()
        else:
            time_created = datetime.now(timezone.utc).isoformat()
        ensure_chat_bucket(chat_id)
        attach_user_to_chat(chat_id, chat_creator_username)

        for participant in participants:
            if participant == creator_obj.username: continue
            attach_user_to_chat(chat_id, participant)

        event = {"operation": "chat_created"} | chat_obj.to_dict()

        print(f"CHAT EVENT: {event}")

        CHAT_MANAGER.save_chat_database()
        USER_MANAGER.save()

        print('DATABASES SAVED')

        await broadcast_to_chat(chat_id, event)
        await send_ws_ack(request_websocket, "create_chat", {"chat_id": chat_id, "time_created": time_created})

    except Exception as e:
        print(f"Error creating chat: {e}")
        await send_ws_error(request_websocket, "create_chat", "error", "Error creating chat", {"detail": str(e)})

async def handle_enter_chat(websocket, username, payload):
    chat_id = payload.get("chat_id")
    if not chat_id:
        await send_ws_error(websocket, "enter_chat", "missing_chat_id", "Missing chat ID")
        return
    ensure_chat_bucket(chat_id)
    attach_user_to_chat(chat_id, username)
    update_active_chat_status("chat", chat_id, username)
    await send_ws_ack(websocket, "enter_chat", {"chat_id": chat_id})

async def handle_exit_chat(websocket, username, payload):
    chat_id = payload.get("chat_id")
    if not chat_id:
        await send_ws_error(websocket, "exit_chat", "missing_chat_id", "Missing chat ID")
        return
    chat_map = active_chat_connections.get(chat_id)
    update_active_chat_status("dashboard", chat_id, username)
    await send_ws_ack(websocket, "exit_chat", {"chat_id": chat_id})

async def handle_leave_chat(websocket, username, payload):
    chat_id = payload.get("chat_id")
    if not chat_id:
        await send_ws_error(websocket, "leave_chat", "missing_chat_id", "Missing chat ID")
        return

    user_status, user_obj = find_user(username)
    if not user_status or user_obj is None:
        await send_ws_error(websocket, "leave_chat", "user_not_found", "User does not exist", {"username": username})
        return

    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        await send_ws_error(websocket, "leave_chat", "chat_not_found", "Chat does not exist", {"chat_id": chat_id})

    ensure_chat_bucket(chat_id)

    is_owner = chat_obj.owner == username

    chat_obj.remove_participant(user_obj)

    if len(chat_obj.participants) == 0:
        CHAT_MANAGER.delete_chat(chat_id)
        active_chat_connections.pop(chat_id, None)
        await send_ws_ack(websocket, "leave_chat", {"chat_id": chat_id, "message": "Chat deleted due to no participants."})
        return

    if is_owner:
        participant_list = list(chat_obj.participants.keys())
        random_new_owner_index = randint(0, len(participant_list) - 1)
        new_owner_username = participant_list[random_new_owner_index]
        chat_obj.promote_to_owner(new_owner_username)

    leave_chat_message = chat_obj.send_user_leave_message(username)
    if leave_chat_message:
        await broadcast_to_chat(chat_id, {"operation": "message"} | {'chat_id': chat_id} | leave_chat_message | {"unread_messages_by": list(chat_obj.unread_messages_by)})

    await broadcast_to_chat(chat_id, {"operation": "update_chat"} | chat_obj.to_dict())
    remove_user_from_chat(chat_id, username)

    CHAT_MANAGER.save_chat_database()
    USER_MANAGER.save()

    await send_ws_ack(websocket, "leave_chat", {"chat_id": chat_id})

async def handle_send_message(websocket, username, payload):
    chat_id = payload.get("chat_id")
    message_text = payload.get("message")
    if not chat_id:
        await send_ws_error(websocket, "send_message", "missing_chat_id", "Missing chat ID")
        return
    if not message_text:
        await send_ws_error(websocket, "send_message", "missing_message", "Missing message")
        return

    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        await send_ws_error(websocket, "send_message", "chat_not_found","Chat does not exist",{"chat_id": chat_id})

    ensure_chat_bucket(chat_id)
    new_message = format_chat_dict(chat_id, username, message_text)

    print(f"New message: {new_message}")
    chat_obj.add_message(new_message)

    print(f"UNREAD BY: {chat_obj.unread_messages_by}")

    chat_map = active_chat_connections.get(chat_id)

    print(f"Active chat connections for {chat_id}: {chat_map}")

    for active_participant_username, active_participant_connection_info in chat_map.items():
        subscription_type = active_participant_connection_info["subscription_type"]
        if subscription_type == "chat":
            chat_obj.mark_as_read_by(active_participant_username)

    CHAT_MANAGER.save_chat_database()
    USER_MANAGER.save()

    await broadcast_to_chat(chat_id, {"operation": "message"} | new_message | {"unread_messages_by": list(chat_obj.unread_messages_by)})

    message_id = new_message.get('message_id')
    message_timestamp = new_message.get('time_sent')

    await send_ws_ack(websocket, "send_message", format_chat_dict_for_json(message_id, "message", chat_id, username, message_text, message_timestamp))

async def handle_read_receipt(websocket, payload):
    chat_id = payload.get("chat_id")
    if not chat_id:
        await send_ws_error(websocket, "read_receipt", "missing_chat_id", "Missing chat ID")
        return

    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        await send_ws_error(websocket, "read_receipt", "chat_not_found", "Chat does not exist", {"chat_id": chat_id})
        return

    username = payload.get("username")
    if not username:
        await send_ws_error(websocket, "read_receipt", "missing_username", "Missing username")
        return

    chat_obj.mark_as_read_by(username)
    chat_unread_list = list(chat_obj.unread_messages_by)

    CHAT_MANAGER.save_chat_database()

    read_receipt_payload = {"operation": "read_receipt", "chat_id": chat_id, "username": username, "unread_messages_by": chat_unread_list}

    await broadcast_to_chat(chat_id, read_receipt_payload)

async def handle_update_chat(websocket, username, payload):
    chat_id = payload.get("chat_id")
    if not chat_id:
        await send_ws_error(websocket, "update_chat", "missing_chat_id", "Missing chat ID")
        return
    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        await send_ws_error(websocket, "update_chat", "chat_not_found", "Chat does not exist", {"chat_id": chat_id})
        return

    removed_participant_list = payload.get("removed_participants", [])
    added_participant_list = payload.get("added_participants", [])
    updated_permissions = payload.get("updated_permissions", {})
    updated_chat_name = payload.get("chat_name", None)

    ensure_chat_bucket(chat_id)

    for participant_username in updated_permissions:
        if participant_username in removed_participant_list or participant_username in added_participant_list: continue
        chat_obj.update_permissions(participant_username, updated_permissions[participant_username])

    for participant_to_be_removed in removed_participant_list:
        user_status, user_obj = find_user(participant_to_be_removed)
        if not user_status or user_obj is None: continue
        chat_obj.remove_participant(user_obj)
        user_obj.chat_ids.remove(chat_id)

        kick_message = chat_obj.send_user_kick_message(participant_to_be_removed, username)
        if kick_message:
            await broadcast_to_chat(chat_id, {"operation": "message"} | {'chat_id': chat_id} | kick_message | {"unread_messages_by": list(chat_obj.unread_messages_by)})

    for participant_to_be_added in added_participant_list:
        user_status, user_obj = find_user(participant_to_be_added)
        if not user_status or user_obj is None: continue

        can_edit = updated_permissions.get(participant_to_be_added, {}).get("can_edit", False)
        chat_obj.add_participant(user_obj, can_edit)
        user_obj.add_chat_id(chat_id)

        attach_user_to_chat(chat_id, participant_to_be_added)

        join_message = chat_obj.send_user_join_message(participant_to_be_added, username)
        if join_message:
            await broadcast_to_chat(chat_id, {"operation": "message"} | {'chat_id': chat_id} | join_message | {"unread_messages_by": list(chat_obj.unread_messages_by)})

    if updated_chat_name is not None:
        chat_obj.chat_name = updated_chat_name


    CHAT_MANAGER.save_chat_database()
    USER_MANAGER.save()

    await broadcast_to_chat(chat_id, {'operation': "update_chat"} | chat_obj.to_dict())
    for removed_participant_username in removed_participant_list:
        remove_user_from_chat(chat_id, removed_participant_username)

    edit_message = chat_obj.send_user_edit_message(username)
    if edit_message:
        await broadcast_to_chat(chat_id, {"operation": "message"} | {'chat_id': chat_id} | edit_message | {"unread_messages_by": list(chat_obj.unread_messages_by)})

async def handle_join_chat(websocket, username, payload):
    chat_id = payload.get("chat_id")
    if not chat_id:
        await send_ws_error(websocket, "join_chat", "missing_chat_id", "Missing chat ID")
        return
    ensure_chat_bucket(chat_id)
    attach_user_to_chat(chat_id, username)
    await send_ws_ack(websocket, "join_chat", {"chat_id": chat_id})

async def handle_username_update(websocket, username, payload):
    new_username = payload.get("new_username")
    if not new_username:
        await send_ws_error(websocket, "username_update", "missing_new_username", "Missing new username")

    user_status, user_obj = find_user(new_username)
    if not user_status or user_obj is None:
        await send_ws_error(websocket, "username_update", "user_not_found", "User does not exist", {"username": username})
        return

    user_chats = list(user_obj.chat_ids)

    await update_active_connection_username(username, new_username)
    await update_chat_connection_username(username, new_username, user_chats)

    for chat_id in user_chats:
        await broadcast_to_chat(chat_id, {"operation": "update_user", "chat_id": chat_id} | {"old_username": username} | user_obj.to_dict())

async def broadcast_to_chat(chat_id: str, payload: dict):
    payload = json_sanitize(payload)
    chat_map = active_chat_connections.get(chat_id) or {}
    for info in list(chat_map.values()):
        ws = info.get("websocket")
        if ws:
            try:
                await ws.send_json(payload)
            except Exception:
                pass

def json_sanitize(x):
    if isinstance(x, (datetime, date)):
        return x.isoformat()
    if isinstance(x, UUID):
        return str(x)
    if isinstance(x, dict):
        return {k: json_sanitize(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [json_sanitize(v) for v in x]
    return x

async def send_ws_error(ws: WebSocket, op: str, code: str, message: str, extra: dict | None = None):
    payload = {"type": "error", "operation": op, "code": code, "message": message}
    if extra:
        payload["data"] = extra
    await ws.send_json(payload)

async def send_ws_ack(ws: WebSocket, op: str, extra: dict | None = None):
    payload = {"type": "ack", "operation": op}
    if extra:
        payload["data"] = extra
    await ws.send_json(payload)

@router.websocket('/{username}')
async def websocket_endpoint(websocket: WebSocket, username: str):
    user_status, user = find_user(username)

    if not user_status:
        await websocket.close(1008, "User does not exist.")
        return

    await websocket.accept()
    await add_user_to_active_connections(username, websocket)
    user_chat_ids = getattr(user, "chat_ids", [])

    for chat_id in user_chat_ids:
        attach_user_to_chat(chat_id, username)

    try:
        while True:
            try:
                incoming_json = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except Exception as e:
                await send_ws_error(websocket, "unknown", "bad_json", "Invalid JSON", {"detail": str(e)})
                continue

            operation = (incoming_json or {}).get("operation")
            data = (incoming_json or {}).get("data") or {}

            if operation == "ping":

                print(f"Received ping from {username}")
                await send_ws_ack(websocket, "pong")

            elif operation == "create_chat":

                print(f"Creating chat: {data}")
                await handle_create_chat(websocket, user, data)

            elif operation == "enter_chat":

                print(f"Entering chat: {data}")
                await handle_enter_chat(websocket, username, data)

            elif operation == "exit_chat":

                print(f"Exiting chat: {data}")
                await handle_exit_chat(websocket, username, data)

            elif operation == "send_message":

                print(f"Sending message: {data}")
                await handle_send_message(websocket, username, data)

            elif operation == "join_chat":

                print(f"Joining chat: {data}")
                await handle_join_chat(websocket, username, data)

            elif operation == "leave_chat":

                print(f"Leaving chat: {data}")
                await handle_leave_chat(websocket, username, data)

            elif operation == "read_receipt":

                print(f"Received read receipt: {data}")
                await handle_read_receipt(websocket, data)

            elif operation == "update_chat":

                print(f"Updating chat: {data}")
                await handle_update_chat(websocket, username, data)

            elif operation == "update_username":

                print(f"UPDATING USERNAME: {data}")
                await handle_username_update(websocket, username, data)
                username = data.get("new_username")

            else:
                await send_ws_error(websocket, operation or "unknown", "unsupported_operation", "Unsupported operation")

    finally:
        await remove_user_from_active_connections(username)
        for chat_id, chat_map in list(active_chat_connections.items()):
            if username in chat_map:
                chat_map.pop(username, None)
                if not chat_map:
                    active_chat_connections.pop(chat_id, None)
