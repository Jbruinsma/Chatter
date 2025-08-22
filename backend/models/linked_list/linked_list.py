from backend.models.linked_list.list_node import ListNode


class LinkedList:

    def __init__(self):
        self.head = None
        self.tail = None

    def append(self, value):
        new_node = ListNode(value)
        if self.is_empty():
            self.head = new_node
            self.tail = new_node
        else:
            new_node.prev = self.tail
            self.tail.next = new_node
            self.tail = new_node

    def get_all_chats(self):
        chats = []
        current = self.head
        while current:
            chats.append(current.value)
            current = current.next
        return chats

    def remove_last(self):
        if self.is_empty():
            return None
        else:
            removed_node = self.tail
            if self.head == self.tail:
                self.head = None
                self.tail = None
            else:
                self.tail = self.tail.prev
                self.tail.next = None
            return removed_node.value

    def is_empty(self):
        return self.head is None
