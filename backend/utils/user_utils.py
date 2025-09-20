from fastapi import Request

def find_user(username):
    from backend.instances import USER_MANAGER
    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return False, None
    user = user_node.value
    return True, user

def user_uuid_to_username(user_uuid):
    user_status, user_obj = find_user(user_uuid)
    if not user_status:
        return None
    return user_obj.username

def format_pfp_link(request: Request, pfp_link: str) -> str | None:
    if pfp_link is not None:
        if pfp_link.startswith("/media/"):
            pfp_link = pfp_link.replace("/media/", "", 1)
            return str(request.url_for("media", path=pfp_link))
    return None