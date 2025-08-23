from fastapi import APIRouter

router = APIRouter()

@router.post('/login')
async def login():
    data = await request.json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return {"error": "Username and password are required."}

    return {"message": "Login successful."}

@router.post('/register')
async def register():
    return {"message": "Register successful."}