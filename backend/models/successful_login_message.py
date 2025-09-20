from __future__ import annotations

from pydantic import BaseModel

from backend.models.notification_preferences import NotificationPreferences


class SuccessfulLoginMessage(BaseModel):
    message: str
    id: str
    username: str
    notificationPreferences: NotificationPreferences