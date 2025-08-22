def find_user(username):
    from backend.instances import USER_MANAGER
    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return False, None
    user = user_node.value
    return True, user
