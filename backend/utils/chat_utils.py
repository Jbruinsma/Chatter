from backend.instances import CHAT_MANAGER


def find_chat(chat_id):
    chat_node = CHAT_MANAGER.search_for_chat(chat_id)
    if chat_node is None:
        return False, None
    chat = chat_node.value
    return True, chat