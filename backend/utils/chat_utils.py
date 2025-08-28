from backend.instances import CHAT_MANAGER


def find_chat(chat_id):
    chat_node = CHAT_MANAGER.search_for_chat(chat_id)
    if chat_node is None:
        return False, None
    chat = chat_node.value
    return True, chat

# lookups.py
from typing import Optional, Callable

# Inject these from your app:
# - load_user(uuid) -> User (must have .chat_ids: set[str])
# - load_chat(chat_id) -> Chat (must have .chat_type and .participants: set[str])
# - direct_index: DirectIndex instance

def get_direct_chat_id(
    a_uuid: str,
    b_uuid: str,
    direct_index,
    load_user: Callable[[str], "User"],
    load_chat: Callable[[str], "Chat"]
) -> Optional[str]:
    """
    1) Try O(1) index
    2) If missing, repair by scanning ONLY the intersection of A and B chat_ids
    3) Cache the repaired result back into the index
    """
    # 1) O(1) path
    chat_id = direct_index.get(a_uuid, b_uuid)
    if chat_id:
        return chat_id

    # 2) Repair via small scan of intersection
    a_chats = load_user(a_uuid).chat_ids
    b_chats = load_user(b_uuid).chat_ids
    for cid in (a_chats & b_chats):
        chat = load_chat(cid)
        # tolerate old data by checking both explicit type and participant count
        if getattr(chat, "chat_type", None) == "direct" and chat.participants == {a_uuid, b_uuid}:
            direct_index.put(a_uuid, b_uuid, cid)
            return cid
        if getattr(chat, "chat_type", None) is None and chat.participants == {a_uuid, b_uuid}:
            # legacy: two-party chat recorded as group; still fine
            direct_index.put(a_uuid, b_uuid, cid)
            return cid

    return None

import threading
_create_dm_lock = threading.Lock()

def ensure_direct_chat(
    a_uuid: str,
    b_uuid: str,
    direct_index,
    load_user, save_user,
    load_chat, save_chat,
    create_chat  # fn(chat_name, chat_cover, owner_id, participant_ids, participant_permissions, chat_type) -> Chat
) -> str:
    """
    Returns the existing direct chat id if present, otherwise creates it exactly once.
    """
    # Fast path
    cid = direct_index.get(a_uuid, b_uuid)
    if cid:
        return cid

    with _create_dm_lock:
        # Re-check under lock
        cid = direct_index.get(a_uuid, b_uuid)
        if cid:
            return cid

        # Guardrails: blocks, etc. (if you enforce that)
        a = load_user(a_uuid)
        b = load_user(b_uuid)
        if b_uuid in getattr(a, "blocked_users", set()) or a_uuid in getattr(b, "blocked_users", set()):
            raise PermissionError("Cannot start a direct chat due to blocking.")

        # Create the direct chat with your existing "owner-only editor" logic
        perms = {
            a_uuid: {"can_edit": True},
            b_uuid: {"can_edit": False},
        }
        chat = create_chat(
            chat_name="", chat_cover="", owner_id=a_uuid,
            participant_ids=[a_uuid, b_uuid],
            participant_permissions=perms,
            chat_type="direct",
        )
        save_chat(chat)

        # Attach to each user's chat_ids (and any per-user caches you keep)
        a.chat_ids.add(chat.chat_id); b.chat_ids.add(chat.chat_id)
        save_user(a); save_user(b)

        # Index the pair
        direct_index.put(a_uuid, b_uuid, chat.chat_id)
        return chat.chat_id
