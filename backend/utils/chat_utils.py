from typing import Optional, Callable, Tuple, Literal
import threading

from backend.instances import CHAT_MANAGER, USER_MANAGER, DIRECT_CHAT_INDEX_MANAGER
from backend.utils.user_utils import find_user

Category = Literal["main", "requests", "deny"]


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
    def normalize_pref(x) -> str:
        raw = getattr(x, "value", x)
        return str(raw or "ANYONE").strip().upper()

    def get_chat_category_for_participant(
        is_user_public: bool,
        is_friends_with_owner: bool,
        participant_message_preference_: object,
        is_blocked: bool = False
    ) -> Category:
        if is_blocked:
            return "deny"
        pref = normalize_pref(participant_message_preference_)
        if is_friends_with_owner:
            return "main"
        if pref == "NONE":
            return "deny"
        if is_user_public:
            return "main" if pref == "ANYONE" else "requests"
        return "requests"

    owner_ok, owner_obj = find_user(owner_id)
    if not owner_ok or owner_obj is None:
        raise ValueError("Owner not found")

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

    def ensure_inbox(user):
        inbox = getattr(user, "chat_ids", None)
        if not isinstance(inbox, dict):
            user.chat_ids = {"main": set(), "requests": set()}
        else:
            if "main" not in user.chat_ids:
                user.chat_ids["main"] = set()
            if "requests" not in user.chat_ids:
                user.chat_ids["requests"] = set()

    ensure_inbox(owner_obj)
    owner_obj.chat_ids["main"].add(new_chat_id)

    for uid in tuple(new_chat_obj.participants):
        if uid == owner_id:
            continue
        ok, participant = find_user(uid)
        if not ok or participant is None:
            new_chat_obj.participants.discard(uid)
            continue

        ensure_inbox(participant)

        owner_following = set(getattr(owner_obj, "following", []))
        participant_following = set(getattr(participant, "following", []))
        owner_blocked = set(getattr(owner_obj, "blocked_users", []))
        participant_blocked = set(getattr(participant, "blocked_users", []))

        is_friends = (uid in owner_following) and (owner_id in participant_following)
        is_blocked = (owner_id in participant_blocked) or (uid in owner_blocked)

        category = get_chat_category_for_participant(
            is_user_public=participant.public_status,
            is_friends_with_owner=is_friends,
            participant_message_preference_=participant.message_preferences,
            is_blocked=is_blocked
        )

        if category == "deny":
            new_chat_obj.participants.discard(uid)
            continue

        if normalize_pref(participant.message_preferences) == "FRIENDS" and not is_friends:
            if not hasattr(new_chat_obj, "invited_users"):
                new_chat_obj.invited_users = set()
            new_chat_obj.invited_users.add(uid)
            new_chat_obj.participants.discard(uid)
            continue

        participant.chat_ids[category].add(new_chat_id)

    if chat_type == "direct":
        a_uuid, b_uuid = sorted(participants)
        DIRECT_CHAT_INDEX_MANAGER.put(a_uuid, b_uuid, new_chat_id)

    return new_chat_id, new_chat_obj


def _flatten_chat_ids(user_obj) -> set[str]:
    ids = getattr(user_obj, "chat_ids", set())
    if isinstance(ids, dict):
        out = set()
        for s in ids.values():
            out |= set(s)
        return out
    return set(ids)


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
    a_chats = _flatten_chat_ids(load_user(a_uuid))
    b_chats = _flatten_chat_ids(load_user(b_uuid))
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
    create_chat_fn
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
        if b_uuid in set(getattr(a, "blocked_users", [])) or a_uuid in set(getattr(b, "blocked_users", [])):
            raise PermissionError("Cannot start a direct chat due to blocking.")
        perms = {
            a_uuid: {"can_edit": True},
            b_uuid: {"can_edit": False},
        }
        new_chat_id, _ = create_chat_fn(
            chat_name="",
            chat_cover="",
            owner_id=a_uuid,
            participant_ids={a_uuid, b_uuid},
            participant_permissions=perms,
            chat_type="direct",
        )
        direct_index.put(a_uuid, b_uuid, new_chat_id)
        return new_chat_id


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

    me_chats = _flatten_chat_ids(me_node.value)
    peer_chats = _flatten_chat_ids(peer_node.value)

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
