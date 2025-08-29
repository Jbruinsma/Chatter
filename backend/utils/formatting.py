from datetime import datetime
from typing import Dict

def format_message_dict(
        chat_id: str,
        chat_type: str,
        message_id: str,
        sender_id: str,
        message: str,
        time_sent: datetime
) -> Dict[str, str | datetime]:
    return {
        "chat_id": chat_id,
        "message_type": chat_type,
        "message_id": message_id,
        "sender_id": sender_id,
        "message": message,
        "time_sent": time_sent
    }

def format_message_dict_for_json(
        chat_id: str,
        chat_type: str,
        message_id: str,
        sender_id: str,
        message: str,
        time_sent: datetime
):
    return {
        "chatId": chat_id,
        "messageType": chat_type,
        "messageId": message_id,
        "senderId": sender_id,
        "message": message,
        "timeSent": time_sent
    }