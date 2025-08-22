import os
import pickle

from backend.models.databases.avl_tree.avl_node import AVLNode


class AVLTree:

    def __init__(self, file_name):
        self.root = None
        self.file_name = file_name
        if os.path.exists(file_name):
            self._load_from_file()
        else:
            self.save()

    def insert(self, key, value):
        self.root = self._insert(self.root, key, value)

    def delete(self, key):
        self.root = self._delete(self.root, key)

    def search(self, key):
        return self._search(self.root, key)

    def change_key(self, old_key, new_key):
        if old_key == new_key:
            return None

        node = self._search(self.root, old_key)
        if node is None:
            return None

        # prevent duplicates (tree rejects duplicates on insert)
        if self._search(self.root, new_key) is not None:
            raise ValueError("new_key already exists")

        value = node.value
        self.root = self._delete(self.root, old_key)
        self.root = self._insert(self.root, new_key, value)
        return None

    def _insert(self, node, key, value):
        if node is None:
            return AVLNode(key, value)

        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            return node  # Duplicate keys not allowed

        return self._rebalance(node)

    def _delete(self, node, key):
        if node is None:
            return None

        if key < node.key:
            node.left = self._delete(node.left, key)
        elif key > node.key:
            node.right = self._delete(node.right, key)
        else:
            if node.left is None and node.right is None:
                return None

            if node.left is None:
                return node.right
            if node.right is None:
                return node.left

            in_order_successor = self._min_value_node(node.right)
            node.key = in_order_successor.key
            node.value = in_order_successor.value
            node.right = self._delete(node.right, in_order_successor.key)

        return self._rebalance(node)

    def _search(self, node, key):
        if node is None or node.key == key: return node
        if key < node.key: return self._search(node.left, key)
        return self._search(node.right, key)

    def _rotate_left(self, node):
        temp_right_node = node.right
        node.right = temp_right_node.left
        temp_right_node.left = node
        node.height = 1 + max(self._get_height(node.left), self._get_height(node.right))
        temp_right_node.height = 1 + max(self._get_height(temp_right_node.left), self._get_height(temp_right_node.right))
        return temp_right_node

    def _rotate_right(self, node):
        temp_left_node = node.left
        node.left = temp_left_node.right
        temp_left_node.right = node
        node.height = 1 + max(self._get_height(node.left), self._get_height(node.right))
        temp_left_node.height = 1 + max(self._get_height(temp_left_node.left), self._get_height(temp_left_node.right))
        return temp_left_node

    @staticmethod
    def _get_height(node):
        if node is None: return 0
        return node.height

    def _get_balance(self, node):
        if node is None: return 0
        balance = self._get_height(node.left) - self._get_height(node.right)
        return balance

    def _rebalance(self, node):
        node.height = 1 + max(self._get_height(node.left), self._get_height(node.right))
        balance = self._get_balance(node)

        # Left Left Case
        if balance > 1 and self._get_balance(node.left) >= 0:
            return self._rotate_right(node)

        # Left Right Case
        if balance > 1 and self._get_balance(node.left) < 0:
            node.left = self._rotate_left(node.left)
            return self._rotate_right(node)

        # Right Right Case
        if balance < -1 and self._get_balance(node.right) <= 0:
            return self._rotate_left(node)

        # Right Left Case
        if balance < -1 and self._get_balance(node.right) > 0:
            node.right = self._rotate_right(node.right)
            return self._rotate_left(node)

        return node

    def _min_value_node(self, node):
        if node.left is None: return node
        return self._min_value_node(node.left)

    def _load_from_file(self):
        with open(self.file_name, "rb") as file:
            loaded_tree = pickle.load(file)
            self.root = loaded_tree.root

    def save(self):
        with open(self.file_name, "wb") as file:
            pickle.dump(self, file)
