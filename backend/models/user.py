from typing import Dict, List
from enum import Enum
import bcrypt

from backend.utils.formatting import format_notification_timestamp



class User:

    def __init__(self, uuid: str, username: str, password: str, is_public: bool):
        self.id: str = uuid
        self.profile_picture: str | None = None
        self.username: str = username
        self.password: bytes = self._hash_password(password)
        self.is_public: bool = is_public

        self.followers: set = set()
        self.following: set = set()
        self.blocked_users: set = set()
        self.follow_requests: set = set()

        self.message_preferences: Enum = MessagePreference.ANYONE if self.is_public else MessagePreference.FRIENDS

        self.chat_ids: Dict[str, set] = {
            "main": set(),
            "requests": set()
        }

        self.allow_notifications= {
            "essential": True,
            "messages": False
        }
        self.notifications: List[Dict[str, str]] = []

    def __str__(self) -> str:
        return f"User: Username: {self.username}, UUID: {self.id}, Chat IDS: {self.chat_ids}, Public status: {self.is_public}"

    @staticmethod
    def _hash_password(plain_text) -> bytes:
        salt : bytes = bcrypt.gensalt()
        return bcrypt.hashpw(plain_text.encode('utf-8'), salt)

    def check_password(self, attempt) -> bool:
        return bcrypt.checkpw(attempt.encode('utf-8'), self.password)

    def update_message_preference(self, preference: str):
        if preference == "ANYONE":
            self.message_preferences = MessagePreference.ANYONE
        elif preference == "FRIENDS":
            self.message_preferences = MessagePreference.FRIENDS
        elif preference == "NONE":
            self.message_preferences = MessagePreference.NONE
        else:
            raise ValueError("Invalid preference")

    def update_message_preferences(self, new_preference: str):
        if new_preference == "ANYONE":
            self.message_preferences = MessagePreference.ANYONE

        elif new_preference == "FRIENDS":
            self.message_preferences = MessagePreference.FRIENDS

        elif new_preference == "NONE":
            self.message_preferences = MessagePreference.NONE

        else:
            raise ValueError("Invalid preference")

    def add_notification(self, message, notification_type, extra= None):
        notification = {
            "message": message,
            "timestamp": format_notification_timestamp(),
            "type": notification_type,
            "extra": extra
        }
        self.notifications.append(notification)

    def essentials_to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "profilePicture": self.profile_picture,
            "publicStatus": self.is_public,
        }

    def settings_to_dict(self):
        return {
            "id": self.id,
            "notificationPreferences": self.allow_notifications,
            "profilePicture": self.profile_picture,
            "username": self.username,
            "isPublic": self.is_public,
            "messagePreferences": self.message_preferences.value,
        }

    def to_dict(self):
        return {
            "id": self.id,
            "profile_picture": self.profile_picture,
            "username": self.username,
            "message_preferences": self.message_preferences.value,
            "followers": list(self.followers),
            "following": list(self.following),
            "blocked_users": list(self.blocked_users),
            "follow_requests": list(self.follow_requests),
            "chat_ids": list(self.chat_ids.get("main", [])),
            "chat_requests": list(self.chat_ids.get("requests", [])),
            "public_status": self.is_public,
            "notifications": self.notifications,
            "notification_settings": self.allow_notifications,
        }

class MessagePreference(Enum):
    ANYONE = "ANYONE"
    FRIENDS = "FRIENDS"
    NONE = "NONE"