from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect
from typing import Dict, Any

from backend.instances import USER_MANAGER, CHAT_MANAGER
from backend.routes.chat_routes import user_websocket_endpoint
from backend.utils.chat_utils import find_chat
from backend.utils.formatting import format_websocket_json
from backend.utils.user_utils import find_user

router = APIRouter()

active_user_connections : Dict[str, WebSocket] = {}
active_chat_connections : Dict[str, Dict[str, Dict[str, Any]]] = {}

@router.websocket("/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    print(f"WebSocket connection attempt: username={username}")

    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        await websocket.close(1008, "User does not exist.")
        return
    user = user_node.value
    user_chat_ids = user.chat_ids

    await websocket.accept()
    print(f"WebSocket connected: {username}")

    await add_user_to_active_connections(username, websocket)

    for chat_id in user_chat_ids:
        if chat_id not in active_chat_connections:
            active_chat_connections[chat_id] = {}
        user_websocket : WebSocket | None = get_user_connection(username)
        if user_websocket is not None:
            active_chat_connections[chat_id][username] = format_connection(user_websocket)
    print(f"Active connections: {active_chat_connections}")

    try:
        while True:
            try:
                incoming_json = await websocket.receive_json()
                print(f"Received JSON from {username}: {incoming_json}")
            except WebSocketDisconnect:
                break
            except Exception as e:
                await send_ws_error(websocket, "unknown", "bad_json", "Invalid JSON", {"detail": str(e)})
                continue

            operation = (incoming_json or {}).get("operation")
            payload = (incoming_json or {}).get("data") or {}

            try:
                match operation:
                    case "enter_chat":
                        print(f"Entering chat: {payload}")
                        update_active_chat_status("chat", payload.get("chat_id"), username)
                        # await send_ws_ack(websocket, "enter_chat")

                    case "exit_chat":
                        print(f"Exiting chat: {payload}")
                        update_active_chat_status("dashboard", payload.get("chat_id"), username)
                        # await send_ws_ack(websocket, "exit_chat")

                    case "send_message":
                        print(f"Sending message: {payload}")
                        target_chat_id = payload.get("chat_id")
                        message_id = payload.get("message_id")
                        sender = payload.get("sender")

                        if not target_chat_id or not sender:
                            await send_ws_error(websocket, "send_message", "missing_fields","Required fields: id, sender")
                            continue

                        user_status, sender_user_object = find_user(sender)
                        if not user_status or sender_user_object is None:
                            await send_ws_error(websocket, "send_message", "user_not_found","Sender not found",{"sender": sender})
                            continue

                        chat_status, chat_obj = find_chat(target_chat_id)
                        if not chat_status or chat_obj is None:
                            await send_ws_error(websocket, "send_message", "chat_not_found","Chat does not exist",{"chat_id": target_chat_id})
                            continue

                        if chat_obj.chat_id not in sender_user_object.chat_ids:
                            await send_ws_error(websocket, "send_message", "chat_ownership","Chat does not belong to the user.",{"chat_id": target_chat_id, "sender": sender})
                            continue

                        chat_obj.add_message(payload)
                        unread_by = list(chat_obj.unread_messages_by)

                        payload = payload | {"unread_messages_by": unread_by}

                        print(f"UNREAD BY: {unread_by}")

                        print(f"ADDED MESSAGE: {payload}")
                        CHAT_MANAGER.save_chat_database()

                        for connection in active_chat_connections.get(target_chat_id, {}).values():
                            try:
                                await connection["websocket"].send_json(payload)
                            except Exception as e:
                                print(f"Broadcast error to {target_chat_id}: {e}")

                        await send_ws_ack(websocket, "send_message",{"delivered": True, "chat_id": target_chat_id, "message_id": payload.get("id")})

                    case "create_chat":
                        print(f"Creating chat: {payload}")
                        newly_created_chat_id = payload.get('chat_id')

                        if newly_created_chat_id not in active_chat_connections:
                            active_chat_connections[newly_created_chat_id] = {}

                        active_chat_connections[newly_created_chat_id][username] = format_connection(websocket)

                        chat_status, chat_obj = find_chat(newly_created_chat_id)
                        if not chat_status:
                            print(f"Chat {newly_created_chat_id} could not be found.")
                            continue

                        for participant in payload.get('participants'):
                            print("PARTICIPANT: ", participant)
                            if participant == username: continue

                            user_status, user_obj = find_user(participant)
                            if not user_status:
                                print(f"User {participant} not found.")
                                continue

                            if participant in active_user_connections and user_obj.is_active:
                                user_websocket : WebSocket | None = get_user_connection(participant)
                                if user_websocket is not None:
                                    active_chat_connections[newly_created_chat_id][participant] = format_connection(user_websocket)
                            else:
                                print(f"User {participant} is inactive.")

                        print("NEW PAYLOAD: ", payload)

                        for connection in active_chat_connections[newly_created_chat_id].values():
                            await connection["websocket"].send_json(format_websocket_json("chat_created", payload))

                    case _:
                        await send_ws_error(websocket, "unknown", "unsupported_operation",f"Unknown operation: {operation}")
                        continue

            except Exception as e:
                # Any unexpected error while handling this message
                await send_ws_error(websocket, operation or "unknown", "internal_error",
                                    "Failed to process message", {"detail": str(e)})
                continue

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print(f"WebSocket disconnected: {username}")
        await remove_user_from_active_connections(username)
        user.set_user_inactive()
        USER_MANAGER.save()
        for chat_id in list(user_chat_ids):
            chat_map = active_chat_connections.get(chat_id)
            if not chat_map:
                continue
            chat_map.pop(username, None)
            if not chat_map:
                active_chat_connections.pop(chat_id, None)

def format_connection(websocket: WebSocket):
    return {
        "websocket": websocket,
        "subscription_type": "dashboard"
    }

def update_subscription_type(new_subscription_type, active_connection_info):
    try:
        active_connection_info['subscription_type'] = new_subscription_type
    except KeyError as e:
        print(f"ERROR IN update_subscription_type(): {e}")
        return

def update_active_chat_status(subscription_type, chat_id, username):
    if chat_id in active_chat_connections:
        chat_connection_info = active_chat_connections[chat_id]
        user_connection_info = chat_connection_info[username]
        update_subscription_type(subscription_type, user_connection_info)


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

async def add_user_to_active_connections(username: str, websocket: WebSocket):
    active_user_connections[username] = websocket

async def remove_user_from_active_connections(username: str):
    active_user_connections.pop(username, None)

def get_user_connection(username: str) -> WebSocket | None:
    return active_user_connections.get(username, None)