from backend.instances import USER_MANAGER, CHAT_MANAGER, UUID_INDEX, DIRECT_CHAT_INDEX_MANAGER

def save_all_databases() -> None:
    USER_MANAGER.save()
    CHAT_MANAGER.save_chat_database()
    UUID_INDEX.save()
    if hasattr(DIRECT_CHAT_INDEX_MANAGER, "save"):
        DIRECT_CHAT_INDEX_MANAGER.save()
