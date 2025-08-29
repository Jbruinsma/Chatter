import uuid
from typing import List, Dict, Literal

from backend.models.chat import Chat
from backend.models.databases.avl_tree.avl_tree import AVLTree
from backend.models.user import User


class ChatDatabase(AVLTree):

    def __init__(self, file_path: str) -> None:
        super().__init__(file_path)

    def search_for_chat(self, chat_id: str) -> Chat | None:
        return self.search(chat_id)

    def add_chat(
            self,
            chat_name: str,
            chat_cover: str,
            owner_id: str,
            participant_ids: List[str],
            participant_permissions: Dict[str, Dict[str, bool | str]],
            chat_type: Literal["direct", "group"] = "group"
    ):
        chat_id = str(uuid.uuid4())
        if self.search(chat_id) is not None:
            return self.add_chat(chat_name= chat_name, chat_cover=chat_cover, owner_id=owner_id, participant_ids=participant_ids, participant_permissions=participant_permissions, chat_type=chat_type)
        new_chat = Chat(
            chat_name= chat_name,
            chat_cover= chat_cover,
            owner_id= owner_id,
            participant_ids= participant_ids,
            participant_permissions= participant_permissions,
            chat_type= chat_type
        )
        self.insert(chat_id, new_chat)
        return chat_id, new_chat

    def delete_chat(self, chat_id):
        self.delete(chat_id)

    def save_chat_database(self):
        super().save()