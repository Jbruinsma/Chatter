from pydantic import BaseModel


class NotificationPreferences(BaseModel):
    essential: bool
    messages: bool