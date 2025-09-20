import bcrypt
from sqlmodel import select, or_

from backend.instances import USER_MANAGER, CHAT_MANAGER, UUID_INDEX, DIRECT_CHAT_INDEX_MANAGER
from backend.models.sql_models import User
from backend.procedures import retrieve_essential_user_info


def save_all_databases() -> None:
    USER_MANAGER.save()
    CHAT_MANAGER.save_chat_database()
    UUID_INDEX.save()
    if hasattr(DIRECT_CHAT_INDEX_MANAGER, "save"):
        DIRECT_CHAT_INDEX_MANAGER.save()

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