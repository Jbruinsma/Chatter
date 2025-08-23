import uuid
from datetime import datetime, timezone
from typing import List, Dict, Set

from backend.models.linked_list.linked_list import LinkedList
from backend.utils.user_utils import find_user


class ChatNew:

    def __init__(self, chat_name: str, chat_cover: str, owner_id: str, participant_ids: List[str], participant_permissions: Dict[str, Dict[str, bool | str]]):

        participant_ids = list(set(participant_ids))
        participant_permissions = copy.deepcopy(participant_permissions)
        participant_permissions[owner_id]["can_edit"] = True

        if owner_id not in participant_ids:
            raise ValueError("Owner must be a participant.")

        if len(participant_ids) < 2:
            raise ValueError("Chat must have at least 2 participants.")

        if set(participant_permissions.keys()) != set(participant_ids):
            raise ValueError("Participant permissions must include all participants.")

        self.chat_id: str = str(uuid.uuid4())
        self.chat_name: str = chat_name
        self.chat_cover: str = chat_cover
        self.owner_id: str = owner_id
        self.participants: Set[str] = set(participant_ids)
        self.participant_permissions: Dict[str, Dict[str, bool | str]] = participant_permissions
        self.created_at = datetime.now(timezone.utc)
        self.messages: LinkedList = LinkedList()
        self.unread_messages_by: Set[str] = set()

    def get_participant_role(self, user_uuid: str) -> str:
        if user_uuid == self.owner_id:
            return "Owner"
        try:
            can_edit = self.participant_permissions[user_uuid]["can_edit"]
            if can_edit:
                return "Editor"
        except KeyError:
            pass
        return "Participant"

    def format_participant_dict(self,user_uuid):
        user_status, user_obj = find_user(user_uuid)
        if user_status and user_obj is not None:
            user_id = user_obj.user_id
            username = user_obj.username
            avatar = user_obj.avatar
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
            "role": role
        }

    def to_dict(self, viewer_uuid: str = None):

        if len(self.participants) == 0 or self.owner_id not in self.participants:
            return {}

        participants = {}
        participants_list = list(self.participants)
        for user_uuid in participants_list:
            participant_info = self.format_participant_dict(user_uuid)
            participants[user_uuid] = participant_info

        capabilities = {}
        if viewer_uuid is not None:
            try:
                is_owner = viewer_uuid == self.owner_id
                can_edit = is_owner or self.participant_permissions[viewer_uuid]["can_edit"]
                capabilities["canEdit"] = can_edit
                capabilities["role"] = "Owner" if is_owner else "Editor" if can_edit else "Participant"
            except KeyError:
                capabilities["canEdit"] = False
                capabilities["role"] = "Participant"

        return {
            "chatId": self.chat_id,
            "chatCover": self.chat_cover,
            "chatName": self.chat_name,
            "ownerId": self.owner_id,
            "participantsById": participants,
            "participantIds": list(self.participants),
            "capabilities": capabilities,
            "createdAt": self.created_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "hasUnreadMessages": True if viewer_uuid is not None and viewer_uuid in self.unread_messages_by else False,
            "lastMessage": self.messages.tail.value.get("message") if not self.messages.is_empty() else "",
        }