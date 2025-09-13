import {v4 as uuidv4} from 'uuid';


export function truncateMessage(msg, maxLength = 25) {
  return msg && msg.length > maxLength ? msg.slice(0, maxLength - 2) + '...' : msg
}

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

export function formatNewMessageJSON(chatId, messageType, senderId, message){
  return {
    chat_id: chatId,
    message_type: messageType,
    message_id: uuidv4(),
    sender_id: senderId,
    message: message,
    time_sent: new Date().toISOString(),
  }
}

export function convertNewMessageJSONToMessage(messageJSON){
  return {
    messageStatus: "sending",
    chatId: messageJSON.chat_id,
    messageType: messageJSON.message_type,
    messageId: messageJSON.message_id,
    senderId: messageJSON.sender_id,
    message: messageJSON.message,
    timeSent: messageJSON.time_sent,
  }
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

export function formatChatUpdateJSON(chatId, changes){
  return {
    chat_id: chatId,
    changes: changes,
  }
}


export function initials(name) {
  if (!name) return '?'
  const cleaned = String(name)
    .replace(/@/g, '')                // remove leading @
    .replace(/[_-]/g, ' ')            // treat underscores/dashes as spaces
    .trim()
  const parts = cleaned.split(/\s+|,|&|and/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}
