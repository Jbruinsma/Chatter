import bcrypt
from fastapi import Request
from sqlmodel import select, or_

from backend.models.sql_models import User
from backend.procedures import retrieve_essential_user_info


async def check_password(session, plain_text_password, user_id: str= None, username: str= None) -> tuple[bool, dict | None]:
    if not user_id and not username:
        return False, None

    statement = select(User.password).where(or_(User.id == user_id, User.username == username))
    result = await session.execute(statement)

    hashed_password: bytes | None = result.scalar_one_or_none()
    if hashed_password is None:
        return False, None

    successful_password_attempt: bool = bcrypt.checkpw(plain_text_password.encode('utf-8'), hashed_password)
    if successful_password_attempt:
        return True, await retrieve_essential_user_info(session, user_id= user_id, user_username= username)
    return False, None

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