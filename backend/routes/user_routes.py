from fastapi import APIRouter

from backend.instances import UUID_INDEX

router = APIRouter()

@router.post('/login')
async def login():
    data = await request.json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return {"error": "Username and password are required."}

    user_uuid = UUID_INDEX[username]

    if user_uuid is not None:
        pass

    return {"message": "Login successful."}

@router.post('/register')
async def register():
    return {"message": "Register successful."}