import uuid
from datetime import datetime

from fastapi import APIRouter
from starlette.requests import Request
from starlette.websockets import WebSocket

from backend.instances import USER_MANAGER, CHAT_MANAGER
from backend.utils.chat_utils import find_chat
from backend.utils.user_utils import find_user

router = APIRouter()


@router.get("/user/{username}/chats") # List all chats for a user
async def get_chats(username: str):
    user_status, user_obj = find_user(username)
    if not user_status or user_obj is None:
        return {"error": "User not found."}

    user_chat_ids = user_obj.get_chat_ids()
    chat_overviews = []

    for chat_id in user_chat_ids:
        chat_status, chat_obj = find_chat(chat_id)
        if chat_status and chat_obj is not None:
            chat_overviews.append(chat_obj.get_chat_overview())

    chat_overviews.sort(
        key=lambda c: c["last_message_time"] or datetime.min.isoformat(),
        reverse=True
    )
    return {"chats": chat_overviews}

@router.get("/user/{username}/chats/{chat_id}") # Get a specific chat by ID for a user
async def get_chat(username: str, chat_id: str):
    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return {"error": "User not found."}
    user = user_node.value

    chat_node = CHAT_MANAGER.search_for_chat(chat_id)
    if chat_node is None:
        return {"error": "Chat not found."}
    chat = chat_node.value

    if chat.chat_id not in user.chat_ids:
        return {"error": "Chat does not belong to the user."}

    return chat.to_dict()

@router.post("/user/{username}/chats") # Create a new chat for a user
async def create_chat(username: str, chat_data: Request):
    data = await chat_data.json()
    chat_name = data.get("chat_name")
    chat_participant_usernames = data.get("chat_participant_usernames")
    if not chat_name or not chat_participant_usernames:
        return {"error": "Chat name and participant usernames are required."}

    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return {"error": "User not found."}
    user = user_node.value

    participants = []
    skipped_users = []

    for participant_username in chat_participant_usernames:
        if participant_username[0] == '@':
            participant_username = participant_username[1:]
        participant_node = USER_MANAGER.search_for_user(participant_username)
        if participant_node is None:
            skipped_users.append(participant_username)
            continue

        participants.append(participant_node.value)

    if len(participants) < 1:
        return {"error": "At least one participant is required."}

    try:
        new_chat_id, chat = CHAT_MANAGER.add_chat(owner= user, participants= participants, chat_name= chat_name)
        chat.add_system_message(f"Chat created by {user.username}.")

        for participant in participants:
            participant.add_chat_id(new_chat_id)
        user.add_chat_id(new_chat_id)

    except ValueError as exception:
        return {"error": str(exception)}

    CHAT_MANAGER.save_chat_database()
    USER_MANAGER.save()
    return {"message": f"Chat created successfully with ID: {new_chat_id}",
            "chat_id": new_chat_id,
            "skipped_users": skipped_users,
            "last_message": chat.get_last_message()
            }

@router.post("/user/{username}/chats/{chat_id}/send_message") # Send a message in a chat
async def send_message(username : str, chat_id : str, message_data: Request):
    data = await message_data.json()
    print(data)
    # {
    #     "id": "unique_message_id",
    #     "type": "message",
    #     "chat_id": "...",
    #     "sender": "justin",
    #     "message": "yo",
    #     "timestamp": "..."
    # }

    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return {"error": "User not found."}
    user = user_node.value

    chat_node = CHAT_MANAGER.search_for_chat(chat_id)
    if chat_node is None:
        return {"error": "Chat not found."}
    chat = chat_node.value
    chat.add_message(data)

    CHAT_MANAGER.save_chat_database()
    return {"message": "Message sent successfully."}

@router.post("/user/{username}/chats/{chat_id}/mark_as_read")
async def mark_chat_as_read(username: str, chat_id: str):
    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return {"error": "User not found."}
    user = user_node.value

    chat_node = CHAT_MANAGER.search_for_chat(chat_id)
    if chat_node is None:
        return {"error": "Chat not found."}
    chat = chat_node.value

    chat.mark_as_read_by(username)

    CHAT_MANAGER.save_chat_database()
    return {"message": "Chat marked as read."}

@router.delete("/user/{username}/chats/{chat_id}")
async def delete_chat(username: str, chat_id: str):
    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return {"error": "User not found."}
    user = user_node.value

    chat_node = CHAT_MANAGER.search_for_chat(chat_id)
    if chat_node is None:
        return {"error": "Chat not found."}
    chat = chat_node.value

    if chat.chat_id not in user.chat_ids:
        return {"error": "Chat does not belong to the user."}

    user_permissions = chat.get_participant_permissions(username)
    if not user_permissions or not user_permissions.get('can_delete', False):
        return {"error": "User does not have permission to delete this chat."}

    user.chat_ids.remove(chat.chat_id)
    for participant_info in chat.participants.values():
        participant_username = participant_info["username"]
        participant_node = USER_MANAGER.search_for_user(participant_username)
        if participant_node:
            participant_node.value.chat_ids.discard(chat.chat_id)  # discard avoids KeyError if not present

    CHAT_MANAGER.delete_chat(chat_id)
    CHAT_MANAGER.save_chat_database()
    USER_MANAGER.save()

    return {"message": "Chat deleted successfully."}

@router.post("/user/{username}/chats/{chat_id}/add_participant")
async def add_participant_to_chat(username: str, chat_id: str, request: Request):
    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return {"error": "User not found."}
    user = user_node.value

    chat_node = CHAT_MANAGER.search_for_chat(chat_id)
    if chat_node is None:
        return {"error": "Chat not found."}
    chat = chat_node.value

    user_permissions = chat.get_participant_permissions(username)
    if not user_permissions or not user_permissions.get('can_edit', False):
        return {"error": "User does not have permission to add participants to this chat."}

    data = await request.json()
    new_participant_username = data.get("new_participant_username")
    if not new_participant_username:
        return {"error": "New participant username is required."}

    new_participant_node = USER_MANAGER.search_for_user(new_participant_username)
    if new_participant_node is None:
        return {"error": "New participant not found."}
    if new_participant_username in chat.participants:
        return {"error": "User is already a participant in this chat."}

    new_participant = new_participant_node.value
    participant_edit_permissions = data.get("can_edit", False)

    chat.add_participant(new_participant, participant_edit_permissions)
    new_participant.add_chat_id(chat_id)

    CHAT_MANAGER.save_chat_database()
    USER_MANAGER.save()

    return {"message": f"Participant {new_participant_username} added to chat {chat_id}."}

@router.post("/user/{username}/chats/{chat_id}/remove_participant")
async def remove_participant(username: str, chat_id: str, request: Request):
    user_node = USER_MANAGER.search_for_user(username)
    if user_node is None:
        return {"error": "User not found."}
    user = user_node.value

    chat_node = CHAT_MANAGER.search_for_chat(chat_id)
    if chat_node is None:
        return {"error": "Chat not found."}
    chat = chat_node.value

    user_permissions = chat.get_participant_permissions(username)
    if not user_permissions or not user_permissions.get('can_edit', False):
        return {"error": "User does not have permission to remove participants from this chat."}

    data = await request.json()
    participant_username = data.get("participant_username")

    if not participant_username:
        return {"error": "Participant username is required."}
    if participant_username == chat.owner:
        return {"error": "Cannot remove the chat owner."}
    if participant_username not in chat.participants:
        return {"error": "User is not a participant in this chat."}

    participant_node = USER_MANAGER.search_for_user(participant_username)
    if participant_node:
        participant = participant_node.value
        chat.remove_participant(participant)

    CHAT_MANAGER.save_chat_database()
    USER_MANAGER.save()

    return {"message": f"Participant {participant_username} removed from chat {chat_id}."}




active_connections = {}


@router.websocket("/ws/chat/{chat_id}/{username}")
async def websocket_endpoint(websocket : WebSocket, chat_id: str, username: str):
    print(f"WebSocket connection attempt: chat_id={chat_id}, username={username}")
    # Check if the chat exists
    chat_node = CHAT_MANAGER.search_for_chat(chat_id)
    if chat_node is None:
        await websocket.close(1008, "Chat not found")
        return
    chat = chat_node.value

    print(f"Chat {chat_id} connected by {username}")

    # Verify that the user is a participant in the chat
    if username not in chat.participants:
        await websocket.close(1008, "User not a participant")
        return

    # Accept the WebSocket connection
    await websocket.accept()
    if chat_id not in active_connections:
        active_connections[chat_id] = []
    active_connections[chat_id].append(websocket)

    try:
        while True:
            # Receive message text from the client
            data = await websocket.receive_text()

            print(f"RECEIVED MESSAGE in chat {chat_id} from {username}: {data}")

            # Create a full message object
            message = {
                "id": str(uuid.uuid4()),  # Generate a unique ID
                "type": "message",
                "chat_id": chat_id,
                "sender": username,
                "message": data,
                "timestamp": datetime.now().isoformat()
            }

            # Add the message to the chat and save it
            chat.add_message(message)
            CHAT_MANAGER.save_chat_database()

            # Broadcast the message to all connected clients as JSON
            for connection in active_connections[chat_id]:
                await connection.send_json(message)

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Clean up the connection when it closes
        active_connections[chat_id].remove(websocket)
        if not active_connections[chat_id]:
            del active_connections[chat_id]

@router.websocket("/ws/{username}")
async def user_websocket_endpoint(websocket: WebSocket, username: str):
    print(f"User WebSocket connection attempt: username={username}")

    await websocket.accept()
    print (f"User WebSocket connected: {username}")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received message from {username}: {data}")

    except Exception as e:
        print(f"Error: {e}")

