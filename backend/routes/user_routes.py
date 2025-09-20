import bcrypt
from fastapi import APIRouter, Request, Query, HTTPException, UploadFile, Depends
from pathlib import Path
import uuid
import json
import mimetypes
from typing import Dict, Any, Coroutine

from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm.session import Session

from backend.database import get_session
from backend.instances import UUID_INDEX, USER_MANAGER
from backend.models.login_data import LoginData
from backend.models.notification_preferences import NotificationPreferences
from backend.models.successful_login_message import SuccessfulLoginMessage
from backend.models.user import User
from backend.models.user_registration import UserRegistration
from backend.procedures import register_user_procedure, check_if_user_exists, retrieve_user_notification_preferences
from backend.pydantic_models.pydantic_variables import FollowerCount, FollowingCount
from backend.utils.user_utils import find_user, format_pfp_link, check_password
from backend.utils.formatting import format_count

from backend.models.pydantic_models import (
    EssentialInfo,
    Settings,
    Profile,
    Stats,
    Relations,
    Permissions,
    ErrorMessage
)



router = APIRouter()


APP_ROOT = Path(__file__).resolve().parents[2]
MEDIA_DIR = (APP_ROOT / "media").resolve()
AVATAR_DIR = (MEDIA_DIR / "avatars").resolve()
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "on"}
    return None


async def _save_upload(file: UploadFile, dest: Path, max_bytes: int = MAX_UPLOAD_BYTES):
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    size = 0
    with dest.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                try:
                    f.close()
                finally:
                    dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File too large (max 5MB).")
            f.write(chunk)
    await file.close()
    print(f"[avatar] saved {size} bytes -> {dest}")

async def send_login_success(database_session: AsyncSession, user_id: str, user_username: str, message: str) -> SuccessfulLoginMessage:
    notification_preferences: NotificationPreferences = await retrieve_user_notification_preferences(database_session, user_username= user_username)
    return SuccessfulLoginMessage(
        message= message,
        id= user_id,
        username= user_username,
        notificationPreferences=notification_preferences
    )


@router.post('/login')
async def login(login_data: LoginData, database_session: AsyncSession = Depends(get_session)) -> ErrorMessage | SuccessfulLoginMessage:
    if not login_data:
        return ErrorMessage(error= "Username and password are required.")

    error_message: str = "Invalid username or password."
    username = login_data.username
    password = login_data.password

    if not await check_if_user_exists(database_session, user_username= username):
        return ErrorMessage(error= error_message)

    valid_password_attempt, essential_user_info = await check_password(database_session, password, username= username)

    if valid_password_attempt:

        try:
            return await send_login_success(
                database_session= database_session,
                user_id= essential_user_info["id"],
                user_username= username,
                message= "Login successful."
            )
        except Exception as e: pass

    return ErrorMessage(
        error= error_message
    )

@router.post('/register')
async def register(user_data: UserRegistration, database_session: AsyncSession = Depends(get_session)) -> ErrorMessage | SuccessfulLoginMessage:
    if not user_data:
        return ErrorMessage(error= "Username and password are required.")

    username = user_data.username

    if await check_if_user_exists(database_session, user_username= username):
        return ErrorMessage(error= "Username already exists.")

    new_uuid = str(uuid.uuid4())
    hashed_password = bcrypt.hashpw(user_data.password.encode(), bcrypt.gensalt())

    data_for_procedure = {
        "user_id": new_uuid,
        "username": username,
        "password": hashed_password,
        "is_public": user_data.is_public,
    }

    try:
        await register_user_procedure(database_session, data_for_procedure)
        return await send_login_success(
            database_session= database_session,
            user_id= new_uuid,
            user_username= username,
            message= "Registration successful."
        )
    except Exception as e:
        return ErrorMessage(error= "User registration failed: " + str(e))

@router.get('/')
async def get_user(user_uuid: str | None = Query(None), username: str | None = Query(None)) -> ErrorMessage | Any:
    error_message: str = "User not found."
    try:
        if user_uuid is None and username is None:
            return ErrorMessage(error= "Must provide either user_uuid or username.")
        if username is not None:
            user_uuid = UUID_INDEX[username]
        user_status, user_obj = find_user(user_uuid)
        if not user_status or user_obj is None:
            return ErrorMessage(error= error_message)
        return user_obj.to_dict()
    except KeyError:
        return ErrorMessage(error= error_message)


@router.get('/{user_uuid}/preferences')
async def get_user_preferences(user_uuid: str, request: Request):
    user_status, user_obj = find_user(user_uuid)
    if not user_status or not user_obj:
        return ErrorMessage(error= "User not found.")

    return Settings(
        id = user_obj.id,
        notificationPreferences = user_obj.allow_notifications,
        profilePicture = format_pfp_link(request, user_obj.profile_picture),
        username = user_obj.username,
        isPublic = user_obj.is_public,
        messagePreferences = user_obj.message_preferences.value,
    )


@router.post('/{user_uuid}/preferences')
async def update_user_preferences(user_uuid: str, request: Request):

    def update_notification_prop(prop: str, addon: str):
        if len(prop) > 0:
            prop += f", {addon}"
        else:
            prop += addon
        return prop

    """
    Unified handler:
      - JSON bodies update preferences/username/public/message prefs.
      - multipart/form-data can also include 'profile_picture' file upload
        plus optional fields as strings.
    """
    success_message = "User preferences updated successfully."

    # ---- Parse body (supports JSON or multipart) ----
    content_type = request.headers.get("content-type", "") or ""
    notification_preferences = None
    profile_picture: UploadFile | None = None
    username = None
    is_public = None
    message_preferences = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        print("[prefs] multipart keys:", list(form.keys()))
        profile_picture = form.get("profile_picture")  # UploadFile or None
        username = form.get("username")
        is_public = form.get("is_public")
        message_preferences = form.get("message_preferences")
        np_raw = form.get("notification_preferences")
        if np_raw:
            try:
                notification_preferences = json.loads(np_raw)
            except json.JSONDecodeError:
                return ErrorMessage(error= "Invalid notification_preferences JSON.")
    else:
        try:
            data = await request.json()
        except Exception:
            data = {}
        if not data:
            return ErrorMessage(error= "No data provided.")
        notification_preferences = data.get('notification_preferences')
        profile_picture = None
        username = data.get('username')
        is_public = data.get('is_public')
        message_preferences = data.get('message_preferences')

    # ---- Load user ----
    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        return ErrorMessage(error= "User not found.")

    notification_prop = ""

    try:
        # ---- Notification preferences ----
        if notification_preferences is not None:
            essential = bool(notification_preferences.get("essential", False))
            messages = bool(notification_preferences.get("messages", False))
            user_obj.allow_notifications["essential"] = essential
            user_obj.allow_notifications["messages"] = messages
            success_message = "Your notification preferences have been updated successfully."

        # ---- Profile picture upload (multipart) ----
        if profile_picture is not None:
            ctype = getattr(profile_picture, "content_type", None)
            if ctype not in {"image/jpeg", "image/png"}:
                return ErrorMessage(error= "Unsupported image type. Use JPG or PNG.")

            # Decide extension from content-type or filename
            ext = mimetypes.guess_extension(ctype) or Path(profile_picture.filename or "").suffix.lower() or ".jpg"
            dest_path = AVATAR_DIR / f"{user_uuid}{ext}"
            await _save_upload(profile_picture, dest_path)

            # Persist a URL that your frontend can load (served by StaticFiles in app.py)
            public_url = f"/media/avatars/{dest_path.name}"
            user_obj.profile_picture = public_url

            notification_prop = update_notification_prop(notification_prop, "profile picture updated")
            success_message = "Your profile photo was updated."

        # ---- Username ----
        if username is not None:
            old_username = user_obj.username
            user_obj.username = username

            UUID_INDEX.rename(old_username= old_username, new_username= username)

            notification_prop = update_notification_prop(notification_prop, f"Username updated: @{old_username} -> @{username}")
            success_message = f"Your username has been updated to @{username}."

        # ---- Public/private ----
        if is_public is not None:
            parsed_public = _to_bool(is_public)
            if parsed_public is None:
                return ErrorMessage(error= "(Internal Error) Invalid value for is_public.")
            user_obj.is_public = parsed_public

            notification_prop = update_notification_prop(notification_prop, f"Public status updated: {'Public' if parsed_public else 'Private'}")
            success_message = f"Your account type has been set to {'Public' if parsed_public else 'Private'}."

        # ---- Message preferences ----
        if message_preferences is not None:
            try:
                old_message_preferences = user_obj.message_preferences
                user_obj.update_message_preferences(message_preferences)
                notification_prop = update_notification_prop(notification_prop, f"Message preferences updated: {old_message_preferences.value} -> {user_obj.message_preferences.value}")
                success_message = "Your message preferences have been updated."
            except ValueError as ve:
                return ErrorMessage(error= str(ve))

        print(notification_prop)
        if len(notification_prop) > 0:
            print("ADDING NOTIFICATION")
            user_obj.add_notification(f"Updated Profile: {notification_prop}", "update")
            print("ADDED NOTIFICATION")

        USER_MANAGER.save()
        if username is not None: UUID_INDEX.save()


        payload = {"message": success_message}
        if getattr(user_obj, "profile_picture", None):
            payload["profilePicture"] = user_obj.profile_picture
        return payload

    except HTTPException:
        raise
    except Exception as e:
        print("[prefs] error:", e)
        return ErrorMessage(error= "User preferences not updated: " + str(e))

@router.get('/{user_uuid}/followers')
def get_user_followers(user_uuid: str):
    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        return ErrorMessage(error= "User not found.")

    follower_info = []
    followers_ids_list = list(user_obj.followers)

    for follower_id in followers_ids_list:
        follower_status, follower_obj = find_user(follower_id)
        if not follower_status or follower_obj is None: continue
        follower_info.append(follower_obj.to_dict())

    return follower_info

@router.put('/{user_uuid}/notifications')
async def update_user_notifications(user_uuid: str, request: Request):
    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        return ErrorMessage(error= "User not found.")

    data = await request.json()

    deleted_notification_index = data.get('notification_index')
    if deleted_notification_index is None:
        return ErrorMessage(error= "notification_index is required.")

    user_obj.notifications.pop(deleted_notification_index)
    USER_MANAGER.save()
    return {"message": "Notification deleted successfully."}

@router.delete('/{user_uuid}/notifications')
async def clear_user_notifications(user_uuid: str, request: Request):
    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        return ErrorMessage(error= "User not found.")

    user_obj.notifications.clear()
    USER_MANAGER.save()
    return {"message": "Notifications cleared successfully."}

@router.get('/{user_uuid}/notifications')
async def get_user_notifications(user_uuid: str, request: Request):
    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        return ErrorMessage(error= "User not found.")
    return user_obj.notifications

@router.get('/profiles/')
async def get_user_profile(request: Request, target_profile_uuid: str | None = Query(None), target_profile_username: str | None = Query(None), viewer_uuid: str | None = Query(None)):
    if target_profile_uuid is None and target_profile_username is None:
        return ErrorMessage(error= "Must provide either target_profile_uuid or target_profile_username.")

    if target_profile_username is not None:
        try:
            target_profile_uuid: str = UUID_INDEX[target_profile_username]
        except KeyError:
            return ErrorMessage(error= f"User @{target_profile_username} not found.")

    target_status, target_obj = find_user(target_profile_uuid)
    if not target_status or target_obj is None:
        return ErrorMessage(error= "Target user not found.")

    if viewer_uuid != "null":
        viewer_status, viewer_obj = find_user(viewer_uuid)
        if not viewer_status or viewer_obj is None:
            return ErrorMessage(error= "Viewer user not found.")

        is_self: bool = viewer_obj.id == target_obj.id
        viewer_follows_user: bool = viewer_obj.id in target_obj.followers
        user_follows_viewer: bool = target_obj.id in viewer_obj.followers
        pending_follow_request: bool = viewer_obj.id in target_obj.follow_requests
        is_blocked_by_user: bool = viewer_obj.id in target_obj.blocked_users
        viewer_blocked_user: bool = target_obj.id in viewer_obj.blocked_users

        can_view_profile: bool = True if not (is_blocked_by_user or viewer_blocked_user) else False
        can_follow: bool = True if not is_blocked_by_user else False

    else:
        is_self: bool = viewer_uuid == target_obj.id
        viewer_follows_user: bool = False
        user_follows_viewer: bool = False
        pending_follow_request: bool = False
        is_blocked_by_user: bool = False
        viewer_blocked_user: bool = False

        can_view_profile: bool = True
        can_follow: bool = True

    can_message: bool = True if not target_obj.message_preferences.value == "NONE" else False

    follower_count: FollowerCount = format_count(len(target_obj.followers))
    following_count: FollowingCount = format_count(len(target_obj.following))

    return Profile(
        id= target_obj.id,
        username= target_obj.username,
        profilePicture= format_pfp_link(request, target_obj.profile_picture),
        publicStatus= target_obj.is_public,
        stats= Stats(
            followersCount= follower_count,
            followingCount= following_count
        ),
        relations = Relations(
            isSelf= is_self,
            viewerFollowsUser= viewer_follows_user,
            userFollowsViewer= user_follows_viewer,
            pendingFollowRequest= pending_follow_request,
            isBlockedByUser= is_blocked_by_user,
            viewerBlockedUser= viewer_blocked_user
        ),
        permissions = Permissions(
            canViewProfile= can_view_profile,
            canMessage= can_message,
            canFollow= can_follow
        )
    )

@router.post('/{user_uuid}/follow')
async def follow_user(user_uuid: str, request: Request):
    data = await request.json()
    target_id = data.get('target_id')
    follower_id = data.get('follower_id')

    if not target_id or not follower_id:
        return ErrorMessage(error= "target_id and follower_id are required.")

    if follower_id != user_uuid:
        return ErrorMessage(error= f"follower_id must match the authenticated user {user_uuid}." )

    target_status, target_user_obj = find_user(target_id)
    if not target_status or target_user_obj is None:
        return ErrorMessage(error= "Target user not found.")

    follower_status, follower_user_obj = find_user(follower_id)
    if not follower_status or follower_user_obj is None:
        return ErrorMessage(error= "Follower user not found.")

    if target_id in follower_user_obj.blocked_users:
        return ErrorMessage(error= f"'@{target_user_obj.username}' is blocked.")

    if follower_id in target_user_obj.blocked_users:
        return ErrorMessage(error= f"'@{follower_user_obj.username}' is blocked.")

    if follower_id in target_user_obj.followers or follower_id in target_user_obj.follow_requests:
        return ErrorMessage(error= f"You are already following @{target_user_obj.username}.")
    target_user_public_status = target_user_obj.is_public

    if target_user_public_status:
        target_user_obj.followers.add(follower_id)
        follower_user_obj.following.add(target_id)
        success_message = f"You started following @{target_user_obj.username}."
        target_message = f"@{follower_user_obj.username} is now following you."
    else:
        target_user_obj.follow_requests.add(follower_id)
        success_message = f"You have sent a follow request to @{target_user_obj.username}."
        target_message = f"@{follower_user_obj.username} has requested to follow you."

    follower_user_obj.add_notification(success_message, "profile", {
        "uuid": target_id
    })

    target_user_obj.add_notification(target_message, "profile", {
        "uuid": follower_id
    })

    USER_MANAGER.save()

    return {
    "message": success_message,
    "notificationForRecipient": {
        "recipient_uuid": target_id,
        "frontend_notification_payload": {
            "function": "toProfile",
            "uuid": follower_id,
            "message": target_message,
        }
    }
}

@router.post('/{user_uuid}/unfollow')
async def unfollow_user(user_uuid: str, request: Request):
    # {target_id: targetId, unfollower_id: actorId}
    data = await request.json()
    target_id = data.get('target_id')
    unfollower_id = data.get('unfollower_id')

    if not target_id or not unfollower_id:
        return ErrorMessage(error= "target_id and unfollower_id are required.")

    if unfollower_id != user_uuid:
        return ErrorMessage(error= f"unfollower_id must match the authenticated user {user_uuid}." )

    target_status, target_user_obj = find_user(target_id)
    if not target_status or target_user_obj is None:
        return ErrorMessage(error= "Target user not found.")

    unfollower_status, unfollower_user_obj = find_user(unfollower_id)
    if not unfollower_status or unfollower_user_obj is None:
        return ErrorMessage(error= "Unfollower user not found.")

    if unfollower_id not in target_user_obj.followers:
        return ErrorMessage(error= f"You are not following @{target_user_obj.username}." )

    target_user_obj.followers.remove(unfollower_id)
    unfollower_user_obj.following.remove(target_id)

    success_message = f"You stopped following @{target_user_obj.username}."

    unfollower_user_obj.add_notification(success_message, "profile", {
        "uuid": target_id
    })

    USER_MANAGER.save()

    return {
        "message": success_message,
    }

@router.post('/{user_uuid}/cancel_follow_request')
async def cancel_follow_request(user_uuid: str, request: Request):
    data = await request.json()
    target_id = data.get('target_id')
    request_sender_id = data.get('request_sender_id')

    if not target_id or not request_sender_id:
        return ErrorMessage(error= "target_id and request_sender_id are required.")

    if request_sender_id != user_uuid:
        return ErrorMessage(error= f"request_sender_id must match the authenticated user {user_uuid}." )

    target_status, target_user_obj = find_user(target_id)
    if not target_status or target_user_obj is None:
        return ErrorMessage(error= "Target user not found.")

    request_sender_status, request_sender_user_obj = find_user(request_sender_id)
    if not request_sender_status or request_sender_user_obj is None:
        return ErrorMessage(error= "Request sender user not found.")

    if request_sender_id not in target_user_obj.follow_requests:
        return ErrorMessage(error= f"You have no pending follow request to @{target_user_obj.username}." )

    target_user_obj.follow_requests.remove(request_sender_id)
    USER_MANAGER.save()

    return {
        "message": f"You have cancelled your follow request to @{target_user_obj.username}."
    }

@router.get('/{user_uuid}/follow_requests')
async def get_follow_requests(user_uuid: str, request: Request):
    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        return ErrorMessage(error= "User not found.")

    follow_requests = []
    user_follow_requests_ids_list = list(user_obj.follow_requests)

    for follow_request_id in user_follow_requests_ids_list:
        follow_request_status, follow_request_obj = find_user(follow_request_id)
        if not follow_request_status or follow_request_obj is None: continue
        user_info = EssentialInfo(
            id= follow_request_obj.id,
            username= follow_request_obj.username,
            profilePicture= format_pfp_link(request, follow_request_obj.profile_picture),
            publicStatus= follow_request_obj.is_public
        )
        follow_requests.append(user_info)
    return follow_requests

@router.post('/{user_uuid}/follow_requests')
async def accept_follow_request(user_uuid: str, request: Request):
    data = await request.json()
    target_id = data.get('target_id')
    follower_id = data.get('follower_id')

    if not target_id or not follower_id:
        return ErrorMessage(error= "target_id and follower_id are required.")

    if target_id != user_uuid:
        return ErrorMessage(error= f"target_id must match the authenticated user {user_uuid}." )

    target_status, target_user_obj = find_user(target_id)
    if not target_status or target_user_obj is None:
        return ErrorMessage(error= "Target user not found.")

    follower_status, follower_obj = find_user(follower_id)
    if not follower_status or follower_obj is None:
        return ErrorMessage(error= "Follower user not found.")

    if follower_id not in target_user_obj.follow_requests:
        return ErrorMessage(error= f"You have no pending follow request to @{target_user_obj.username}." )

    target_user_obj.followers.add(follower_id)
    target_user_obj.follow_requests.remove(follower_id)
    follower_obj.following.add(target_id)

    target_success_message = f"You accepted @{target_user_obj.username}'s follow request."
    follower_success_message = f"@{target_user_obj.username} has accepted your follow request."

    target_user_obj.add_notification(target_success_message, "profile", {
        "uuid": follower_id
    })

    follower_obj.add_notification(follower_success_message, "profile", {
        "uuid": target_id
    })

    USER_MANAGER.save()

    return {
        "message": target_success_message,
        "notificationForRecipient": {
            "recipient_uuid": follower_id,
            "frontend_notification_payload": {
                "function": "toProfile",
                "uuid": target_id,
                "message": follower_success_message,
            }
        }
    }

@router.delete('/{user_uuid}/follow_requests')
async def decline_follow_request(user_uuid: str, request: Request):
    data = await request.json()
    target_id = data.get('target_id')
    follower_id = data.get('follower_id')

    if not target_id or not follower_id:
        return ErrorMessage(error= "target_id and follower_id are required.")

    if target_id != user_uuid:
        return ErrorMessage(error= f"target_id must match the authenticated user {user_uuid}." )

    target_status, target_user_obj = find_user(target_id)
    if not target_status or target_user_obj is None:
        return ErrorMessage(error= "Target user not found.")

    follower_status, follower_obj = find_user(follower_id)
    if not follower_status or follower_obj is None:
        return ErrorMessage(error= "Follower user not found.")

    if follower_id not in target_user_obj.follow_requests:
        return ErrorMessage(error= f"You have no pending follow request to @{target_user_obj.username}." )

    target_user_obj.follow_requests.remove(follower_id)
    USER_MANAGER.save()

    return {
        "message": f"You declined @{target_user_obj.username}'s follow request."
    }