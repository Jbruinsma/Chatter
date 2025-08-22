import {defineStore} from 'pinia'
import {ref} from 'vue'
import {fetchAPI, getWebSocketUrl} from '@/utils/api.js'
import {
  formatChatUpdate,
  formatMessage,
  formatNewDashboardChat,
  formatReadReceipt,
  formatWebSocketPayload
} from '@/utils/formatting.js'
import {BASE_API_LINK} from '@/stores/variables.js'

export const useChatStore = defineStore('chat', () => {
  const webSocket = ref(null)
  const isOpen = ref(false)
  const user = ref(null)

  const dashboardChats = ref([])
  const activeChatMessageStore = ref({})

  const activeChatID = ref(null)
  const activeChatIndex = ref(-1)
  const showChatInfo = ref(false)

  function connect(username) {
    if (!username) return
    if (webSocket.value && isOpen.value) return

    user.value = username
    const wsUrl = getWebSocketUrl(`/ws/${username}`)
    webSocket.value = new WebSocket(wsUrl)

    webSocket.value.onopen = function () {
      isOpen.value = true
      // console.log('WebSocket connection opened')
    }

    webSocket.value.onmessage = async (event) => {
      let incomingJSON
      try {
        if (typeof event.data === 'string') {
          incomingJSON = JSON.parse(event.data)
        } else if (event.data instanceof Blob) {
          incomingJSON = JSON.parse(await event.data.text())
        } else {
          incomingJSON = event.data
        }
      } catch (e) {
        console.error('Bad WS JSON:', e, event.data)
        return
      }

      const operation = incomingJSON.operation

      if (operation === 'enter_chat') {

        const chatID = incomingJSON.data.chat_id
        if (chatID !== activeChatID.value) { exitChat(activeChatID.value) }

      } else if (operation === 'message') {

        if (activeChatID.value !== null && activeChatID.value === incomingJSON.chat_id) activeChatMessageStore.value.push(incomingJSON)
        const unreadMessagesBy = incomingJSON.unread_messages_by
        updateDashboardChatPreviews(incomingJSON, unreadMessagesBy)

      } else if (operation === 'chat_created') {

        const newDashboardChat = formatNewDashboardChat(
          incomingJSON.chat_id,
          incomingJSON.chat_name,
          incomingJSON.last_message,
          incomingJSON.last_message_time,
          incomingJSON.participants,
          incomingJSON.time_created,
          incomingJSON.unread_messages_by,
          incomingJSON.participant_permissions,
        )
        dashboardChats.value.unshift(newDashboardChat)

      } else if (operation === 'read_receipt') {

        const chatId = incomingJSON.chat_id
        const chatIndex = findChatIndex(chatId)
        if (chatIndex === -1) return
        dashboardChats.value[chatIndex].unread_messages_by = incomingJSON.unread_messages_by

      } else if (operation === 'update_chat') {

        const chatID = incomingJSON.chat_id
        const newChatName = incomingJSON.chat_name
        const updatedParticipantList = incomingJSON.participants
        const updatedPermissionsList = incomingJSON.participant_permissions

        const chatIndex = findChatIndex(chatID)
        if (chatIndex === -1) {
          const newChat = formatNewDashboardChat(chatID, newChatName, incomingJSON.last_message, incomingJSON.last_message_time, updatedParticipantList, incomingJSON.time_created, incomingJSON.unread_messages_by, updatedPermissionsList,)
          dashboardChats.value.unshift(newChat)
          return
        }

        dashboardChats.value[chatIndex].chat_name = newChatName
        dashboardChats.value[chatIndex].participants = updatedParticipantList
        dashboardChats.value[chatIndex].participant_permissions = updatedPermissionsList

        if (!updatedParticipantList.includes(user.value)){
          dashboardChats.value.splice(chatIndex, 1)
          activeChatID.value = null
          activeChatMessageStore.value = []
        }

      } else if (operation === 'leave_chat') {

        const chatID = incomingJSON.data.chat_id
        const chatIndex = findChatIndex(chatID)
        if (chatIndex === -1) return

        dashboardChats.value.splice(chatIndex, 1)
        if (activeChatID.value === chatID) {
          activeChatID.value = null
          activeChatMessageStore.value = []
        }

      } else if (operation === 'update_user') {

        const chatID = incomingJSON.data.chat_id
        const oldUsername = incomingJSON.old_username
        const newUsername = incomingJSON.username

        if (chatID === null || chatID === undefined) return
        if (oldUsername === null || oldUsername === undefined) return
        if (newUsername === null || newUsername === undefined) return
        if (newUsername === user.value) return

        const chatIndex = findChatIndex(chatID)
        if (chatIndex === -1) return

        const oldParticipantUsernameIndex = dashboardChats.value[chatIndex].participants.indexOf(oldUsername)
        if (oldParticipantUsernameIndex !== -1)  dashboardChats.value[chatIndex].participants.splice(oldParticipantUsernameIndex, 1, newUsername)

        const oldReadReceiptUsernameIndex = dashboardChats.value[chatIndex].unread_messages_by.indexOf(oldUsername)
        if (oldReadReceiptUsernameIndex !== -1)  dashboardChats.value[chatIndex].unread_messages_by.splice(oldReadReceiptUsernameIndex, 1, newUsername)

      }

    }
  }

  function disconnect() {
    if (webSocket.value && isOpen.value) {
      webSocket.value.close()
      isOpen.value = false
      console.log('WebSocket connection closed')
    }
  }

  function verifyWebSocket() {
    return webSocket.value && webSocket.value.readyState === WebSocket.OPEN
  }

  async function enterChat(chatID) {
    if (!chatID || chatID === activeChatID.value) return
    if (verifyWebSocket()) {
      activeChatID.value = chatID
      webSocket.value.send(formatWebSocketPayload('enter_chat', { chat_id: chatID }))
      await fetchChatMessages(chatID)
    }
  }

  function exitChat(chatID) {
    if (verifyWebSocket()) {
      activeChatID.value = null
      webSocket.value.send(formatWebSocketPayload('exit_chat', { chat_id: chatID }))
      activeChatMessageStore.value = []
    }
  }

  function switchChat(oldChatID, newChatID) {
    if (verifyWebSocket()) {
      if (oldChatID === newChatID) return

      if (oldChatID !== null) webSocket.value.send(formatWebSocketPayload('exit_chat', { chat_id: oldChatID }))

      activeChatMessageStore.value = []
      activeChatID.value = newChatID

      if (newChatID !== null) {
        webSocket.value.send(formatWebSocketPayload('enter_chat', { chat_id: newChatID }))
        return findChatIndex(newChatID)
      }
    }
  }

  function updateActiveChatID(chatID) {
    activeChatID.value = chatID
  }

  function findChatIndex(chatID) {
    return dashboardChats.value.findIndex(chat => chat.chat_id === chatID)
  }

  function sendMessage(chatID, senderUsername, message) {
    if (message.trim() === '') return
    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload('send_message', formatMessage(chatID, 'message', senderUsername, message))
      webSocket.value.send(payload)
    } else {
      console.error('WebSocket is not open')
    }
  }

  async function fetchChatMessages() {
    const chatID = activeChatID.value
    if (chatID === null || chatID === undefined) return
    try {
      const url = `${BASE_API_LINK}/chats/user/${user.value}/chats/${chatID}`
      const response = await fetchAPI(url)
      activeChatMessageStore.value = response.messages || []
    } catch (error) {
      console.error('Error fetching messages:', error)
    }
  }

  async function sendReadReceipt(){
    const chatID = activeChatID.value
    if (chatID === null || chatID === undefined) return
    if (user.value === null || user.value === undefined) return

    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload("read_receipt" ,formatReadReceipt(chatID, user.value))
      webSocket.value.send(payload)
    }

  }

  async function fetchDashboardChatPreviews() {
    if (user.value === null || user.value === undefined) return
    try {
      const url = `${BASE_API_LINK}/chats/user/${user.value}/chats`
      const response = await fetchAPI(url)
      dashboardChats.value = [...(response.chats ?? [])].sort((a, b) => {
        const ta = Date.parse(a.last_message_time ?? a.time_created ?? 0) || 0
        const tb = Date.parse(b.last_message_time ?? b.time_created ?? 0) || 0
        if (tb !== ta) return tb - ta
        return (a.chat_name || '').localeCompare(b.chat_name || '')
      })
    } catch (error) {
      console.log(error)
    }
  }

  function updateDashboardChatPreviews(newMessageInfo, unreadMessagesBy) {
    const newMessageChatID = newMessageInfo.chat_id

    const chatIndex = findChatIndex(newMessageChatID)
    if (chatIndex === -1) return

    if (chatIndex !== 0) pushChatToTop(chatIndex)
    dashboardChats.value[0].last_message = newMessageInfo.message
    dashboardChats.value[0].last_message_time = newMessageInfo.time_sent
    dashboardChats.value[0].unread_messages_by = unreadMessagesBy
  }

  function pushChatToTop(chatIndex) {
    const [chat] = dashboardChats.value.splice(chatIndex, 1)
    dashboardChats.value.unshift(chat)
  }

  function toggleShowChatInfo(){
    showChatInfo.value = !showChatInfo.value
  }

  async function updateUsername(newUsername){
    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload('update_username', {
        new_username: newUsername,
        old_username: user.value
      })

      webSocket.value.send(payload)
      user.value = newUsername
      console.log('Updated username to: ', newUsername)

    }
  }

  async function createChat(chatName, participantList, participantPermissionsList) {
    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload('create_chat', { chat_name: chatName, participants: participantList, permissions: participantPermissionsList })
      webSocket.value.send(payload)
    }
  }

  async function leaveChat(chatID){
    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload('leave_chat', {chat_id: chatID})
      webSocket.value.send(payload)
    }
  }

  async function updateChat(chatID, newChatName, addedParticipantList, removedParticipants, updatedPermissionsList) {
    if (verifyWebSocket()) {
      const payload = formatWebSocketPayload('update_chat', formatChatUpdate(chatID, user.value,newChatName, addedParticipantList, removedParticipants, updatedPermissionsList))
      webSocket.value.send(payload)
    }
  }

  function resetChatStore() {
    if (verifyWebSocket()) disconnect()
    webSocket.value = null
    isOpen.value = false
    user.value = null
    activeChatID.value = null
    dashboardChats.value = []
    activeChatMessageStore.value = {}
  }

  return {
    webSocket,
    isOpen,
    user,
    dashboardChats,
    activeChatMessageStore,
    activeChatID,
    activeChatIndex,
    showChatInfo,
    connect,
    disconnect,
    verifyWebSocket,
    enterChat,
    exitChat,
    switchChat,
    updateActiveChatID,
    findChatIndex,
    sendMessage,
    fetchChatMessages,
    sendReadReceipt,
    fetchDashboardChatPreviews,
    updateDashboardChatPreviews,
    pushChatToTop,
    toggleShowChatInfo,
    updateUsername,
    createChat,
    leaveChat,
    updateChat,
    resetChatStore
  }
})
