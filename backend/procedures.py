from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.sql import text

from backend.models.notification_preferences import NotificationPreferences


async def register_user_procedure(session: AsyncSession, user_data: dict) -> None:
    sql = text(
        "CALL register_user(:user_id, :user_username, :user_password, :user_is_public)"
    )
    await session.execute(sql, {
        "user_id": user_data["user_id"],
        "user_username": user_data["username"],
        "user_password": user_data["password"],
        "user_is_public": user_data["is_public"]
    })
    await session.commit()

async def check_if_user_exists(session: AsyncSession, user_id: str= None, user_username: str= None) -> bool | None:
    if not user_id and not user_username:
        return False

    sql = text(
        "CALL find_user(:target_user_id, :target_user_username)"
    )
    result = await session.execute(sql, {
        "target_user_id": user_id,
        "target_user_username": user_username
    })
    return result.fetchone()

async def retrieve_user_notification_preferences(session: AsyncSession, user_id: str =None, user_username: str =None) -> NotificationPreferences:
    if not user_id and not user_username:
        raise Exception("Must provide either user_id or user_username.")

    sql = text(
        "CALL retrieve_user_notification_preferences(:user_id, :user_username)"
    )
    result = await session.execute(sql, {
        "user_id": user_id,
        "user_username": user_username
    })

    row = result.first()
    if row:
        allow_essential_notifications = bool(row[0])
        allow_message_notifications = bool(row[1])
        return NotificationPreferences(
            essential= allow_essential_notifications,
            messages= allow_message_notifications,
        )

    raise Exception(f"Notification preferences for User (ID): {user_id}, (Username): {user_username} not found.")

async def retrieve_essential_user_info(session: AsyncSession, user_id: str =None, user_username: str =None) -> dict:
    if not user_id and not user_username:
        raise Exception("Must provide either user_id or user_username.")
    sql = text(
        "CALL retrieve_essential_user_info(:target_user_id, :target_user_username)"
    )
    result = await session.execute(sql, {
        "target_user_id": user_id,
        "target_user_username": user_username
    })
    row = result.first()
    if row:
        return {
            "id": row[0],
            "username": row[1],
            "isPublic": row[2],
        }
    raise Exception(f"User (ID): {user_id}, (Username): {user_username} not found.")