from typing import Annotated, Dict

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from backend.utils.user_utils import find_user, user_uuid_to_username
from backend.utils.chat_utils import create_chat, find_direct_chat_with_user
from backend.utils.database_utils import save_all_databases

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

        new_chat_obj.add_system_message(f"Chat created by {user_uuid_to_username(owner_uuid)}")
        save_all_databases()

        for participant_uuid in list(new_chat_obj.participants) + list(new_chat_obj.invited_users):
            attach_user_to_chat(new_chat_id, participant_uuid)

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

async def handle_new_message():
    pass

async def handle_chat_leave():
    pass

async def handle_read_receipt():
    pass

async def handle_typing_receipt():
    pass

async def handle_chat_update():
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

@router.websocket('/{user_uuid}')
async def websocket_endpoint(websocket: WebSocket, user_uuid: UserUUID):
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

            if operation == "ping":
                print(f"Received ping from {user_uuid}")
                await send_websocket_acknowledgement(websocket, "pong")

            elif operation == "create_chat":
                print(f"Received create_chat from {user_uuid}")
                await handle_chat_creation(websocket, user_uuid, data)

            elif operation == "send_message":
                pass

            elif operation == "leave_chat":
                pass

            elif operation == "read_receipt":
                pass

            elif operation == "typing_receipt":
                pass

            elif operation == "update_chat":
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
