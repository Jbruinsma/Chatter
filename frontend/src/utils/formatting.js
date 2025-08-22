import {v4 as uuidv4} from 'uuid';


export function formatDate(date) {
  const d = new Date(date);
  const month = String(d.getMonth() + 1).padStart(2, '0'); // getMonth is 0-indexed
  const day = String(d.getDate()).padStart(2, '0');
  const year = d.getFullYear();
  return `${month}/${day}/${year}`;
}

export function formatWebSocketPayload(operation, data) {
  const payload = {
    operation: operation,
    data: data,
  }
  return JSON.stringify(payload);
}


export function formatMessage(ID, messageType, senderUsername, messageContent){
  return {
    chat_id: ID,
    type: messageType,
    message_id: uuidv4(),
    sender: senderUsername,
    message: messageContent,
    timeStamp: new Date().toISOString(),
  };
}

export function formatNewChatJSON(newChatName, participantList, currentUser){
  return {
    chat_name: newChatName,
    participants: participantList,
    time_created: new Date().toISOString(),
    unread_messages_by: [currentUser],
    last_message: null,
    last_message_time: null
  };
}

export function formatNewDashboardChat(chatID, chatName, lastMessage, lastMessageTime, participants, timeCreated, unreadMessagesBy, permissionsList){
  return {
    chat_id: chatID,
    chat_name: chatName,
    last_message: lastMessage,
    last_message_time: lastMessageTime,
    participants: participants,
    time_created: timeCreated,
    unread_messages_by: unreadMessagesBy,
    participant_permissions: permissionsList,
  };
}

export function formatReadReceipt(chatID, username){
  return {
    chat_id: chatID,
    username: username,
  }
}

export function formatChatUpdate(chatID, editor,chatName, addedParticipants, removedParticipants, updatedPermissions){
  return {
    chat_id: chatID,
    editor_username: editor,
    chat_name: chatName,
    added_participants: addedParticipants,
    removed_participants: removedParticipants,
    updated_permissions: updatedPermissions,
  }
}
