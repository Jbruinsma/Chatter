from fastapi import APIRouter, Request, Query
import uuid

from typing import Dict, Any

from backend.instances import UUID_INDEX, USER_MANAGER
from backend.models.user import User
from backend.utils.user_utils import find_user

router = APIRouter()

@router.post('/login')
async def login(request: Request):
    error_message = "Username or password is Invalid."
    data = await request.json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return {"error": "Username and password are required."}

    try:
        user_uuid = UUID_INDEX[username]
    except KeyError:
        return {"error": error_message}

    if user_uuid is not None:
        user_status, user_obj = find_user(user_uuid)
        if not user_status or user_obj is None:
            return {"error": error_message}

        correct_password = user_obj.check_password(password)
        if not correct_password:
            return {"error": error_message}
        else:
            return {
                "message": "Login successful.",
                "id": user_uuid,
                "username": username,
            }

    return {"error": error_message}

@router.post('/register')
async def register(request: Request):
    data = await request.json()
    username = data.get('username')
    password = data.get('password')
    is_public = data.get('is_public')

    if not username or not password:
        return {"error": "Username and password are required."}

    if username in UUID_INDEX:
        return {"error": "Username already exists."}

    UUID_INDEX[username] = str(uuid.uuid4())
    new_user_uuid = UUID_INDEX[username]
    new_user = User(uuid= new_user_uuid, username= username, password= password, is_public= is_public)

    USER_MANAGER.add_user(new_user_uuid, new_user)
    USER_MANAGER.save()

    return {
        "message": "Registration successful.",
        "id": new_user_uuid,
        "username": username,
    }

@router.get('/')
async def get_user(user_uuid: str | None = Query(None), username: str | None = Query(None)) -> Dict[str, Any]:
    error: Dict[str, str] = {"error": "User not found."}
    try:
        if user_uuid is None and username is None:
            return {"error": "Must provide either user_uuid or username."}
        if username is not None:
            user_uuid = UUID_INDEX[username]
        user_status, user_obj = find_user(user_uuid)
        if not user_status or user_obj is None:
            return error
        return user_obj.to_dict()
    except KeyError:
        return error