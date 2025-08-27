from typing import Dict, List
import bcrypt


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

        self.chat_ids: set = set()
        self.public_status: bool = is_public

    def __str__(self) -> str:
        return f"User: {self.username}, {self.followers}, {self.following}, {self.chat_ids}, {self.public_status}"

    @staticmethod
    def _hash_password(plain_text) -> bytes:
        salt : bytes = bcrypt.gensalt()
        return bcrypt.hashpw(plain_text.encode('utf-8'), salt)

    def check_password(self, attempt) -> bool:
        return bcrypt.checkpw(attempt.encode('utf-8'), self.password)

    def to_dict(self):
        return {
            "id": self.id,
            "profile_picture": self.profile_picture,
            "username": self.username,
            "followers": list(self.followers),
            "following": list(self.following),
            "blocked_users": list(self.blocked_users),
            "follow_requests": list(self.follow_requests),
            "chat_ids": list(self.chat_ids),
            "public_status": self.public_status
        }