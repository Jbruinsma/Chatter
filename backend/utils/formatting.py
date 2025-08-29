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
        "chatId": chat_id,
        "messageType": chat_type,
        "messageId": message_id,
        "senderId": sender_id,
        "message": message,
        "timeSent": time_sent
    }