from backend.models.databases.avl_tree.avl_tree import AVLTree


class UserDatabase:

    def __init__(self, file_path):
        self.users = AVLTree(file_path)

    def add_user(self, username, password):
        if self.users.search(username) is not None:
            raise ValueError("Username already exists.")
        self.users.insert(username, password)

    def search_for_user(self, username):
        return self.users.search(username)

    def update_username_key(self, old_username, new_username):
        self.users.change_key(old_username, new_username)

    def save(self):
        self.users.save()