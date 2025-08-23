from backend.models.databases.avl_tree.avl_tree import AVLTree
from backend.models.user import User


class UserDatabase(AVLTree):

    def __init__(self, file_path: str) -> None:
        super().__init__(file_path)

    def add_user(self, username: str, password: str) -> None:
        if self.search(username) is not None:
            return
        self.insert(username, password)

    def search_for_user(self, username: str) -> User | None:
        return self.search(username)

    def update_username_key(self, old_username: str, new_username: str) -> None:
        self.change_key(old_username, new_username)

    def save(self) -> None:
        self.save()