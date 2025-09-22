from typing import Any, Coroutine

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends
from pathlib import Path
import uuid, os

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.models.chat_overviews import ChatOverviews
from backend.models.pydantic_models import ErrorMessage
from backend.procedures import check_if_user_exists
from backend.utils.chat_utils import find_chat, find_direct_chat_with_user, retrieve_chat_ids
from backend.utils.user_utils import find_user
from backend.utils.media import normalize_chat_media


router = APIRouter()

MAX_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get("/{user_uuid}")
async def get_all_chats(user_uuid: str, request: Request, database_session: AsyncSession = Depends(get_session)) -> ErrorMessage | ChatOverviews:

    user_status = await check_if_user_exists(database_session, user_id= user_uuid)
    if not user_status:
        return ErrorMessage(error= f"User ({user_uuid}) does not exist.")

    user_chat_ids = await retrieve_chat_ids(database_session, user_id= user_uuid)

    return ChatOverviews(
        main=user_chat_ids.get("main", []),
        requests=user_chat_ids.get("requests", [])
    )

    # def get_chat_overview(chat_id: str):
    #     chat_status, chat_obj = find_chat(chat_id)
    #     if chat_status and chat_obj is not None:
    #         raw = chat_obj.to_dict(viewer_uuid=user_uuid)
    #         return normalize_chat_media(request, raw)
    #     return None
    #
    # try:
    #     user_status, user_obj = find_user(user_uuid)
    #     if not user_status or user_obj is None:
    #         return {"error": "User not found."}
    #
    #     user_main_chat_ids = list(user_obj.chat_ids.get("main", []))
    #     user_request_chat_ids = list(user_obj.chat_ids.get("requests", []))
    #
    #     chat_overviews = {
    #         "main":     [c for c in (get_chat_overview(cid) for cid in user_main_chat_ids) if c is not None],
    #         "requests": [c for c in (get_chat_overview(cid) for cid in user_request_chat_ids) if c is not None],
    #     }
    #
    #     return {"chats": chat_overviews}
    #
    # except Exception as e:
    #     print(f"Error fetching chats: {e}")
    #     return {"chats": {"main": [], "requests": []}, "error": "Error fetching chats. Try again later."}


@router.get("/{user_uuid}/{chat_id}")
async def get_chat(user_uuid: str, chat_id: str, request: Request):
    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        return {"error": "User not found."}

    user_main_chat_ids = list(user_obj.chat_ids.get("main", []))
    user_request_chat_ids = list(user_obj.chat_ids.get("requests", []))
    if chat_id not in user_main_chat_ids and chat_id not in user_request_chat_ids:
        return {"error": "Chat not found."}

    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        return {"error": "Chat not found."}

    raw = chat_obj.to_dict(viewer_uuid=user_uuid)
    return {"chat": normalize_chat_media(request, raw)}


@router.get("/{user_uuid}/{chat_id}/messages")
async def get_chat_messages(user_uuid: str, chat_id: str):
    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        return {"error": "User not found."}

    if chat_id not in user_obj.chat_ids["main"] and chat_id not in user_obj.chat_ids["requests"]:
        return {"error": "User does not have permission to view the contents of this chat."}

    chat_status, chat_obj = find_chat(chat_id)
    if not chat_status or chat_obj is None:
        return {"error": "Chat not found."}

    return {"messages": chat_obj.all_messages_to_list()}


@router.post("/upload_chat_cover")
async def upload_chat_cover(request: Request, chat_cover: UploadFile = File(...)):
    if chat_cover.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(status_code=400, detail="Only PNG or JPG allowed")

    cover_dir = Path(request.app.state.CHAT_COVER_DIR)
    cover_dir.mkdir(parents=True, exist_ok=True)

    ext = ".png" if chat_cover.content_type == "image/png" else ".jpg"
    fname = f"{uuid.uuid4().hex}{ext}"
    dest_path = cover_dir / fname

    written = 0
    with dest_path.open("wb") as out:
        while True:
            chunk = await chat_cover.read(1024 * 1024)  # 1MB
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_BYTES:
                out.close()
                try:
                    dest_path.unlink()
                except Exception:
                    pass
                raise HTTPException(status_code=400, detail="Max 5MB")
            out.write(chunk)

    rel_path = f"/media/covers/{fname}"
    base = str(request.base_url).rstrip("/")
    full_url = f"{base}{rel_path}"

    print("Saved chat cover:", dest_path)
    return {"chat_cover": full_url, "path": rel_path}


@router.get("/{user_uuid}/direct_chats/{participant_uuid}")
async def get_direct_chat(user_uuid: str, participant_uuid: str, request: Request):
    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        return {"error": "User not found."}

    participant_status, participant_obj = find_user(participant_uuid)
    if not participant_status or participant_obj is None:
        return {"error": "Participant not found."}

    chat_id = None

    chat_status, chat_id = find_direct_chat_with_user(user_uuid, participant_uuid)

    return {
        "chatStatus": chat_status,
        "chatId": chat_id
    }
