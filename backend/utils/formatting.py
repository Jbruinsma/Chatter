from datetime import datetime, timezone
from uuid import uuid4


def format_websocket_json(subscription_type, data):
    return {"subscription_type": subscription_type, "data": data}

def format_dashboard_json(data):
    return {
        "chat_id": data.get("id"),
        "last_message": data.get("message"),
        "last_message_time": data.get("timestamp")
    }

def format_chat_dict(chat_id, sender, message_text):
    return {
        "message_id": str(uuid4()),
        "type": "message",
        "chat_id": chat_id,
        "sender": sender,
        "message": message_text,
        "time_sent": now_iso(),
    }

def format_chat_dict_for_json(message_id, message_type, chat_id, sender, message_text, timestamp):
    return {
        "message_id": message_id,
        "type": message_type,
        "chat_id": chat_id,
        "sender": sender,
        "message": message_text,
        "time_sent": timestamp,
    }

def format_new_chat_dict(chat_id, chat_name, participant_list, time_created, unread_messages_by):
    return {
        "event": "new_chat",
        "data": {
            "chat_id": chat_id,
            "chat_name": chat_name,
            "participants": participant_list,
        }
    }

def now_iso():
    return datetime.now(timezone.utc).isoformat()