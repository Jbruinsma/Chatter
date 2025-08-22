from typing import Dict, Any

from starlette.websockets import WebSocket

from backend.models.databases.chat_database import ChatDatabase
from backend.models.databases.user_database import UserDatabase

USER_MANAGER = UserDatabase("user_manager.pkl")
CHAT_MANAGER = ChatDatabase("chat_manager.pkl")
