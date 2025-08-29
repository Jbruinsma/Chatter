def find_user(username):
    from backend.instances import USER_MANAGER
    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return False, None
    user = user_node.value
    return True, user

def user_uuid_to_username(user_uuid):
    user_status, user_obj = find_user(user_uuid)
    if not user_status:
        return None
    return user_obj.username