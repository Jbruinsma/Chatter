from typing import List, Any, Coroutine, Sequence

from sqlalchemy import Row
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

async def _fetch_ids_from_procedure(session: AsyncSession, procedure_name: str, user_id: str | None = None, user_username: str | None = None) -> List[str]:
    if not user_id and not user_username:
        raise ValueError("Must provide either user_id or user_username.")

    sql = text(f"CALL {procedure_name}(:target_user_id, :target_user_username)")
    result = await session.execute(sql, {
        "target_user_id": user_id,
        "target_user_username": user_username
    })
    return list(result.first() or [])

async def retrieve_user_main_chat_ids(session: AsyncSession, user_id: str | None = None, user_username: str | None = None) -> List[str]:
    return await _fetch_ids_from_procedure(
        session, "retrieve_main_chat_ids", user_id, user_username
    )


async def retrieve_user_chat_requests(session: AsyncSession, user_id: str | None = None, user_username: str | None = None) -> List[str]:
    return await _fetch_ids_from_procedure(
        session, "retrieve_request_chat_ids", user_id, user_username
    )

async def search_for_profile_by_username_procedure(session: AsyncSession, username: str, limit: int = 5):
    result = await session.execute(
        text("CALL search_for_profile_by_username(:user_username, :results_cap)"),{
            "user_username": username,
            "results_cap": limit
        }
    )
    return result.all()