<template>
  <div class="dashboard">
    <aside class="sidebar">
      <div class="top-bar">
        <h2>Chats</h2>
      </div>

      <div class="profile-link action-grid" role="group" aria-label="Sidebar actions">
        <button @click="goToProfile">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="profile-icon">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17.982 18.725A7.488 7.488 0 0 0 12 15.75a7.488 7.488 0 0 0-5.982 2.975m11.963 0a9 9 0 1 0-11.963 0m11.963 0A8.966 8.966 0 0 1 12 21a8.966 8.966 0 0 1-5.982-2.275M15 9.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
          </svg>
          Profile
        </button>

        <button @click="goToSettings">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="profile-icon">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
          </svg>
          Settings
        </button>

        <button @click="openNewChat">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="profile-icon">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Chat
        </button>

        <button @click="openFollowRequests">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="profile-icon">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
          More
        </button>
      </div>

      <input v-if="chatStore.dashboardChats.length > 0" type="text" placeholder="Search chats..." class="search-bar" />

      <div class="chat-list" ref="chatListRef">
        <div
          v-for="chat in chatStore.dashboardChats"
          :key="chat.chat_id"
          :class="['chat-item', { active: chat.chat_id === chatStore.activeChatID }]"
          @click="selectChat(chat.chat_id)"
        >
          <div class="chat-name">{{ chat.chat_name }}</div>
          <div :class="['last-message', { unread: chat.unread_messages_by.includes(currentUser) }]">
            {{ truncateMessage(chat.last_message) }}
          </div>
        </div>
      </div>
    </aside>

    <ChatArea
      v-if="chatStore.activeChatID"
      :chat-id="chatStore.activeChatID"
      :chat-name="activeChatName"
      :current-user="currentUser"
      @show-chat-info="showChatInfoModal"
    />

    <main class="chat-area placeholder" v-else>
      <p v-if="chatStore.dashboardChats.length > 0">Select a chat to get started</p>
      <p v-else>Create a chat to get started</p>
    </main>

    <ChatInfo
      v-if="chatStore.showChatInfo"
      :chat="chatStore.dashboardChats.find(c => c.chat_id === chatStore.activeChatID)"
      @close="closeChatInfoModal"
      @leave-chat="onLeaveChat"
    />

    <ChatEditorModal
      v-if="editorOpen"
      :key="editorKey"
      mode="create"
      :chat="null"
      :active-username="currentUser"
      @submit="handleEditorSubmit"
      @cancel="handleEditorCancel"
    />

    <FollowRequestsModal
      v-if="showFollowRequests"
      :user-info="userInfo"
      @close="closeFollowRequests"
    />

  </div>
</template>


<script setup>
import { ref, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/userStore.js'
import { verifyLogin } from '@/utils/verification.js'
import ChatInfo from '@/components/ChatInfo.vue'
import ChatArea from '@/components/ChatArea.vue'
import ChatEditorModal from '@/components/ChatEditorModal.vue'
import { useChatStore } from '@/stores/websocket.js'
import FollowRequestsModal from "@/components/FollowRequestsModal.vue";

const router = useRouter()
const chatStore = ref(useChatStore())
const userStore = useUserStore()
const currentUser = ref(userStore.username)

const activeChatName = ref(null)

const editorOpen = ref(false)
const editorKey = ref(0)

const showFollowRequests = ref(false)

const chatListRef = ref(null)
function getChatListEl() { return chatListRef.value ?? document.querySelector('.chat-list') }
function scrollChatsToTop(opts = {}) {
  const { behavior = 'auto', force = true, threshold = 40 } = opts
  const el = getChatListEl(); if (!el) return
  if (force || el.scrollTop <= threshold) {
    if (el.scrollTo) el.scrollTo({ top: 0, behavior }); else el.scrollTop = 0
  }
}
watch(
  () => [chatStore.value.dashboardChats?.length, chatStore.value.dashboardChats?.[0]?.chat_id],
  async () => { await nextTick(); scrollChatsToTop({ behavior: 'auto', force: true }) },
  { immediate: true }
)

onMounted(async () => {
  await verifyLogin()
  chatStore.value.connect(currentUser.value)
  await chatStore.value.fetchDashboardChatPreviews()
  await nextTick()
  scrollChatsToTop({ behavior: 'auto', force: true })
})

async function selectChat(id) {
  if (chatStore.value.activeChatID === id) {
    chatStore.value.exitChat(id)
  } else {
    const currentChatIndex = chatStore.value.switchChat(chatStore.value.activeChatID, id)
    const currentChat = chatStore.value.dashboardChats[currentChatIndex]
    activeChatName.value = currentChat?.chat_name
  }
}

function openNewChat() {
  editorKey.value += 1
  editorOpen.value = true
}

function openFollowRequests() {
  showFollowRequests.value = true
}

function closeFollowRequests() {
  showFollowRequests.value = false
}

function goToProfile() { router.push(`/profile/${userStore.username}`) }

function goToSettings() { router.push('/settings') }

function truncateMessage(msg) { return msg && msg.length > 25 ? msg.slice(0, 25) + '...' : msg }

function showChatInfoModal(chatId) {
  const id = chatId ?? chatStore.value.activeChatID; if (!id) return
  const exists = chatStore.value.dashboardChats.some(c => c.chat_id === id); if (!exists) return
  chatStore.value.toggleShowChatInfo()
}

function handleEditorCancel() {
  editorOpen.value = false
}

async function handleEditorSubmit(payload) {
  const { mode, data } = payload || {}
  if (mode === 'create'){
    const chatName = data.chatName
    const participantList = data.participants
    const participantPermissionList = data.permissions
    chatStore.value.createChat(chatName, participantList, participantPermissionList)
  }
  editorOpen.value = false
}

function closeChatInfoModal(){
  chatStore.value.toggleShowChatInfo()
  chatStore.value.sendReadReceipt()
}

function onLeaveChat(chatId) {
  chatStore.value.toggleShowChatInfo()
  chatStore.value.leaveChat(chatId)
}

</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
.chat-area { display:flex; flex-direction:column; flex-grow:1; min-width:0; }
.chat-area.placeholder { align-items:center; color:#777; display:flex; font-size:1.2rem; justify-content:center; }
.chat-header { align-items:center; background-color:#1a1a1a; border-bottom:1px solid #333; display:flex; justify-content:space-between; padding:1rem; }
.chat-icon { cursor:pointer; height:22px; stroke:#ccc; width:22px; }
.chat-item { background-color:#262626; border-radius:6px; cursor:pointer; margin-bottom:0.5rem; padding:0.75rem; transition:background-color 0.2s ease; }
.chat-item.active { background-color:#444; }
.chat-item:hover { background-color:#333; }
.chat-list { flex-grow:1; overflow-y:auto; }
.chat-name { font-weight:600; margin-bottom:0.25rem; }
.chat-title { font-size:1.1rem; font-weight:bold; }
.dashboard { align-items:stretch; background-color:#0d0d0d; color:#f1f1f1; display:flex; font-family:'Roboto Mono', monospace; height:100vh; overflow:hidden; width:100vw; }
.dashboard > :not(.sidebar) { display:flex; flex:1 1 auto; flex-direction:column; min-width:0; overflow:hidden; }
.error-message { background-color:#2a0000; border-left:4px solid #ff4c4c; border-radius:6px; color:#ffb3b3; font-size:0.9rem; margin-bottom:1rem; padding:0.75rem 1rem; text-align:left; }
.last-message { color:#bbb; font-size:0.85rem; }
.last-message.unread { color:#fff; font-weight:bold; }
.message-input { background-color:#1a1a1a; border-top:1px solid #333; display:flex; gap:0.5rem; padding:1rem; }
.message-input button { background-color:#3a3a3a; border:none; border-radius:6px; color:#f1f1f1; cursor:pointer; font-weight:bold; padding:0.75rem 1.25rem; transition:background-color 0.2s ease; }
.message-input button:hover { background-color:#555; }
.message-input input { background-color:#2a2a2a; border:none; border-radius:6px; color:#f1f1f1; flex-grow:1; padding:0.75rem; }
.message-list { flex-grow:1; overflow-x:hidden; overflow-y:auto; padding:1rem; }
.profile-icon { height:18px; margin-right:8px; stroke:#f1f1f1; width:18px; }
.profile-link { margin-bottom:1rem; display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; }
.profile-link button { align-items:center; background:none; border:1px solid #555; border-radius:4px; color:#f1f1f1; cursor:pointer; display:flex; font-size:0.9rem; gap:0.5rem; padding:0.4rem 0.6rem; width:100%; }
.profile-link button:hover { background-color:#333; }
.search-bar { background-color:#2a2a2a; border:none; border-radius:6px; color:#f1f1f1; margin-bottom:1rem; padding:0.5rem; }
.sidebar { background-color:#1a1a1a; border-right:1px solid #333; display:flex; flex:0 0 300px; flex-direction:column; max-width:300px; min-width:300px; overflow:auto; padding:1rem; width:300px; }
.top-bar { align-items:center; display:flex; justify-content:space-between; margin-bottom:1rem; }
.top-bar button { background:none; border:1px solid #555; border-radius:4px; color:#f1f1f1; cursor:pointer; padding:0.25rem 0.5rem; }
.top-bar h2 { color:#f1f1f1; font-size:1.2rem; }
</style>
