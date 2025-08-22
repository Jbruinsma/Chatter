class AVLNode:

    def __init__(self, key, value, left=None, right=None):
        self.key = key
        self.value = value
        self.left = left
        self.right = right
        self.height = 1

    def __str__(self):
        return f"AVL Node: Key: {self.key}, Value: {self.value}, Height: {self.height}, Left: {self.left if self.left else None}, Right: {self.right if self.right else None}"