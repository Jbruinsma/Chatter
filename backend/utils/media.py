from fastapi import Request

def media_url(request: Request, value: str | None) -> str | None:
    """Expand a stored media path to an absolute URL served by app.mount('/media', ...)."""
    if not value:
        return value
    if value.startswith("http://") or value.startswith("https://") or value.startswith("blob:"):
        return value
    # support both legacy "/media/..." and new "relative" stored paths
    if value.startswith("/media/"):
        path = value.replace("/media/", "", 1)
    else:
        path = value
    return str(request.url_for("media", path=path))

def normalize_chat_media(request: Request, chat: dict | None) -> dict | None:
    if not chat:
        return chat
    # chat cover
    chat["chatCover"] = media_url(request, chat.get("chatCover"))

    # top-level avatar (you set this for direct chats)
    if "avatar" in chat:
        chat["avatar"] = media_url(request, chat.get("avatar"))

    # participants’ avatars
    participants = chat.get("participantsById") or {}
    for _uid, pdata in participants.items():
        if isinstance(pdata, dict) and "avatar" in pdata:
            pdata["avatar"] = media_url(request, pdata.get("avatar"))

    # embedded otherParticipant avatar (direct chat convenience field)
    other = chat.get("otherParticipant")
    if isinstance(other, dict) and "avatar" in other:
        other["avatar"] = media_url(request, other.get("avatar"))

    return chat
