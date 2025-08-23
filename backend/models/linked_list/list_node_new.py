class ListNode:

    def __init__(self, chat_id: str, message_type: str, message_id: str, sender_id: str, message: str, time_sent: str):
        self.prev = None
        self.value = {
            "chatId": chat_id,
            "messageType": chat_type,
            "messageId": message_id,
            "senderId": sender_id,
            "message": message,
            "timeSent": time_sent
        }
        self.next = None

    def __repr__(self):
        return f"ListNode({self.value})"

    def __str__(self):
        return str(self.value)