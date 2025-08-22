from backend.models.databases.avl_tree.avl_tree import AVLTree


class UserDatabase(AVLTree):

    def __init__(self, file_path):
        super().__init__(file_path)

    def add_user(self, username, password):
        if self.search(username) is not None:
            raise ValueError("Username already exists.")
        self.insert(username, password)

    def search_for_user(self, username):
        return self.search(username)

    def update_username_key(self, old_username, new_username):
        self.change_key(old_username, new_username)

    def save(self):
        self.save()