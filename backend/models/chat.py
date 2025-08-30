import copy
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Set, Optional, Literal

from backend.models.linked_list.linked_list import LinkedList
from backend.utils.user_utils import find_user

from backend.utils.formatting import format_message_dict


class Chat:
    """
    Chat model supporting explicit chat types:
      - "direct": exactly 2 participants (1-to-1). UI can treat this as a DM.
      - "group": 2+ participants.

    Notes:
    - We keep an explicit `chat_type` instead of inferring from participant count.
    - For direct chats, invariants are enforced (exactly 2 participants).
    - `to_dict(viewer_uuid=...)` now includes:
        * "type": "direct" | "group"
        * "isDirect": bool
        * "otherParticipant" (when direct + viewer provided)
        * "title" and "avatar" convenient defaults for DMs
    """

    def __init__(
        self,
        chat_name: str,
        chat_cover: str,
        owner_id: str,
        participant_ids: List[str],
        participant_permissions: Dict[str, Dict[str, bool | str]],
        chat_type: Literal["direct", "group"] = "group",
    ):
        participant_ids = list(set(participant_ids))
        participant_permissions = copy.deepcopy(participant_permissions)

        if owner_id not in participant_ids:
            raise ValueError("Owner must be a participant.")
        participant_permissions.setdefault(owner_id, {})
        participant_permissions[owner_id]["can_edit"] = True

        if len(participant_ids) < 2:
            raise ValueError("Chat must have at least 2 participants.")

        if set(participant_permissions.keys()) != set(participant_ids):
            raise ValueError("Participant permissions must include all participants.")

        self.chat_id: str = str(uuid.uuid4())
        self.chat_name: str = chat_name
        self.chat_cover: str = chat_cover
        self.owner_id: str = owner_id
        self.participants: Set[str] = set(participant_ids)
        self.invited_users: Set[str] = set()
        self.participant_permissions: Dict[str, Dict[str, bool | str]] = participant_permissions
        self.created_at = datetime.now(timezone.utc)
        self.messages: LinkedList = LinkedList()
        self.unread_messages_by: Set[str] = set()

        self.chat_type: Literal["direct", "group"] = chat_type
        if self.chat_type == "direct":
            if len(self.participants) != 2:
                raise ValueError("Direct chats must have exactly 2 participants.")
            for uid in self.participants:
                self.participant_permissions[uid]["can_edit"] = True

    @property
    def is_direct(self) -> bool:
        return self.chat_type == "direct"

    def get_participant_role(self, user_uuid: str) -> str:
        if user_uuid == self.owner_id:
            return "Owner"
        elif user_uuid in self.invited_users:
            return "Invited"
        try:
            if self.participant_permissions[user_uuid].get("can_edit", False):
                return "Editor"
        except KeyError:
            pass
        return "Participant"

    def _other_participant_uuid(self, viewer_uuid: Optional[str]) -> Optional[str]:
        if not viewer_uuid or not self.is_direct:
            return None
        for uid in self.participants:
            if uid != viewer_uuid:
                return uid
        return None

    def add_message(self, new_message_info: Dict[str, str]):
        self.messages.append(new_message_info)
        self.mark_unread_for_all()

    def add_system_message(self, system_message: str):
        message_dict = format_message_dict(
            chat_id= self.chat_id,
            chat_type="system",
            message_id= str(uuid.uuid4()),
            sender_id= "system",
            message= system_message,
            time_sent= datetime.now(timezone.utc)
        )
        self.add_message(message_dict)

    def format_participant_dict(self, user_uuid: str) -> Dict[str, str]:
        user_status, user_obj = find_user(user_uuid)
        if user_status and user_obj is not None:
            user_id = user_obj.id
            username = user_obj.username
            avatar = user_obj.profile_picture
            role = self.get_participant_role(user_uuid)
        else:
            user_id = user_uuid
            username = "Deleted User"
            avatar = ""
            role = "Participant"
        return {
            "id": user_id,
            "username": username,
            "avatar": avatar,
            "role": role,
        }

    def last_message_to_dict(self) -> Dict[str, object]:
        return self.messages.tail.value

    def to_dict(self, viewer_uuid: Optional[str] = None) -> Dict[str, object]:
        if len(self.participants) == 0 or self.owner_id not in self.participants:
            return {}

        participants_by_id: Dict[str, Dict[str, str]] = {}
        for user_uuid in list(self.participants):
            participants_by_id[user_uuid] = self.format_participant_dict(user_uuid)

        capabilities: Dict[str, object] = {}
        if viewer_uuid is not None:
            try:
                is_owner = viewer_uuid == self.owner_id
                can_edit = is_owner or bool(self.participant_permissions[viewer_uuid].get("can_edit", False))
                capabilities["canEdit"] = can_edit
                capabilities["role"] = "Owner" if is_owner else ("Editor" if can_edit else "Participant")
            except KeyError:
                capabilities["canEdit"] = False
                capabilities["role"] = "Participant"

        data: Dict[str, object] = {
            "chatId": self.chat_id,
            "chatCover": self.chat_cover,
            "chatName": self.chat_name,
            "ownerId": self.owner_id,
            "participantsById": participants_by_id,
            "participantIds": list(self.participants),
            "participantCount": len(self.participants),
            "capabilities": capabilities,
            "createdAt": self.created_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "hasUnreadMessages": bool(viewer_uuid is not None and viewer_uuid in self.unread_messages_by),
            "lastMessage": self.messages.tail.value.get("message") if not self.messages.is_empty() else "",
            "type": self.chat_type,
            "isDirect": self.is_direct,
            "invitedUsers": list(self.invited_users),
        }

        if self.is_direct and viewer_uuid:
            other_uuid = self._other_participant_uuid(viewer_uuid)
            if other_uuid:
                other_info = participants_by_id.get(other_uuid) or self.format_participant_dict(other_uuid)
                data["otherParticipant"] = other_info 
                data["title"] = other_info.get("username", "")
                data["avatar"] = other_info.get("avatar", "")

        return data

    def mark_unread_for_all(self) -> None:
        self.unread_messages_by = set(self.participants)

    def mark_unread_for(self, user_uuid: str) -> None:
        if user_uuid in self.participants:
            self.unread_messages_by.add(user_uuid)

    def mark_read_for(self, user_uuid: str) -> None:
        self.unread_messages_by.discard(user_uuid)

    def can_user_edit(self, user_uuid: str) -> bool:
        if user_uuid == self.owner_id:
            return True
        return bool(self.participant_permissions.get(user_uuid, {}).get("can_edit", False))

    def rename(self, user_uuid: str, new_name: str) -> None:
        """Allow owners/editors to rename (for direct chats, many UIs ignore custom names)."""
        if not self.can_user_edit(user_uuid):
            raise PermissionError("User lacks permission to rename this chat.")
        self.chat_name = new_name
