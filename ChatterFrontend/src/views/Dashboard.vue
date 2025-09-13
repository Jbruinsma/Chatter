<template>
  <div class="dashboard">
    <aside class="sidebar">
      <div class="top-bar">
        <h2>Chats</h2>
        <button
          class="notif-btn"
          type="button"
          aria-label="Open notifications"
          title="Notifications"
          @click="goToNotifications"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            class="notif-icon"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0"
            />
          </svg>
        </button>
      </div>

      <div class="profile-link action-grid" role="group" aria-label="Sidebar actions">
        <button @click="goToProfile">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            class="profile-icon"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M17.982 18.725A7.488 7.488 0 0 0 12 15.75a7.488 7.488 0 0 0-5.982 2.975m11.963 0a9 9 0 1 0-11.963 0m11.963 0A8.966 8.966 0 0 1 12 21a8.966 8.966 0 0 1-5.982-2.275M15 9.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
            />
          </svg>
          Profile
        </button>

        <button @click="goToSettings">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            class="profile-icon"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
            />
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
            />
          </svg>
          Settings
        </button>

        <button @click="openNewChat">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            class="profile-icon"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Chat
        </button>

        <button @click="openFollowRequests">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            class="profile-icon"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
            />
          </svg>
          More
        </button>
      </div>

      <!-- Messages / Requests Toggle -->
      <div class="mr-toggle" role="tablist" aria-label="Messages and Requests">
        <button
          class="mr-tab"
          :class="{ active: activeTab === 'messages' }"
          role="tab"
          :aria-selected="activeTab === 'messages'"
          @click="activeTab = 'messages'"
        >
          Messages
        </button>
        <button
          class="mr-tab"
          :class="{ active: activeTab === 'requests' }"
          role="tab"
          :aria-selected="activeTab === 'requests'"
          @click="activeTab = 'requests'"
        >
          {{ requestsCount > 0 ? 'Requests (' + requestsCount + ')' : 'Requests' }}
        </button>
      </div>

      <!-- Requests list -->
      <div class="chat-list" v-show="activeTab === 'requests'">
        <div v-if="requestsCount === 0" class="empty-state">No chat requests</div>
        <div
          v-else
          v-for="req in chatRequestsList"
          :key="req.chatId || req.id"
          class="chat-item request"
          @click="selectChat(req.chatId || req.id)"
        >
          <div class="chat-cover">
            <img v-if="req.chatCover || req.avatar" :src="req.chatCover || req.avatar" alt="" />
            <div v-else class="chat-cover placeholder">
              {{ initials(req.title || req.chatName || req.name) }}
            </div>
          </div>

          <div class="chat-name">{{ req.title || req.chatName || req.name || 'Untitled' }}</div>

          <div :class="['last-message', { unread: !!req.hasUnreadMessages }]">
            {{ truncateMessage(req.lastMessage) }}
          </div>
        </div>
      </div>

      <!-- Messages list -->
      <div v-if="activeTab === 'messages' && dashboardChats.length === 0" class="empty-state">
        No messages
      </div>

      <div class="chat-list" ref="chatListRef" v-show="activeTab === 'messages'">
        <div
          v-for="chat in dashboardChats"
          :key="chat.chatId"
          :class="['chat-item', { active: chat.chatId === activeChatID }]"
          @click="selectChat(chat.chatId)"
        >
          <div class="chat-cover">
            <img v-if="chat.chatCover || chat.avatar" :src="chat.chatCover || chat.avatar" alt="" />
            <div v-else class="chat-cover placeholder">
              {{ initials(chat.title || chat.chatName) }}
            </div>
          </div>

          <div class="chat-name">{{ chat.title || chat.chatName }}</div>
          <div :class="['last-message', { unread: !!chat.hasUnreadMessages }]">
            {{ truncateMessage(chat.lastMessage, 25) }}
          </div>
        </div>
      </div>
    </aside>

    <!-- Main chat area -->
    <ChatArea
      v-if="activeChatID"
      :chat-info="chatStore.activeChatInfo"
      :current-user-id="currentUserUUID"
      @show-chat-info="showChatInfoModal"
    />

    <main class="chat-area placeholder" v-else>
      <p v-if="dashboardChats.length > 0">Select a chat to get started</p>
      <p v-else>Create a chat to get started</p>
    </main>

    <!-- Chat info modal -->
    <ChatInfo
      v-if="showChatInfo"
      :chat-info="chatStore.activeChatInfo"
      @close="closeChatInfoModal"
      @leave-chat="onLeaveChat"
    />

    <!-- New chat modal -->
    <ChatEditorModal
      v-if="editorOpen"
      :key="editorKey"
      mode="create"
      :chat="null"
      :active-user-id="currentUserUUID"
      :active-username="username"
      @submit="handleEditorSubmit"
      @cancel="handleEditorCancel"
    />

    <!-- Follow requests modal -->
    <FollowRequestsModal
      v-if="showFollowRequests"
      @close="closeFollowRequests"
    />

    <!-- Confirmation / Error banners -->
    <teleport to="body">
      <div
        v-if="
          chatStore.dashboardSuccessMessage ||
          chatStore.dashboardErrorMessage ||
          chatStore.dashboardNotificationMessage
        "
        :class="['notice-stack', 'top']"
        role="region"
        aria-label="Notifications"
      >
        <!-- Notification (gray) -->
        <transition name="notice-slide" appear>
          <div
            v-if="chatStore.dashboardNotificationMessage"
            class="notice notice-notification notification-banner"
            role="status"
            aria-live="polite"
            tabindex="0"
            @click="onNotificationClick"
          >
            <div class="notice-content">
              <svg
                class="notice-icon"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  d="M12 2a10 10 0 1 0 .001 20.001A10 10 0 0 0 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"
                />
              </svg>
              <div class="notice-text">
                <strong class="notice-title">Notification</strong>
                <p class="notice-message">{{ chatStore.dashboardNotificationMessage.message }}</p>
              </div>
              <button
                class="notice-close"
                type="button"
                aria-label="Dismiss notification"
                @click="closeNotificationBanner"
              >
                &times;
              </button>
            </div>
          </div>
        </transition>

        <!-- Success -->
        <transition name="notice-slide" appear>
          <div
            v-if="chatStore.dashboardSuccessMessage"
            class="notice notice-success"
            role="status"
            aria-live="polite"
            tabindex="0"
          >
            <div class="notice-content">
              <svg
                class="notice-icon"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  d="M12 2a10 10 0 1 0 .001 20.001A10 10 0 0 0 12 2zm-1 14.2-4.2-4.2 1.4-1.4L11 13.6l4.8-4.8 1.4 1.4L11 16.2z"
                />
              </svg>
              <div class="notice-text">
                <strong class="notice-title">Success</strong>
                <p class="notice-message">{{ chatStore.dashboardSuccessMessage }}</p>
              </div>
              <button
                class="notice-close"
                type="button"
                aria-label="Dismiss success"
                @click="closeSuccessBanner"
              >
                &times;
              </button>
            </div>
          </div>
        </transition>

        <!-- Error -->
        <transition name="notice-slide" appear>
          <div
            v-if="chatStore.dashboardErrorMessage"
            class="notice notice-error"
            role="alert"
            aria-live="assertive"
            tabindex="0"
          >
            <div class="notice-content">
              <svg
                class="notice-icon"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" />
              </svg>
              <div class="notice-text">
                <strong class="notice-title">Error</strong>
                <p class="notice-message">{{ chatStore.dashboardErrorMessage }}</p>
              </div>
              <button
                class="notice-close"
                type="button"
                aria-label="Dismiss error"
                @click="closeErrorBanner"
              >
                &times;
              </button>
            </div>
          </div>
        </transition>
      </div>
    </teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/userStore.js'
import { verifyLogin } from '@/utils/verification.js'
import ChatInfo from '@/components/ChatInfo.vue'
import ChatArea from '@/components/ChatArea.vue'
import ChatEditorModal from '@/components/ChatEditorModal.vue'
import { useChatStore } from '@/stores/websocket.js'
import FollowRequestsModal from '@/components/FollowRequestsModal.vue'
import { initials, truncateMessage } from '@/utils/formatting.js'

const router = useRouter()

const chatStore = useChatStore()
const { dashboardChats, chatRequests, activeChatID, activeTab, showChatInfo } =
  storeToRefs(chatStore)

const userStore = useUserStore()
const { uuid: currentUserUUID, username } = storeToRefs(userStore)

const editorOpen = ref(false)
const editorKey = ref(0)
const showFollowRequests = ref(false)

const chatRequestsList = chatRequests
const requestsCount = computed(() => chatRequests.value.length)
const requestSum = ref(0)

const chatListRef = ref(null)
function getChatListEl() {
  return chatListRef.value ?? document.querySelector('.chat-list')
}
function scrollChatsToTop(opts = {}) {
  const { behavior = 'auto', force = true, threshold = 40 } = opts
  const el = getChatListEl()
  if (!el) return
  if (force || el.scrollTop <= threshold) {
    if (el.scrollTo) el.scrollTo({ top: 0, behavior })
    else el.scrollTop = 0
  }
}

watch(
  () => [dashboardChats.value.length, dashboardChats.value[0]?.chat_id],
  async () => {
    await nextTick()
    scrollChatsToTop({ behavior: 'auto', force: true })
  },
  { immediate: true },
)

onMounted(async () => {
  if (!currentUserUUID.value) {
    await router.push('/')
    return
  }
  chatStore.connect(currentUserUUID.value)
  await chatStore.fetchDashboardChatPreviews()
  requestSum.value = chatRequests.value.length
  await nextTick()
  scrollChatsToTop({ behavior: 'auto', force: true })
})

onUnmounted(async () => {
  chatStore.exitChat()
})

async function selectChat(id) {
  if (activeChatID.value === id) {
    chatStore.exitChat()
  } else {
    chatStore.switchChat(activeChatID.value, id)
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

function goToProfile() {
  router.push(`/profile/${username.value}`)
}

function goToSettings() {
  router.push('/settings')
}

function goToNotifications() {
  router.push('/notifications')
}

function showChatInfoModal(chatId) {
  const id = chatId ?? activeChatID.value
  if (!id) return
  const exists = dashboardChats.value.some((c) => c.chatId === id)
  if (!exists) return
  chatStore.toggleShowChatInfo()
}

function handleEditorCancel() {
  editorOpen.value = false
}

const editorModalBusy = ref(false)

async function handleEditorSubmit(payload) {
  if (editorModalBusy.value) return
  editorModalBusy.value = true
  try {
    await chatStore.createChat(payload)
  } finally {
    editorOpen.value = false
    editorModalBusy.value = false
  }
}

function closeChatInfoModal() {
  chatStore.toggleShowChatInfo()
  chatStore.sendReadReceipt()
}

function onLeaveChat(chatId) {
  chatStore.toggleShowChatInfo()
  chatStore.leaveChat(chatId)
}

function onNotificationClick() {
  const notificationFunction = chatStore.dashboardNotificationMessage?.function

  if (notificationFunction === 'toProfile') {
    const uuid = chatStore.dashboardNotificationMessage.uuid
    router.push(`/profile/${uuid}`)
  } else {
    const chatId = chatStore.dashboardNotificationMessage.chatId
    enterChatThroughNotification(chatId)
  }
}

function enterChatThroughNotification(chatId) {
  if (chatId) {
    selectChat(chatId)
  }
  chatStore.resetDashboardNotificationMessage()
}

function closeNotificationBanner() {
  chatStore.resetDashboardNotificationMessage()
}

function closeSuccessBanner() {
  chatStore.resetDashboardSuccessMessage()
}

function closeErrorBanner() {
  chatStore.resetDashboardErrorMessage()
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
.chat-area { display:flex; flex-direction:column; flex-grow:1; min-width:0; }
.chat-area.placeholder { align-items:center; color:#777; display:flex; font-size:1.2rem; justify-content:center; }
.chat-cover { align-items:center; aspect-ratio:1; background:#2a2a2e; border-radius:50%; display:flex; flex:0 0 44px; height:44px; justify-content:center; overflow:hidden; width:44px; }
.chat-cover img { display:block; height:100%; object-fit:cover; width:100%; }
.chat-cover.placeholder { align-items:center; background:#2a2a2e; border-radius:50%; color:#e5e5e7; display:flex; font-size:14px; font-weight:700; height:44px; justify-content:center; width:44px; }
.chat-header { align-items:center; background-color:#1a1a1a; border-bottom:1px solid #333; display:flex; justify-content:space-between; padding:1rem; }
.chat-icon { cursor:pointer; height:22px; stroke:#ccc; width:22px; }
.chat-item { align-items:center; background-color:#262626; border-radius:6px; column-gap:12px; cursor:pointer; display:grid; grid-auto-rows:min-content; grid-template-columns:44px 1fr; margin-bottom:0.5rem; padding:0.75rem; transition:background-color 0.2s ease; }
.chat-item .chat-cover { grid-column:1; grid-row:1 / span 2; }
.chat-item .chat-name { grid-column:2; margin:0 0 0.25rem 0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.chat-item .last-message { grid-column:2; margin:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.chat-item.active { background-color:#444; }
.chat-item:hover { background-color:#333; }
.chat-item.request { opacity:0.95; }
.chat-list { flex-grow:1; overflow-y:auto; }
.chat-name { font-weight:600; margin-bottom:0.25rem; }
.chat-title { font-size:1.1rem; font-weight:bold; }
.dashboard { align-items:stretch; background-color:#0d0d0d; color:#f1f1f1; display:flex; font-family:'Roboto Mono', monospace; height:100vh; overflow:hidden; width:100vw; }
.dashboard > :not(.sidebar) { display:flex; flex:1 1 auto; flex-direction:column; min-width:0; overflow:hidden; }
.empty-state { align-items:center; color:#888; display:flex; font-size:0.9rem; justify-content:center; margin:0.75rem 0; text-align:center; width:100%; }
.error-message { background-color:#2a0000; border-left:4px solid #ff4c4c; border-radius:6px; color:#ffb3b3; font-size:0.9rem; margin-bottom:1rem; padding:0.75rem 1rem; text-align:left; }
.last-message { color:#bbb; font-size:0.85rem; }
.last-message.unread { color:#fff; font-weight:bold; }
.message-input { background-color:#1a1a1a; border-top:1px solid #333; display:flex; gap:0.5rem; padding:1rem; }
.message-input button { background-color:#3a3a3a; border:none; border-radius:6px; color:#f1f1f1; cursor:pointer; font-weight:bold; padding:0.75rem 1.25rem; transition:background-color 0.2s ease; }
.message-input button:hover { background-color:#555; }
.message-input input { background-color:#2a2a2a; border:none; border-radius:6px; color:#f1f1f1; flex-grow:1; padding:0.75rem; }
.message-list { flex-grow:1; overflow-x:hidden; overflow-y:auto; padding:1rem; }
.mr-tab { background:transparent; border:none; border-radius:0; color:#fff; cursor:pointer; font-size:0.95rem; font-weight:500; margin:0; outline:none; padding:0.25rem 0; }
.mr-tab.active { font-weight:700; }
.mr-tab:hover { opacity:1; }
.mr-tab:focus-visible { outline:2px solid currentColor; outline-offset:2px; }
.mr-tab:not(.active) { opacity:0.8; }
.mr-toggle { align-items:center; display:flex; gap:1.25rem; justify-content:center; margin:0.5rem 0 0; padding:0.25rem 0; width:100%; }
.notif-btn { align-items:center; background:none; border:1px solid #555; border-radius:4px; color:#f1f1f1; cursor:pointer; display:flex; padding:0.25rem 0.5rem; }
.notif-icon { display:block; height:18px; stroke:#f1f1f1; width:18px; }
.notice { align-items:center; background-color:#1a1a1a; border:1px solid #333; border-left:4px solid #555; border-radius:10px; box-shadow:0 8px 24px rgba(0, 0, 0, 0.35); color:#eaeaea; margin:8px 0; max-width:720px; pointer-events:auto; width:calc(100% - 2rem); }
.notice-close { background:transparent; border:none; color:inherit; cursor:pointer; font-size:1.25rem; line-height:1; margin-left:auto; opacity:0.9; padding:0.25rem 0.4rem; transition:opacity 0.2s ease; }
.notice-close:hover { opacity:1; }
.notice-content { align-items:center; display:flex; gap:12px; padding:0.9rem 1rem; }
.notice-error { background-color:#2a0000; border-color:#4a1a1a; border-left-color:#ff4c4c; color:#ffb3b3; }
.notice-icon { flex:0 0 20px; height:20px; opacity:0.95; width:20px; }
.notice-message { font-size:0.9rem; line-height:1.35; margin:0; opacity:0.95; }
.notice-notification { background-color:#1f1f1f; border-color:#333; border-left-color:#9e9e9e; color:#e0e0e0; }
.notice-slide-enter-active, .notice-slide-leave-active { transition:opacity 0.25s ease, transform 0.25s ease; }
.notice-slide-enter-from, .notice-slide-leave-to { opacity:0; transform:translateY(-12px); }
.notice-stack { display:flex; justify-content:center; left:0; padding:0 1rem; pointer-events:none; position:fixed; right:0; z-index:1000; }
.notice-stack.bottom { bottom:12px; }
.notice-stack.bottom .notice-slide-enter-from, .notice-stack.bottom .notice-slide-leave-to { transform:translateY(12px); }
.notice-stack.top { top:12px; }
.notice-success { background-color:#062a16; border-color:#1a3d2a; border-left-color:#2bd46b; color:#b1f0c5; }
.notice-text { display:flex; flex-direction:column; gap:2px; }
.notice-title { font-size:0.95rem; font-weight:700; line-height:1.2; margin:0; }
.notification-banner { cursor:pointer; }
.profile-icon { height:18px; margin-right:8px; stroke:#f1f1f1; width:18px; }
.profile-link { display:grid; gap:0.5rem; grid-template-columns:1fr 1fr; margin-bottom:1rem; }
.profile-link button { align-items:center; background:none; border:1px solid #555; border-radius:4px; color:#f1f1f1; cursor:pointer; display:flex; font-size:0.9rem; gap:0.5rem; padding:0.4rem 0.6rem; width:100%; }
.profile-link button:hover { background-color:#333; }
.search-bar { background-color:#2a2a2a; border:none; border-radius:6px; color:#f1f1f1; margin-bottom:1rem; padding:0.5rem; }
.sidebar { background-color:#1a1a1a; border-right:1px solid #333; display:flex; flex:0 0 300px; flex-direction:column; max-width:300px; min-width:300px; overflow:auto; padding:1rem; width:300px; }
.top-bar { align-items:center; display:flex; justify-content:space-between; margin-bottom:1rem; }
.top-bar button { background:none; border:1px solid #555; border-radius:4px; color:#f1f1f1; cursor:pointer; padding:0.25rem 0.5rem; }
.top-bar h2 { color:#f1f1f1; font-size:1.2rem; }
</style>
