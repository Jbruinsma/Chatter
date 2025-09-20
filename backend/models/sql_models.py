from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table= True):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    username: str = Field(unique=True, index=True)
    password: bytes
    is_public: bool
    profile_picture: Optional[str] = None
    message_preference_type: str = Field(default="FRIENDS")
    allow_essential_notifications: bool = Field(default=True)
    allow_message_notifications: bool = Field(default=False)

class Chat(SQLModel, table=True):
    __tablename__ = "chats"

    chat_id: str = Field(primary_key=True)
    owner_id: str = Field(foreign_key="users.id")
    chat_name: str
    chat_cover: Optional[str] = None
    created_at: str
    chat_type: str