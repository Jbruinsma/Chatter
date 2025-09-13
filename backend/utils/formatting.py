from typing import Any, Dict, Union
from datetime import datetime, timezone

TimeLike = Union[datetime, str, int, float]

def _to_iso8601_z(value: TimeLike) -> str:
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    if isinstance(value, (int, float)):

        secs = value / 1000.0 if value >= 1_000_000_000_000 else value
        return datetime.fromtimestamp(secs, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return value

def format_message_dict(
    chat_id: str,
    message_type: str,
    message_id: str,
    sender_id: str,
    message: str,
    time_sent: TimeLike
) -> Dict[str, Any]:
    return {
        "chat_id": chat_id,
        "message_type": message_type,
        "message_id": message_id,
        "sender_id": sender_id,
        "message": message,
        "time_sent": _to_iso8601_z(time_sent),
    }

def format_message_dict_for_json(
        chat_id: str,
        message_type: str,
        message_id: str,
        sender_id: str,
        message: str,
        time_sent: datetime
):
    return {
        "messageStatus": "delivered",
        "chatId": chat_id,
        "messageType": message_type,
        "messageId": message_id,
        "senderId": sender_id,
        "message": message,
        "timeSent": time_sent
    }

from datetime import datetime, timezone, timedelta

def format_notification_timestamp() -> str:
    """
    Return current local time as an ISO-8601 string with offset (JSON-safe).
    Examples:
      '2025-09-08T11:12:34.567-04:00'  (local offset)
      '2025-09-08T15:12:34.567Z'       (UTC)
    """
    dt = datetime.now().astimezone()  # local tz with offset
    if dt.utcoffset() == timedelta(0):
        return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return dt.isoformat(timespec="milliseconds")

def format_count(count: int) -> str:
    if count >= 10000:
        return f"{count // 1000}K"
    elif count >= 1000000:
        return f"{count // 1000000}M"
    return str(count)