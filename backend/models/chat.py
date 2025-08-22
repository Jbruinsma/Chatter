import uuid
from datetime import datetime
from typing import Dict, List

from backend.models.linked_list.linked_list import LinkedList
from backend.models.user import User


class Chat:

    def __init__(self, chat_id : str, chat_owner : User, participants : List[str], participant_permissions : Dict[str, Dict[str, str | bool]] , chat_name : str =None):

        owner_username : str = chat_owner.username

        chat_participants : List[Dict[str, str | bool]] = [{"username": owner_username, 'can_edit': True, 'can_delete': True}]

        for participant_username in participant_permissions:
            chat_participants.append(participant_permissions[participant_username])

        self.chat_id : str = chat_id
        self.participants : Dict[str, Dict[str, str | bool]]= {participant['username']: participant for participant in chat_participants}
        self.messages : LinkedList = LinkedList()
        self.time_created : datetime = datetime.now()
        self.unread_messages_by : set = set(participant['username']   for participant in chat_participants)
        self.owner : str = owner_username

        if chat_name is None:
            self.chat_name = f"Chat with {', '.join([participant['username'] for participant in chat_participants])}"
        else:
            self.chat_name = chat_name

    def __str__(self) -> str:
        return f"Chat: {self.chat_id}, {self.chat_name}, {self.participants}, {self.time_created}, {self.unread_messages_by}"

    def update_chat(self, added_participants : List[str], removed_participants : List[str], updated_permissions : Dict[str, Dict[str, bool]], chat_name= None) -> None:
        pass

    def add_message(self, message_data : Dict[str, str | datetime]) -> None:
        self.messages.append(message_data)
        self.mark_as_unread_for_all()

    def send_user_leave_message(self, username) -> Dict[str, str | datetime]:
        message_info : Dict[str, str | datetime] = self.add_system_message(f"{username} has left the chat.")
        return message_info

    def send_user_join_message(self, added_user_username: str, added_by_username : str =None) -> Dict[str, str | datetime]:
        if added_by_username: system_message : str = f"{added_user_username} has been added to the chat by {added_by_username}."
        else: system_message : str = f"{added_user_username} has joined the chat."
        message_info : Dict[str, str | datetime] = self.add_system_message(system_message)
        return message_info

    def send_user_edit_message(self, editor_username) -> Dict[str, str | datetime]:
        message_info : Dict[str, str | datetime] = self.add_system_message(f"{editor_username} has edited the chat.")
        return message_info

    def send_user_kick_message(self, kicked_user : str, kicked_by : str) -> Dict[str, str | datetime]:
        message_info : Dict[str, str | datetime] = self.add_system_message(f"{kicked_user} has been kicked by {kicked_by}")
        return message_info

    def update_permissions(self, username : str, permissions : Dict[str, bool]) -> None:
        if username in self.participants:
            can_edit : bool = permissions.get('can_edit', False)
            can_delete : bool = permissions.get('can_delete', False)
            self.participants[username] = {"username": username, "can_edit": can_edit, "can_delete": can_delete}

    def promote_to_owner(self, new_owner_username : str) -> None:
        self.participants[new_owner_username] = {"username": new_owner_username, "can_edit": True, "can_delete": True}
        self.owner = new_owner_username

    def mark_as_unread_for_all(self) -> None:
        for participant in self.participants.keys():
            self.unread_messages_by.add(participant)

    def mark_as_read_by(self, username : str) -> None:
        if username in self.unread_messages_by:
            self.unread_messages_by.remove(username)

    def get_last_message(self) -> str | None:
        if self.messages.is_empty():
            return None
        return self.messages.tail.value.get('message')

    def get_last_message_time(self) -> datetime | None:
        if self.messages.is_empty():
            return None
        return self.messages.tail.value.get('time_sent')

    def get_participant_permissions(self, username : str) -> Dict[str, bool] | None:
        participant : Dict[str, bool] = self.participants.get(username)
        if participant:
            return {
                "can_edit": participant.get('can_edit', False),
                "can_delete": participant.get('can_delete', False)
            }
        return None

    def add_participant(self, new_participant : User, participant_edit_permissions : bool =False) -> None:
        new_participant_username : str = new_participant.username
        self.participants[new_participant_username] = {
            "username": new_participant_username,
            "can_edit": participant_edit_permissions,
            "can_delete": False
        }

    def remove_participant(self, participant : User) -> None:
        participant_username : str = participant.username
        if participant_username in self.participants:
            del self.participants[participant_username]
            if participant_username in self.unread_messages_by:
                self.unread_messages_by.remove(participant_username)
        participant.remove_chat_id(self.chat_id)

    def get_chat_overview(self) -> Dict[str, str | List[str] | datetime | List[str]]:
        return {
            "chat_id": self.chat_id,
            "chat_name": self.chat_name,
            "participants": list(self.participants.keys()),
            "time_created": self.time_created.isoformat(),
            "unread_messages_by": list(self.unread_messages_by),
            "last_message": self.get_last_message(),
            "last_message_time": self.get_last_message_time(),
            "participant_permissions": self.participants
        }

    def add_system_message(self, message : str) -> Dict[str, str | datetime]:
        system_message : Dict[str, str | datetime] = {
            "message_id": f"{str(uuid.uuid4())}",
            "sender": "System",
            "message": message,
            "time_sent": datetime.now().isoformat()
        }
        self.messages.append(system_message)
        self.mark_as_unread_for_all()
        return system_message

    def to_dict(self) -> Dict[str, str | List[str] | datetime | List[str]]:
        return {
            "chat_id": self.chat_id,
            "chat_name": self.chat_name,
            "participants": list(self.participants.keys()),
            "time_created": self.time_created.isoformat(),
            "unread_messages_by": list(self.unread_messages_by),
            "messages": [msg for msg in self.messages.get_all_chats()],
            "last_message": self.get_last_message(),
            "last_message_time": self.get_last_message_time(),
            "participant_permissions": self.participants
        }

    def remove_last_message(self) -> None:
        self.messages.remove_last()