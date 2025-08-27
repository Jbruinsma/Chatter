from fastapi import APIRouter, Request
import uuid

from backend.instances import UUID_INDEX, USER_MANAGER
from backend.models.user_new import UserNew
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
    new_user = UserNew(uuid= new_user_uuid, username= username, password= password, is_public= is_public)

    USER_MANAGER.add_user(new_user_uuid, new_user)
    USER_MANAGER.save()

    return {
        "message": "Registration successful.",
        "id": new_user_uuid,
        "username": username,
    }

@router.get('/{username}')
async def get_user(username: str):
    error_message = "User not found."
    if username not in UUID_INDEX:
        return {"error": error_message}

    user_uuid = UUID_INDEX[username]
    user_status, user_obj = find_user(user_uuid)
    if not user_status or user_obj is None:
        return {"error": error_message}

    return user_obj.to_dict()