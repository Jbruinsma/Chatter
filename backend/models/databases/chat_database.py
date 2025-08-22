import uuid

from backend.models.chat import Chat
from backend.models.databases.avl_tree.avl_tree import AVLTree


class ChatDatabase:

    def __init__(self, file_path):
        self.chats = AVLTree(file_path)

    def search_for_chat(self, chat_id):
        return self.chats.search(chat_id)

    def add_chat(self, owner, participants, chat_name, participant_permissions) -> tuple[str, Chat]:
        chat_id = str(uuid.uuid4())
        if self.chats.search(chat_id) is not None:
            raise ValueError("Chat ID already exists.")

        new_chat = Chat(chat_id= chat_id, chat_owner= owner, participants= participants, participant_permissions= participant_permissions, chat_name= chat_name)
        self.chats.insert(chat_id, new_chat)
        return chat_id, new_chat

    def delete_chat(self, chat_id):
        self.chats.delete(chat_id)

    def save_chat_database(self):
        self.chats.save()