import { defineStore } from 'pinia';
import { ref } from 'vue';
import { fetchAPI, getWebSocketUrl, postToAPI } from '@/utils/api.js';
import {
  convertNewMessageJSONToMessage,
  formatChatUpdateJSON,
  formatNewMessageJSON,
  formatReadReceipt,
  formatWebSocketPayload,
  truncateMessage
} from '@/utils/formatting.js';
import { BASE_API_LINK } from '@/stores/variables.js';
import { useUserStore } from '@/stores/userStore.js';

export const useChatStore = defineStore('chat', () => {
  const webSocket = ref(null);
  const isOpen = ref(false);
  const user = ref(null);

  const activeTab = ref('messages');

  const notificationPreferences = ref({
    essential: true,
    messages: true
  });

  const dashboardSuccessMessage = ref('');
  const dashboardErrorMessage = ref('');
  const dashboardNotificationMessage = ref('');

  const dashboardChats = ref([]);
  const chatRequests = ref([]);
  const activeChatMessageStore = ref([]);
  const activeChatIsRequest = ref(false);

  const activeChatID = ref(null);
  const activeChatIndex = ref(-1);
  const activeChatInfo = ref(null);

  const showChatInfo = ref(false);

  const notificationStore = ref([]);

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  function login(user_uuid, notificationPreferencesParam) {
    if (!user_uuid) return;
    user.value = user_uuid;
    notificationPreferences.value = notificationPreferencesParam;
  }

  function connect(user_uuid) {
    if (!user_uuid) return;
    if (webSocket.value && isOpen.value) return;

    user.value = user_uuid;
    const webSocketUrl = getWebSocketUrl(`/ws/${user_uuid}`);
    webSocket.value = new WebSocket(webSocketUrl);

    webSocket.value.onopen = function () {
      isOpen.value = true;
    };

    webSocket.value.onmessage = async (event) => {
      let incomingJSON;
      try {
        if (typeof event.data === 'string') {
          incomingJSON = JSON.parse(event.data);
        } else if (event.data instanceof Blob) {
          incomingJSON = JSON.parse(await event.data.text());
        } else {
          incomingJSON = event.data;
        }
      } catch (e) {
        console.error('Bad WS JSON:', e, event.data);
        return;
      }

      const operation = incomingJSON.operation;
      const type = incomingJSON.type;
      console.log('INCOMING JSON: ', incomingJSON);
      console.log('OPERATION: ', operation);

      if (operation === 'update_chat') {
        const chatId = incomingJSON.chatId;
        let { chatIndex, chatCategory } = findChatIndexDetail(chatId);
        if (chatIndex === -1) return;

        const updatedChatInfo = await fetchChatInfo(chatId);
        if (updatedChatInfo === null || updatedChatInfo === undefined) return;
        if (chatCategory === 'requests' && !updatedChatInfo.invitedUsers.includes(user.value)) return;

        if (chatCategory === 'messages') {
          dashboardChats.value[chatIndex] = updatedChatInfo;
        } else if (chatCategory === 'requests') {
          chatRequests.value[chatIndex] = updatedChatInfo;
        } else {
          await setDashboardErrorMessage('Internal error: unknown chat category');
          return;
        }

        if (chatId === activeChatID.value) {
          const { chatIndex } = findChatIndexDetail(chatId);
          activeChatInfo.value = dashboardChats.value[chatIndex];
        }
      } else if (operation === 'create_chat') {
        await fetchDashboardChatPreviews();
      } else if (operation === 'leave_chat') {
        const info = incomingJSON.data;
        const chatId = info.chatId;
        deleteChatFromDashboard(chatId);
      } else if (operation === 'deleted_chat') {
        deleteChatFromDashboard(incomingJSON.chatId);
      } else if (operation === 'leave_chat_confirmation') {
        const leaveChatInfo = incomingJSON.data;
        const chatId = leaveChatInfo.chatId;

        await exitChat();
        const { chatIndex } = findChatIndexDetail(chatId);
        if (chatIndex === -1) return;
        dashboardChats.value.splice(chatIndex, 1);
      } else if (operation === 'receive_message') {
        const messageInfo = incomingJSON.messageInfo;
        if (messageInfo === null || messageInfo === undefined) return;
        const chatId = messageInfo.chatId;

        updateDashboardChatPreviews(messageInfo, incomingJSON.hasUnreadMessages);

        const messageId = messageInfo.messageId;
        const messageIndex = findMessageIndex(messageId);

        if (chatId === activeChatID.value) {
          await sendReadReceipt();
          if (messageIndex === -1) {
            activeChatMessageStore.value.push(messageInfo);
          }
        }
      } else if (operation === 'message_delivered') {
        const acknowledgementData = incomingJSON.data;
        const chatId = acknowledgementData.chatId;
        const messageId = acknowledgementData.messageId;

        const { chatIndex } = findChatIndexDetail(chatId);
        if (chatIndex === -1) return;

        const messageIndex = findMessageIndex(messageId);
        if (messageIndex === -1) return;

        if (chatId === activeChatID.value) {
          const messageIndex2 = findMessageIndex(messageId);
          activeChatMessageStore.value[messageIndex2].messageStatus = 'delivered';
        }
      } else if (operation === 'read_receipt') {
        const readReceiptInfo = incomingJSON.data;
        const chatId = readReceiptInfo.chatId;
        const hasUnreadMessages = readReceiptInfo.hasUnreadMessages;
        const { chatIndex, chatCategory } = findChatIndexDetail(chatId);
        if (chatIndex === -1) return;
        if (chatCategory === 'messages') {
          dashboardChats.value[chatIndex].hasUnreadMessages = hasUnreadMessages;
        } else if (chatCategory === 'requests') {
          chatRequests.value[chatIndex].hasUnreadMessages = hasUnreadMessages;
        } else {
          console.error('Unknown chat category:', chatCategory);
        }
      } else if (operation === 'decline_chat_request') {
        const declinedChatInfo = incomingJSON.data;
        const chatId = declinedChatInfo.chatId;
        if (chatId === activeChatID.value) {
          exitChat();
        }

        const { chatIndex } = findChatIndexDetail(chatId);
        if (chatIndex === -1) return;
        chatRequests.value.splice(chatIndex, 1);
      } else if (operation === 'accept_chat_request') {
        exitChat();
        const acceptedChatInfo = incomingJSON.data;
        const chatId = acceptedChatInfo.chatId;

        await fetchDashboardChatPreviews();
        activeTab.value = 'messages';
        enterChat(chatId);
      } else if (operation === 'notification') {
        const notificationPayload = incomingJSON.notification;
        await setDashboardNotification(notificationPayload);
      } else {
        console.log('Unknown operation:', operation);
      }

      if (type !== undefined) {
        const essentialNotificationsAllowed = notificationPreferences.value.essential;
        const payload = incomingJSON.data;
        const message = payload.message;

        if (essentialNotificationsAllowed) {
          await setDashboardBanner(type, message);
        }
      }
    };
  }

  async function setDashboardBanner(type, message) {
    if (type === 'acknowledgement') {
      await setDashboardSuccessMessage(message);
    } else if (type === 'error') {
      await setDashboardErrorMessage(message);
    } else {
      console.error('Unknown type:', type);
    }
  }

  function disconnect() {
    if (webSocket.value && isOpen.value) {
      webSocket.value.close();
      isOpen.value = false;
      console.log('WebSocket connection closed');
    }
  }

  function verifyWebSocket() {
    return webSocket.value && webSocket.value.readyState === WebSocket.OPEN;
  }

  async function sendNotification(notificationPayload) {
    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload('send_notification', notificationPayload);
      webSocket.value.send(payload);
    }
  }

  function enterChat(chatID) {
    if (!chatID || chatID === activeChatID.value) return;
    switchChat(activeChatID, chatID);
  }

  function exitChat() {
    activeChatID.value = null;
    activeChatIsRequest.value = false;
    activeChatMessageStore.value = [];
    activeChatInfo.value = null;
  }

  function switchChat(oldChatID, newChatID) {
    if (oldChatID === newChatID) return;
    const { chatIndex } = findChatIndexDetail(newChatID);
    if (chatIndex === -1) {
      setDashboardErrorMessage('Could not load chat.');
      return;
    }
    activeChatMessageStore.value = [];
    activeChatID.value = newChatID;
    activeChatInfo.value =
      activeTab.value === 'messages' ? dashboardChats.value[chatIndex] : chatRequests.value[chatIndex];
  }

  function deleteChatFromDashboard(chatId) {
    const { chatIndex, chatCategory } = findChatIndexDetail(chatId);
    if (chatIndex === -1) return;

    if (chatId === activeChatID.value) {
      exitChat();
    }

    if (chatCategory === 'messages') {
      dashboardChats.value.splice(chatIndex, 1);
    } else if (chatCategory === 'requests') {
      chatRequests.value.splice(chatIndex, 1);
    } else {
      console.error('Unknown chat category:', chatCategory);
    }
  }

  function updateActiveChatID(chatID) {
    activeChatID.value = chatID;
  }

  function findChatIndexDetail(chatID) {
    const matchReq = chatRequests.value.findIndex((c) => c.chatId === chatID);
    const matchMsg = dashboardChats.value.findIndex((c) => c.chatId === chatID);

    if (matchReq !== -1 && matchMsg !== -1) return { chatIndex: matchReq, chatCategory: 'requests' };
    if (matchReq !== -1) return { chatIndex: matchReq, chatCategory: 'requests' };
    if (matchMsg !== -1) return { chatIndex: matchMsg, chatCategory: 'messages' };
    return { chatIndex: -1, chatCategory: null };
  }

  function findMessageIndex(messageId) {
    if (activeChatMessageStore.value.length === 0) return -1;
    if (!activeChatID.value) return -1;
    return activeChatMessageStore.value.findIndex((message) => message.messageId === messageId);
  }

  function sendMessage(chatID, senderUUID, message) {
    if (message.trim() === '') return;
    if (verifyWebSocket()) {
      const newMessageInfo = formatNewMessageJSON(chatID, 'message', senderUUID, message);
      const payload = formatWebSocketPayload('send_message', newMessageInfo);
      webSocket.value.send(payload);
      const convertedMessageInfo = convertNewMessageJSONToMessage(newMessageInfo);
      activeChatMessageStore.value.push(convertedMessageInfo);
    } else {
      console.error('WebSocket is not open');
    }
  }

  async function fetchChatInfo(chatId) {
    if (chatId === null || chatId === undefined) return;
    try {
      const url = `${BASE_API_LINK}/chats/${user.value}/${chatId}`;
      const response = await fetchAPI(url);
      if (response.error) return;
      return response.chat;
    } catch (error) {
      console.error('Error fetching chat info:', error);
    }
  }

  async function fetchChatMessages() {
    const chatID = activeChatID.value;
    if (chatID === null || chatID === undefined) return;
    try {
      const url = `${BASE_API_LINK}/chats/${user.value}/${chatID}/messages`;
      const response = await fetchAPI(url);
      activeChatMessageStore.value = response.messages || [];
    } catch (error) {
      console.error('Error fetching messages:', error);
    }
  }

  async function sendReadReceipt() {
    const chatID = activeChatID.value;
    if (chatID === null || chatID === undefined) return;
    if (user.value === null || user.value === undefined) return;
    if (activeChatIsRequest.value) return;

    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload('read_receipt', formatReadReceipt(chatID, user.value));
      webSocket.value.send(payload);
    }
  }

  async function fetchDashboardChatPreviews() {
    if (user.value === null || user.value === undefined) return;
    try {
      const url = `${BASE_API_LINK}/chats/${user.value}`;
      const response = await fetchAPI(url);
      const mainChatSummaries = response.chats.main || [];
      const chatRequestSummaries = response.chats.requests || [];
      dashboardChats.value = [...(mainChatSummaries ?? [])].sort((a, b) => {
        const ta = Date.parse(a.lastMessageSentAt ?? a.createdAt ?? 0) || 0;
        const tb = Date.parse(b.lastMessageSentAt ?? b.createdAt ?? 0) || 0;
        if (tb !== ta) return tb - ta;
        return (a.chat_name || '').localeCompare(b.chat_name || '');
      });
      chatRequests.value = [...(chatRequestSummaries ?? [])].sort((a, b) => {
        const ta = Date.parse(a.lastMessageSentAt ?? a.createdAt ?? 0) || 0;
        const tb = Date.parse(b.lastMessageSentAt ?? b.createdAt ?? 0) || 0;
        if (tb !== ta) return tb - ta;
        return (a.chat_name || '').localeCompare(b.chat_name || '');
      });
    } catch (error) {
      console.log(error);
    }
  }

  function updateDashboardChatPreviews(newMessageInfo, hasUnreadMessages) {
    const newMessageChatID = newMessageInfo.chatId;
    const { chatIndex, chatCategory } = findChatIndexDetail(newMessageChatID);
    if (chatIndex === -1) return;
    if (chatIndex !== 0) pushChatToTop(chatIndex, chatCategory);

    if (chatCategory === 'messages') {
      dashboardChats.value[0].lastMessage = newMessageInfo.message;
      dashboardChats.value[0].hasUnreadMessages = hasUnreadMessages;
    } else if (chatCategory === 'requests') {
      chatRequests.value[0].lastMessage = newMessageInfo.message;
      chatRequests.value[0].hasUnreadMessages = hasUnreadMessages;
    } else {
      console.error('Invalid chat category');
    }

    const senderId = newMessageInfo.senderId;
    if (senderId === user.value) return;
    const chatNotificationsAllowed = notificationPreferences.value.messages;

    if (chatNotificationsAllowed) {
      if (newMessageChatID !== activeChatID.value) {
        const { chatIndex: idx, chatCategory: cat } = findChatIndexDetail(newMessageChatID);
        if (idx === -1) return;

        const chatInfo = cat === 'messages' ? dashboardChats.value[idx] : chatRequests.value[idx];
        const chatName = chatInfo.chatName;

        const senderUsername =
          senderId === 'system'
            ? 'SYSTEM'
            : chatInfo.participantsById?.[senderId]?.username ?? 'Unknown user';

        const message = `${chatName}: ${senderUsername === 'SYSTEM' ? '' : `(@${senderUsername}) `}${truncateMessage(
          newMessageInfo.message,
          35
        )}`;
        const notificationPayload = {
          function: 'toChat',
          chatId: newMessageChatID,
          message: message
        };

        if (cat === 'messages') {
          setDashboardNotification(notificationPayload);
        }
      }
    }
  }

  function pushChatToTop(chatIndex, chatCategory = 'messages') {
    if (chatIndex === -1) return;
    if (chatIndex === 0) return;
    if (chatIndex >= dashboardChats.value.length) return;

    if (chatCategory === 'messages') {
      const [chat] = dashboardChats.value.splice(chatIndex, 1);
      dashboardChats.value.unshift(chat);
    } else if (chatCategory === 'requests') {
      const [chat] = chatRequests.value.splice(chatIndex, 1);
      chatRequests.value.unshift(chat);
    } else {
      console.error('Invalid chat category');
    }
  }

  function toggleShowChatInfo() {
    showChatInfo.value = !showChatInfo.value;
  }

  async function updateProfile(newUsername = null) {
    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload('update_profile', {});
      webSocket.value.send(payload);
      if (newUsername !== null) {
        const userStore = useUserStore();
        userStore.username = newUsername;
      }
    }
  }

  async function createDirectChat(participant1Id, participant2Id) {
    if (participant1Id === participant2Id) return;

    const chatInfo = {
      chat_name: '',
      chat_cover: '',
      owner_id: participant1Id,
      participant_ids: [participant1Id, participant2Id],
      participant_permissions: {
        [participant1Id]: { can_edit: true },
        [participant2Id]: { can_edit: true }
      },
      chat_type: 'direct'
    };
    await createChat(chatInfo);
  }

  async function createChat(newChatInfo) {
    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload('create_chat', newChatInfo);
      webSocket.value.send(payload);
    }
  }

  async function leaveChat(chatID) {
    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload('leave_chat', {
        chat_id: chatID
      });
      webSocket.value.send(payload);
    }
  }

  async function updateChat(updatedChatInfo) {
    if (verifyWebSocket()) {
      const chatId = updatedChatInfo.chatId;
      const changes = updatedChatInfo.changes;
      const payload = formatWebSocketPayload('update_chat', formatChatUpdateJSON(chatId, changes));
      webSocket.value.send(payload);
    }
  }

  async function acceptChatRequest() {
    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload('accept_chat_request', { chat_id: activeChatID.value });
      webSocket.value.send(payload);
    }
  }

  async function declineChatRequest() {
    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload('decline_chat_request', { chat_id: activeChatID.value });
      webSocket.value.send(payload);
    }
  }

  async function setDashboardNotification(message) {
    dashboardNotificationMessage.value = message;
    await sleep(5000);
    resetDashboardNotificationMessage();
  }

  async function setDashboardSuccessMessage(message) {
    dashboardSuccessMessage.value = message;
    await sleep(5000);
    resetDashboardSuccessMessage();
  }

  async function setDashboardErrorMessage(message) {
    dashboardErrorMessage.value = message;
    await sleep(5000);
    resetDashboardErrorMessage();
  }

  function resetDashboardSuccessMessage() {
    dashboardSuccessMessage.value = '';
  }

  function resetDashboardErrorMessage() {
    dashboardErrorMessage.value = '';
  }

  function resetDashboardNotificationMessage() {
    dashboardNotificationMessage.value = '';
  }

  function resetChatStore() {
    if (verifyWebSocket()) disconnect();
    webSocket.value = null;
    isOpen.value = false;
    user.value = null;
    activeChatID.value = null;
    dashboardChats.value = [];
    activeChatMessageStore.value = [];
  }

  return {
    webSocket,
    isOpen,
    user,
    activeTab,
    notificationPreferences,
    dashboardSuccessMessage,
    dashboardErrorMessage,
    dashboardNotificationMessage,
    dashboardChats,
    chatRequests,
    activeChatMessageStore,
    activeChatIsRequest,
    activeChatID,
    activeChatIndex,
    activeChatInfo,
    showChatInfo,
    notificationStore,
    login,
    connect,
    disconnect,
    verifyWebSocket,
    sendNotification,
    enterChat,
    exitChat,
    switchChat,
    updateActiveChatID,
    findChatIndexDetail,
    sendMessage,
    fetchChatMessages,
    sendReadReceipt,
    fetchDashboardChatPreviews,
    updateDashboardChatPreviews,
    pushChatToTop,
    toggleShowChatInfo,
    updateProfile,
    createDirectChat,
    createChat,
    leaveChat,
    updateChat,
    acceptChatRequest,
    declineChatRequest,
    resetChatStore,
    setDashboardNotification,
    setDashboardSuccessMessage,
    setDashboardErrorMessage,
    resetDashboardSuccessMessage,
    resetDashboardErrorMessage,
    resetDashboardNotificationMessage
  };
});
