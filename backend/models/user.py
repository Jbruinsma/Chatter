from __future__ import annotations

from typing import Dict, List
import bcrypt

from backend.utils.user_utils import find_user


class User:
    def __init__(self, user_uuid : str, username : str, password : str, is_public : bool, is_hashed : bool =False):
        self.id : str = user_uuid
        self.username : str = username
        self.password : bytes = self._hash_password(password) if not is_hashed else password

        self.followers : set = set()
        self.following : set = set()
        self.follow_requests : set = set()
        self.blocked_users : set = set()

        self.chat_ids : set = set()

        self.profile_picture : str | None = None
        self.public_status : bool = is_public

        self.is_active : bool = False
        self.show_active : bool = False

    def __str__(self) -> str:
        return f"User(id={self.id}, username={self.username}, followers={len(self.followers)}, following={len(self.following)})"

    @staticmethod
    def _hash_password(plain_text) -> bytes:
        salt : bytes = bcrypt.gensalt()
        return bcrypt.hashpw(plain_text.encode('utf-8'), salt)

    def check_password(self, attempt) -> bool:
        return bcrypt.checkpw(attempt.encode('utf-8'), self.password)

    def add_chat_id(self, chat_id : str) -> Dict[str, str]:
        if chat_id not in self.chat_ids:
            self.chat_ids.add(chat_id)
            return {"message": f"Chat ID {chat_id} added to user {self.username}."}
        return {"message": f"Chat ID {chat_id} already exists for user {self.username}."}

    def remove_chat_id(self, chat_id : str) -> Dict[str, str]:
        if chat_id in self.chat_ids:
            self.chat_ids.remove(chat_id)
            return {"message": f"Chat ID {chat_id} removed from user {self.username}."}
        return {"message": f"Chat ID {chat_id} does not exist for user {self.username}."}

    def add_follower(self, follower : User) -> Dict[str, str]:
        follower_username : str = follower.username
        if self.public_status:
            if follower_username not in self.followers:
                self.followers.add(follower_username)
                follower.add_user_to_following(self.username)
                return {"message": f"{follower_username} is now following {self.username}."}
            return {"message": f"{follower_username} is already following {self.username}."}
        else:
            self.add_follow_request(follower_username)
            return {"message": "Follow request sent."}

    def add_follow_request(self, follower_username : str) -> None:
        if follower_username not in self.follow_requests:
            self.follow_requests.add(follower_username)

    def add_user_to_following(self, following_username : str) -> None:
        if following_username not in self.following:
            self.following.add(following_username)
        return None

    def accept_follow_request(self, follower : User) -> Dict[str, str]:
        follower_username = follower.username
        if follower_username in self.follow_requests:
            self.follow_requests.discard(follower_username)
            self.followers.add(follower_username)
            follower.add_user_to_following(self.username)
            return {"message": f"{follower_username} is now following {self.username}."}
        return {"message": f"No follow request from {follower_username}."}

    def block_user(self, user : User) -> Dict[str, str]:
        user_username = user.username
        if user_username not in self.blocked_users:
            self.blocked_users.add(user_username)
            self.followers.discard(user_username)
            self.following.discard(user_username)
            return {"message": f"{user_username} has been blocked."}
        return {"message": f"{user_username} is already blocked."}

    def unblock_user(self, user : User) -> Dict[str, str]:
        user_username = user.username
        if user_username in self.blocked_users:
            self.blocked_users.discard(user_username)
            return {"message": f"{user_username} has been unblocked."}
        return {"message": f"{user_username} is not blocked."}

    def get_chat_ids(self) -> List[str]:
        return list(self.chat_ids)

    def set_user_active(self) -> None:
        self.is_active = True

    def set_user_inactive(self) -> None:
        self.is_active = False

    def followers_to_list(self) -> List[Dict[str, str]]:
        followers_list : List[Dict[str, str]] = []
        for follower_username in self.followers:
            user_status, user_obj = find_user(follower_username)
            if user_status:
                followers_list.append(user_obj.to_dict())
        return followers_list

    def following_to_list(self) -> List[Dict[str, str]]:
        following_list : List[Dict[str, str]]= []
        for following_username in self.following:
            user_status, user_obj = find_user(following_username)
            if user_status:
                following_list.append(user_obj.to_dict())
        return following_list

    def to_dict(self) -> Dict[str, str | List[str] | bool]:
        return {
            "id": self.id,
            "username": self.username,
            "followers": list(self.followers),
            "following": list(self.following),
            "blocked_users": list(self.blocked_users),
            "follow_requests": list(self.follow_requests),
            "public_status": self.public_status,
            "profile_picture": self.profile_picture,
            "is_active": self.is_active,
            "show_active": self.show_active,
        }