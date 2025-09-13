from __future__ import annotations
from pydantic import BaseModel
from typing import Dict


class ErrorMessage(BaseModel):
    error: str

class EssentialInfo(BaseModel):
    id: str
    username: str
    profilePicture: str
    publicStatus: bool

class Settings(BaseModel):
    id: str
    notificationPreferences: Dict[str, bool]
    profilePicture: str
    username: str
    isPublic: bool
    messagePreferences: str

class Profile(BaseModel):
    id: str
    username: str
    profilePicture: str
    publicStatus: bool
    stats: Stats
    relations: Relations
    permissions: Permissions

class Stats(BaseModel):
    followersCount: int
    followingCount: int

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