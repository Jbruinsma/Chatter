import uuid
from typing import Dict

from fastapi import APIRouter, Request
from backend.instances import USER_MANAGER
from backend.models.user import User
from backend.utils.user_utils import find_user

router = APIRouter()

@router.post("/login")
async def login(request: Request):
    data = await request.json()
    username = data["username"]
    password = data["password"]

    error_response = {"error": "Username or password is Invalid."}

    if not username or not password:
        return {"error": "Username and password are required."}

    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None: return error_response

    user = user_node.value
    if user.check_password(password):
        user.set_user_active()
        return {"message": "Login successful."}

    return error_response

@router.post("/register")
async def register(request : Request):
    data : Dict[str, str | bool] = await request.json()
    username : str = data.get("username")
    password : str = data.get("password")
    is_public : bool = data.get("is_public")

    if not username or not password:
        return {"error": "Username and password are required."}

    if USER_MANAGER.search_for_user(username) is not None:
        return {"error": "Username already exists."}

    user_id = str(uuid.uuid4())
    new_user = User(user_uuid= user_id, username= username, password= password, is_public= is_public)
    USER_MANAGER.add_user(new_user.username, new_user)
    USER_MANAGER.save()
    return {"message": "User created successfully."}

@router.get("/{username}/logout")
def logout(username: str):
    print(f"{username} IS LOGGING OUT")
    return {"message": "Logout successful."}

@router.get("/user/{username}")
async def get_user(username: str):
    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return {"error": "User not found."}

    user = user_node.value
    return user.to_dict()

# Unfollow
@router.post("/user/{username}/unfollow")
async def unfollow_user(username: str, request: Request):
    data = await request.json()
    target_username = data.get('target_username')
    user_who_sent_unfollow = data.get('unfollower_username')

    if user_who_sent_unfollow != username:
        return {"error": "Internal Error: unfollower username does not match authenticated user."}

    if target_username == username:
        return {"error": "Internal Error: target username cannot be the same as the unfollower username."}

    if not target_username or not user_who_sent_unfollow:
        return {"error": "Internal Error: target username and unfollower username are required."}

    user_status, target_user_obj = find_user(target_username)
    if not user_status or target_user_obj is None:
        return {"error": "Target user not found."}

    user_status, unfollower_user_obj = find_user(user_who_sent_unfollow)
    if not user_status or unfollower_user_obj is None:
        return {"error": "Unfollower user not found."}

    if user_who_sent_unfollow not in target_user_obj.followers or target_username not in unfollower_user_obj.following:
        return {"error": "You are not following this user."}

    target_user_obj.followers.remove(user_who_sent_unfollow)
    unfollower_user_obj.following.remove(target_username)
    USER_MANAGER.save()
    return {"message": f"You have unfollowed {target_username}."}

@router.post("/user/{username}/cancel_follow_request")
async def cancel_follow_request(username: str, request: Request):
    data = await request.json()
    target_username = data.get("target_username")
    user_who_sent_request = data.get("request_sender_username")

    if user_who_sent_request != username:
        return {"error": "Internal Error: request sender username does not match authenticated user."}

    if target_username == username:
        return {"error": "Internal Error: target username cannot be the same as the request sender username."}

    if not target_username or not user_who_sent_request:
        return {"error": "Internal Error: target username and request sender username are required."}

    user_status, target_user_obj = find_user(target_username)
    if not user_status or target_user_obj is None:
        return {"error": "Target user not found."}

    if user_who_sent_request not in target_user_obj.follow_requests:
        return {"error": "No follow request from this user."}

    target_user_obj.follow_requests.remove(user_who_sent_request)
    USER_MANAGER.save()
    return {"message": f"Follow request from {user_who_sent_request} cancelled."}


# Follow
@router.post("/user/{username}/follow")
async def follow_user(username: str, request: Request):

    print(f"Username: {username}")

    data = await request.json()
    target_username = data.get("target_username")
    follower_username = data.get("follower_username")

    print(f"Target Username: {target_username}")
    print(f"Follower Username: {follower_username}")

    if follower_username != username:
        return {"error": "Internal Error: follower username does not match authenticated user."}

    if target_username == username:
        return {"error": "Internal Error: target username cannot be the same as the follower username."}

    user_status, target_user_obj = find_user(target_username)
    if not user_status or target_user_obj is None:
        return {"error": "Target user not found."}

    user_status, follower_user_obj = find_user(follower_username)
    if not user_status or follower_user_obj is None:
        return {"error": "Follower user not found."}

    target_user_obj.add_follower(follower_user_obj)
    USER_MANAGER.save()
    return {"message": f"{follower_username} is now following {target_username}."}

@router.post("/user/{username}/requests/accept")
async def accept_follow_request(request: Request, username: str):
    data = await request.json()

    target_username = data.get("target_username")
    follower_username = data.get("follower_username")

    print(f"Target Username: {target_username}")
    print(f"Follower Username: {follower_username}")

    if not target_username or not follower_username:
        return {"error": "Internal error: Target username and follower username are required."}

    if target_username != username:
        return {"error": "Internal error: Target username does not match authenticated user."}

    if target_username == follower_username:
        return {"error": "Internal error: Target username cannot be the same as the follower username."}

    user_status, target_user_obj = find_user(target_username)
    if not user_status or target_user_obj is None:
        return {"error": "Target user not found."}

    user_status, follower_user_obj = find_user(follower_username)
    if not user_status or follower_user_obj is None:
        return {"error": "Follower user not found."}

    if follower_username not in target_user_obj.follow_requests:
        return {"error": "No follow request from this user."}

    target_user_obj.follow_requests.remove(follower_username)
    target_user_obj.followers.add(follower_username)
    follower_user_obj.following.add(target_username)

    USER_MANAGER.save()
    return {"message": f"{follower_username} accepted your follow request."}

@router.post("/user/{username}/requests/deny")
async def reject_follow_request(request: Request, username: str):
    data = await request.json()

    target_username = data.get("target_username")
    follower_username = data.get("follower_username")

    print(f"Target Username: {target_username}")
    print(f"Follower Username: {follower_username}")

    if not target_username or not follower_username:
        return {"error": "Internal error: Target username and follower username are required."}

    if target_username != username:
        return {"error": "Internal error: Target username does not match authenticated user."}

    if target_username == follower_username:
        return {"error": "Internal error: Target username cannot be the same as the follower username."}

    user_status, target_user_obj = find_user(target_username)
    if not user_status or target_user_obj is None:
        return {"error": "Target user not found."}

    target_user_obj.follow_requests.remove(follower_username)

    USER_MANAGER.save()
    return {"message": f"Follow request from {follower_username} denied."}

@router.post("/user/block")
async def block_user(request: Request):
    data = await request.json()
    username = data.get("username")
    blocked_username = data.get("blocked_username")

    if not username or not blocked_username:
        return {"error": "Username and blocked username are required."}

    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return {"error": "User not found."}
    user = user_node.value

    if blocked_username in user.blocked_users:
        return {"error": f"{blocked_username} is already blocked."}
    blocked_user_node = USER_MANAGER.search_for_user(blocked_username)
    if blocked_user_node is None:
        return {"error": "Blocked user not found."}
    blocked_user = blocked_user_node.value

    user.block_user(blocked_user)
    USER_MANAGER.save()
    return {"message": f"{blocked_username} has been blocked."}

@router.get("/user/{username}/followers")
async def get_followers(username: str):
    user_status, user_obj = find_user(username)
    if not user_status or user_obj is None:
        return {"error": "User not found."}
    return user_obj.followers_to_list()

@router.get("/user/{username}/following")
async def get_following(username: str):
    user_status, user_obj = find_user(username)
    if not user_status or user_obj is None:
        return {"error": "User not found."}
    return user_obj.following_to_list()

@router.get("/user/{username}/update_pfp")
async def update_pfp(username: str, request: Request):
    pass

@router.post("/user/{username}/update_username")
async def update_username(username: str, request: Request):
    data = await request.json()

    old_username = data.get('old_username', None)
    new_username = data.get('new_username', None)

    if not old_username or not new_username:
        return {"error": "Both old and new usernames are required."}

    if username != old_username:
        return {"error": "Username does not match the authenticated user."}

    user_status, user_obj = find_user(old_username)

    if not user_status or user_obj is None:
        return {"error": "User not found."}

    user_obj.username = new_username

    USER_MANAGER.update_username_key(old_username, new_username)
    USER_MANAGER.save()

    print(f"{old_username} has changed their username to {new_username} successfully.")
    return {"message": "Username updated successfully."}


@router.post("/user/{username}/update_public_status")
async def update_public_status(username: str, request: Request):
    data = await request.json()
    is_public = data.get("is_public")
    if is_public is None or not isinstance(is_public, bool):
        return {"error": "Internal Error: is_public is required or is invalid."}

    user_status, user_obj = find_user(username)
    if not user_status or user_obj is None:
        return {"error": "User not found."}
    user_obj.public_status = is_public

    if len(user_obj.follow_requests) > 0:
        for follow_request_username in user_obj.follow_requests:
            user_status, follow_request_user_obj = find_user(follow_request_username)
            if not user_status or follow_request_user_obj is None: continue
            user_obj.follow_requests.remove(follow_request_username)
            follow_request_user_obj.following.add(username)

    USER_MANAGER.save()

    public_status = "Public" if is_public else "Private"
    return {"message": f"Public status successfully updated to: {public_status}"}