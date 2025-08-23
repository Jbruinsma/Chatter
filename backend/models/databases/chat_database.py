import uuid
from typing import List, Dict

from backend.models.chat import Chat
from backend.models.databases.avl_tree.avl_tree import AVLTree
from backend.models.user import User


class ChatDatabase(AVLTree):

    def __init__(self, file_path: str) -> None:
        super().__init__(file_path)

    def search_for_chat(self, chat_id: str) -> Chat | None:
        return self.search(chat_id)

    def add_chat(self, owner: User, participants: List[str], chat_name: str, participant_permissions: Dict[str, Dict[str | bool]]) -> tuple[str, Chat]:
        chat_id = str(uuid.uuid4())
        if self.search(chat_id) is not None:
            return self.add_chat(owner, participants, chat_name, participant_permissions)
        new_chat = Chat(chat_id= chat_id, chat_owner= owner, participants= participants, participant_permissions= participant_permissions, chat_name= chat_name)
        self.insert(chat_id, new_chat)
        return chat_id, new_chat

    def delete_chat(self, chat_id):
        self.delete(chat_id)

    def save_chat_database(self):
        self.save()