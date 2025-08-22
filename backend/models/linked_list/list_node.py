class ListNode:

    def __init__(self, value=None):
        self.prev = None
        self.value = value
        self.next = None

    def __repr__(self):
        return f"ListNode({self.value})"

    def __str__(self):
        return str(self.value)