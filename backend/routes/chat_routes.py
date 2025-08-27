from fastapi import APIRouter


router = APIRouter()


@router.get('/{user_uuid}')
async def get_all_chats(user_uuid: str):
    try:
        user_status, user_obj = find_user(user_uuid)
        if not user_status or user_obj is None:
            return {"error": "User not found."}

        user_chat_ids = list(user_obj.chat_ids)
        chat_overviews = []

        for chat_id in user_chat_ids:
            chat_status, chat_obj = find_chat(chat_id)
            if chat_status and chat_obj is not None:
                chat_overviews.append(chat_obj.get_chat_overview(viewer_uuid= user_uuid))

        return {"chats": chat_overviews}
    except Exception as e:
        print(e)

    return {"chats": []}