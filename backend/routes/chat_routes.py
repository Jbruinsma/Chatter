from fastapi import APIRouter
from backend.utils.chat_utils import find_chat
from backend.utils.user_utils import find_user


router = APIRouter()


@router.get('/{user_uuid}')
async def get_all_chats(user_uuid: str):

    def get_chat_overview(chat_id: str):
        chat_status, chat_obj = find_chat(chat_id)
        if chat_status and chat_obj is not None:
            return chat_obj.get_chat_overview(viewer_uuid= user_uuid)
        return None

    try:
        user_status, user_obj = find_user(user_uuid)
        if not user_status or user_obj is None:
            return {"error": "User not found."}

        user_main_chat_ids = list(user_obj.chat_ids.get("main", []))
        user_request_chat_ids = list(user_obj.chat_ids.get("requests", []))

        chat_overviews = {
            "main": [get_chat_overview(chat_id) for chat_id in user_main_chat_ids],
            "requests": [get_chat_overview(chat_id) for chat_id in user_request_chat_ids]
        }

        return {"chats": chat_overviews}
    except Exception as e:
        print(f"Error fetching chats: {e}")

    return {
        "chats": {
            "main": [],
            "requests": []
        },
        "message": "Error fetching chats. Try again later."
    }