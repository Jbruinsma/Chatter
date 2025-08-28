from typing import Annotated

from fastapi import APIRouter
from starlette.websockets import WebSocket

router = APIRouter()

ChatId = Annotated[str, "chat_id"]
UserUUID = Annotated[str, "user_uuid"]

active_user_connections: Dict[str, WebSocket] = {}
active_chat_connections: Dict[ChatId, Dict[UserUUID, WebSocket]] = {}

async def add_user_to_active_connections(user_uuid: UserUUID, websocket: WebSocket) -> None:
    active_user_connections[user_uuid] = websocket

async def attach_user_to_chat(chat_id: ChatId, user_uuid: UserUUID) -> None:
    user_websocket: WebSocket | None = get_user_connection(user_uuid)
    if user_websocket is None:
        return
    ensure_chat_bucket(chat_id)
    active_chat_connections[chat_id][user_uuid] = user_websocket

def get_user_connection(user_uuid: UserUUID) -> WebSocket | None:
    return active_user_connections.get(user_uuid)

def ensure_chat_bucket(chat_id: ChatId) -> None:
    if chat_id not in active_chat_connections:
        active_chat_connections[chat_id] = {}

async def send_websocket_error(websocket: WebSocket, operation: str, code: str, message: str, extra: dict | None = None) -> None:
    payload = {"type": "error", "operation": operation, "code": code, "message": message}
    if extra:
        payload["data"] = extra
    await websocket.send_json(payload)

async def send_websocket_acknowledgement(websocket: WebSocket, operation: str, extra: dict | None = None) -> None:
    payload = {"type": "ack", "operation": operation}
    if extra:
        payload["data"] = extra
    await websocket.send_json(payload)

@router.websocket_('/{user_uuid}')
async def websocket_endpoint(websocket: Websocket, user_uuid: UserUUID):
    user_status, user_obj = find_user(user_uuid)

    if not user_status or user_obj is None:
        await websocket.close(1008, "User does not exist.")
        return

    await websocket.accept()
    await add_user_to_active_connections(user_uuid, websocket)

    user_chat_ids = list(getattr(user_obj, "chat_ids", []))

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

    finally:
        await remove_user_from_active_connections(user_uuid)
        for chat_id, chat_map in list(active_chat_connections.items()):
            if user_uuid in chat_map:
                chat_map.pop(user_uuid, None)
                if not chat_map:
                    active_chat_connections.pop(chat_id, None)
