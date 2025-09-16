from __future__ import annotations
from pydantic import BaseModel
from typing import Dict

from backend.pydantic_models.pydantic_variables import UserUUID, FollowingCount, FollowerCount


class ErrorMessage(BaseModel):
    error: str

class EssentialInfo(BaseModel):
    id: UserUUID
    username: str
    profilePicture: str | None
    publicStatus: bool

class Settings(BaseModel):
    id: UserUUID
    notificationPreferences: Dict[str, bool]
    profilePicture: str | None
    username: str
    isPublic: bool
    messagePreferences: str

class Profile(BaseModel):
    id: UserUUID
    username: str
    profilePicture: str | None
    publicStatus: bool
    stats: Stats
    relations: Relations
    permissions: Permissions

class Stats(BaseModel):
    followersCount: FollowerCount
    followingCount: FollowingCount

class Relations(BaseModel):
    isSelf: bool
    viewerFollowsUser: bool
    userFollowsViewer: bool
    pendingFollowRequest: bool
    isBlockedByUser: bool
    viewerBlockedUser: bool

class Permissions(BaseModel):
    canViewProfile: bool
    canMessage: bool
    canFollow: bool