from types import new_class
from typing import Optional, Callable, Tuple
import threading

from backend.instances import CHAT_MANAGER, USER_MANAGER, DIRECT_CHAT_INDEX_MANAGER
from sentry_sdk import new_scope
from sqlalchemy.testing.suite.test_reflection import users


def find_chat(chat_id):
    chat_node = CHAT_MANAGER.search_for_chat(chat_id)
    if chat_node is None:
        return False, None
    chat = chat_node.value
    return True, chat

def create_chat(
    chat_name: str,
    chat_cover: str,
    owner_id: str,
    participant_ids: set[str],
    participant_permissions: dict[str, dict[str, bool | str]],
    chat_type: Optional[str] = None
) -> Tuple[str, object]:
    participants = set(participant_ids) | {owner_id}
    chat_type = chat_type or ("direct" if len(participants) == 2 else "group")
    new_chat_id, new_chat_obj = CHAT_MANAGER.add_chat(
        chat_name=chat_name,
        chat_cover=chat_cover,
        owner_id=owner_id,
        participant_ids=list(participants),
        participant_permissions=participant_permissions,
        chat_type=chat_type,
    )
    for uid in list(copy.deepcopy(new_chat_obj.participants)):
        user_status, potential_participant_obj = find_user(uid)
        if not user_status or potential_participant_obj is None: continue
        participant_message_preference = potential_participant_obj.message_preferences
        is_friends = owner_id in potential_participant_obj.following and uid in potential_participant_obj.followers
        chat_category_for_participant = "main" if is_friends else "requests"
        if participant_message_preference == "FRIENDS" and not is_friends:
            new_chat_obj.invited_users.add(uid)
            new_chat_obj.participants.remove(uid)
        potential_participant_obj.chat_ids[chat_category_for_participant].add(new_chat_id)

    USER_MANAGER.save()
    if chat_type == "direct":
        a_uuid, b_uuid = sorted(participants)
        DIRECT_CHAT_INDEX_MANAGER.put(a_uuid, b_uuid, new_chat_id)
    CHAT_MANAGER.save_chat_database()
    return new_chat_id, new_chat_obj

def get_direct_chat_id(
    a_uuid: str,
    b_uuid: str,
    direct_index,
    load_user: Callable[[str], "User"],
    load_chat: Callable[[str], "Chat"]
) -> Optional[str]:
    chat_id = direct_index.get(a_uuid, b_uuid)
    if chat_id:
        return chat_id
    a_chats = load_user(a_uuid).chat_ids
    b_chats = load_user(b_uuid).chat_ids
    for cid in (a_chats & b_chats):
        chat = load_chat(cid)
        if getattr(chat, "chat_type", None) == "direct" and chat.participants == {a_uuid, b_uuid}:
            direct_index.put(a_uuid, b_uuid, cid)
            return cid
        if getattr(chat, "chat_type", None) is None and chat.participants == {a_uuid, b_uuid}:
            direct_index.put(a_uuid, b_uuid, cid)
            return cid
    return None


_create_dm_lock = threading.Lock()


def ensure_direct_chat(
    a_uuid: str,
    b_uuid: str,
    direct_index,
    load_user, save_user,
    load_chat, save_chat,
    create_chat
) -> str:
    cid = direct_index.get(a_uuid, b_uuid)
    if cid:
        return cid
    with _create_dm_lock:
        cid = direct_index.get(a_uuid, b_uuid)
        if cid:
            return cid
        a = load_user(a_uuid)
        b = load_user(b_uuid)
        if b_uuid in getattr(a, "blocked_users", set()) or a_uuid in getattr(b, "blocked_users", set()):
            raise PermissionError("Cannot start a direct chat due to blocking.")
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
        a.chat_ids.add(chat.chat_id)
        b.chat_ids.add(chat.chat_id)
        save_user(a)
        save_user(b)
        direct_index.put(a_uuid, b_uuid, chat.chat_id)
        return chat.chat_id


def find_direct_chat_with_user(me_uuid: str, peer_uuid: str) -> Tuple[bool, Optional[str]]:
    chat_id = DIRECT_CHAT_INDEX_MANAGER.get(me_uuid, peer_uuid)
    if chat_id:
        node = CHAT_MANAGER.search_for_chat(chat_id)
        if node is not None:
            chat = node.value
            participants = getattr(chat, "participants", set())
            chat_type = getattr(chat, "chat_type", None)
            if participants == {me_uuid, peer_uuid} and (chat_type == "direct" or chat_type is None):
                return True, chat_id
    me_node = USER_MANAGER.search_for_user(me_uuid)
    peer_node = USER_MANAGER.search_for_user(peer_uuid)
    if me_node is None or peer_node is None:
        return False, None
    me_chats = getattr(me_node.value, "chat_ids", set())
    peer_chats = getattr(peer_node.value, "chat_ids", set())
    for cid in (me_chats & peer_chats):
        node = CHAT_MANAGER.search_for_chat(cid)
        if node is None:
            continue
        chat = node.value
        participants = getattr(chat, "participants", set())
        chat_type = getattr(chat, "chat_type", None)
        if participants == {me_uuid, peer_uuid} and (chat_type == "direct" or chat_type is None):
            DIRECT_CHAT_INDEX_MANAGER.put(me_uuid, peer_uuid, cid)
            return True, cid
    return False, None
