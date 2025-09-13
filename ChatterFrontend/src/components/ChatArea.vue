<template>
  <div class="chat-area">
    <div class="chat-header">
      <h3 class="chat-title">{{ chatName }}</h3>
      <svg v-if="!websocket.activeChatIsRequest" @click="$emit('showChatInfo', props.chatInfo.chatId)" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="chat-icon">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356 .133 .751 .072 1.076 -.124 .072 -.044 .146 -.086 .22 -.128 .332 -.183 .582 -.495 .644 -.869 l.214 -1.28Z" />
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
      </svg>
    </div>

    <div class="message-list" ref="messageListRef">
      <div
        v-for="(message, idx) in websocket.activeChatMessageStore"
        :key="message.messageId ?? `${message.senderId || 'sys'}-${idx}`"
        class="message-container"
        :class="{
          'other-message': message.messageType !== 'system' && (message.senderId !== (props.currentUserId)),
          'self-message':  message.messageType !== 'system' && (message.senderId === (props.currentUserId)),
          'system-message': message.messageType === 'system'
        }"
      >
        <!-- Other user's message -->
        <template v-if="message.messageType !== 'system' && (message.senderId !== (props.currentUserId))">
          <router-link
            v-if="idx === 0 || websocket.activeChatMessageStore[idx - 1]?.senderId !== message.senderId"
            class="pfp-link"
            :to="`/profile/${message.senderId}`"
            :title="'@' + (props.chatInfo?.participantsById?.[message.senderId]?.username || 'Unknown User')"
          >
            <div class="pfp">
              <img
                v-if="avatarSrc(message.senderId) && !avatarError[message.senderId]"
                :src="avatarSrc(message.senderId)"
                class="pfp-img"
                alt="User avatar"
                loading="lazy"
                decoding="async"
                @error="avatarError[message.senderId] = true"
              />
              <div v-else class="pfp-fallback">
                {{ initialsFor(message.senderId, message.senderUsername) }}
              </div>
            </div>
          </router-link>
          <div v-else class="pfp-spacer" aria-hidden="true"></div>

          <div class="other-stack">
            <div
              class="message-meta other"
              v-if="idx === 0 || websocket.activeChatMessageStore[idx - 1]?.senderId !== message.senderId"
            >
              <span class="meta-username">
                {{
                  props.chatInfo?.participantsById?.[message.senderId]?.username || message.senderUsername || 'Unknown User'
                }}
              </span>
              <span class="meta-sep">•</span>
              <span class="meta-time">
                {{ message.timeSent ? (new Date(message.timeSent).toLocaleDateString() + ', ' + new Date(message.timeSent).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })) : '' }}
              </span>
            </div>

            <div class="message message-other">
              <div class="text-box">{{ message.message }}</div>
            </div>
          </div>
        </template>

        <!-- Current user's message -->
        <template v-else-if="message.messageType !== 'system' && (message.senderId === (props.currentUserId || props.currentUser))">
          <div
            class="message-meta self"
            v-if="idx === 0 || websocket.activeChatMessageStore[idx - 1]?.senderId !== (props.currentUserId || props.currentUser)"
          >
            <span class="meta-username">
              {{
                props.chatInfo?.participantsById?.[props.currentUserId || props.currentUser]?.username
                || 'you'
              }}
            </span>
            <span class="meta-sep">•</span>
            <span class="meta-time">
              {{ message.timeSent ? (new Date(message.timeSent).toLocaleDateString() + ', ' + new Date(message.timeSent).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })) : '' }}
            </span>
          </div>

          <div class="message message-user">
            <div class="text-box">{{ message.message }}</div>
          </div>
        </template>

        <!-- System message -->
        <template v-else>
          <div class="message message-system" role="status" aria-live="polite">
            <div class="text-box">{{ message.message }}</div>
          </div>
        </template>
      </div>
    </div>

    <div
      v-if="websocket.activeChatIsRequest"
      class="request-modal"
      role="dialog"
      aria-labelledby="request-title"
      aria-describedby="request-desc"
    >
      <div class="request-content">
        <div class="request-text">
          <div id="request-title" class="request-title">This chat is a request from @{{
              props.chatInfo?.otherParticipant?.username
              || (Object.values(props.chatInfo?.participantsById || {}).find(p => p?.id !== (props.currentUserId || props.currentUser))?.username)
              || ''
            }}</div>
          <div id="request-desc" class="request-subtitle">
            You can’t send messages until you accept the request.
          </div>
        </div>
        <div class="request-actions">
          <button
            type="button"
            class="btn-decline"
            @click="declineChatRequest"
            aria-label="Decline chat request"
          >
            Decline
          </button>
          <button
            type="button"
            class="btn-accept"
            @click="acceptChatRequest"
            aria-label="Accept chat request"
          >
            Accept
          </button>
        </div>
      </div>
    </div>

    <div v-else class="message-input">
      <input v-model="newMessage" type="text" placeholder="Type your message..." @keyup.enter="sendMessage" />
      <button @click="sendMessage">Send</button>
    </div>
  </div>
</template>



<script setup>
/* =========================
   Imports
========================= */
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/websocket.js'
import { BASE_API_LINK } from '@/stores/variables.js'

/* =========================
   Props / Emits
========================= */
const props = defineProps({
  chatInfo: { type: Object, required: true },
  currentUserId: { type: String, required: true },
})
defineEmits(['showChatInfo', 'newMessage'])

/* =========================
   Stores / State
========================= */
const websocket = useChatStore()

const chatName = ref(null)
const messageListRef = ref(null)
const newMessage = ref('')
const busyAction = ref(false)

/* Avatars: track load errors per user so we can fall back to initials */
const avatarError = reactive({})

/* Who am I? (used in template to style self vs other messages) */
const me = computed(() => props.currentUserId)

/* =========================
   Helpers (media URLs & avatars)
========================= */
/** Normalize relative media paths (e.g. "/media/..." or "avatars/...") to absolute URLs */
function toAbsoluteMediaUrl(path) {
  if (!path) return ''
  if (path.startsWith('blob:') || /^https?:\/\//i.test(path)) return path
  const base = BASE_API_LINK.replace(/\/+$/, '')
  // supports both "/media/avatars/..." and "avatars/..."
  return path.startsWith('/media/')
    ? `${base}${path}`
    : `${base}/media/${path.replace(/^\/+/, '')}`
}

/** Best available display name for a user (for initials fallback) */
function displayName(userId, fallbackSenderUsername) {
  return (
    props.chatInfo?.participantsById?.[userId]?.username ||
    fallbackSenderUsername ||
    userId ||
    '?'
  )
}

/** Initials from a name (first letter of first two tokens; else first 2 chars) */
function initialsFor(userId, fallbackSenderUsername) {
  const name = (displayName(userId, fallbackSenderUsername) || '').trim()
  if (!name) return '?'
  const parts = name.split(/[\s_]+/).filter(Boolean)
  const letters = (parts[0]?.[0] || '') + (parts[1]?.[0] || '')
  return (letters || name.slice(0, 2)).toUpperCase()
}

/** Avatar src for a given userId ('' if none) */
function avatarSrc(userId) {
  const raw = props.chatInfo?.participantsById?.[userId]?.avatar || ''
  return raw ? toAbsoluteMediaUrl(raw) : ''
}

/* =========================
   Scrolling
========================= */
function scrollMessagesToBottom(opts = {}) {
  const { behavior = 'auto', force = true, threshold = 40 } = opts
  const el = messageListRef.value
  if (!el) return
  const nearBottom = el.scrollTop >= el.scrollHeight - el.clientHeight - threshold
  if (force || nearBottom) {
    if (el.scrollTo) el.scrollTo({ top: el.scrollHeight, behavior })
    else el.scrollTop = el.scrollHeight
  }
}

/* =========================
   Lifecycle
========================= */
onMounted(async () => {
  await loadChat()
})

/* When active chat changes in the store, reload content */
watch(
  () => websocket.activeChatID,
  async (newVal) => {
    if (!newVal) return
    await loadChat()
  }
)

/* When messages mutate, keep scrolled to bottom */
watch(
  () => websocket.activeChatMessageStore,
  async () => {
    await nextTick()
    scrollMessagesToBottom({ behavior: 'smooth', force: true })
  },
  { deep: true }
)

/* =========================
   Actions
========================= */
async function loadChat() {
  if (!props.chatInfo) return
  const invitedUserIds = props.chatInfo.invitedUsers || []
  if (invitedUserIds.includes(props.currentUserId)) {
    websocket.activeChatIsRequest = true
  }
  chatName.value = props.chatInfo.title || props.chatInfo.chatName || 'Chat'
  await fetchChatMessages()
  await nextTick()
  scrollMessagesToBottom({ behavior: 'auto', force: true })
  await sendReadReceipt()
}

async function fetchChatMessages() {
  await websocket.fetchChatMessages()
}

async function sendMessage() {
  const text = (newMessage.value || '').trim()
  if (!text) return
  const currentChatId = props.chatInfo.chatId
  await websocket.sendMessage(currentChatId, props.currentUserId, text)
  newMessage.value = ''
}

async function sendReadReceipt() {
  await websocket.sendReadReceipt()
}

async function declineChatRequest() {
  if (busyAction.value) return
  busyAction.value = true
  try {
    await websocket.declineChatRequest()
  } finally {
    busyAction.value = false
  }
}

async function acceptChatRequest() {
  if (busyAction.value) return
  busyAction.value = true
  try {
    await websocket.acceptChatRequest()
  } finally {
    busyAction.value = false
  }
}

/* =========================
   (Optional) expose methods to parent via template ref
   defineExpose({ scrollMessagesToBottom, acceptChatRequest, declineChatRequest })
========================= */
</script>



<style scoped>
.chat-area { display:flex; flex-direction:column; flex-grow:1; min-width:0; }
.chat-header { align-items:center; background-color:#1a1a1a; border-bottom:1px solid #333; display:flex; justify-content:space-between; padding:1rem; }
.chat-icon { cursor:pointer; height:22px; stroke:#ccc; transition:stroke .15s ease; width:22px; }
.chat-icon:hover { stroke:#e0e0e0; }
.chat-title { font-size:1.1rem; font-weight:700; }
.message { border-radius:12px; display:inline-block; max-width:68%; padding:0.5rem 0.7rem; width:auto; }
.message-container { align-items:flex-start; display:flex; gap:0.6rem; margin-bottom:0.8rem; width:100%; }
.message-container.other-message { justify-content:flex-start; margin-top:0.85rem; }
.message-container.self-message { align-items:flex-end; flex-direction:column; gap:0.14rem; justify-content:flex-end; }
.message-container.self-message .message-user { margin-left:0; }
.message-container.system-message { justify-content:center; }
.message-input { background-color:#1a1a1a; border-top:1px solid #333; display:flex; gap:0.5rem; padding:1rem; }
.message-input button { background-color:#3a3a3a; border:none; border-radius:8px; color:#f1f1f1; cursor:pointer; font-weight:700; padding:0.75rem 1.25rem; transition:filter .15s ease, transform .02s ease; }
.message-input button:hover { filter:brightness(1.1); }
.message-input button:active { transform:translateY(1px); }
.message-input button:focus-visible { outline:2px solid #6aa9ff; outline-offset:2px; }
.message-input input { background-color:#2a2a2a; border:none; border-radius:6px; color:#f1f1f1; flex-grow:1; padding:0.75rem; }
.message-list { flex-grow:1; overflow-x:hidden; overflow-y:auto; padding:1rem; }
.message-meta { align-items:center; color:#aaa; display:flex; font-size:.75rem; gap:0.35rem; margin:0; }
.message-meta.other { align-self:flex-start; margin-top:0.6rem; text-align:left; }
.message-meta.self { align-self:flex-end; margin-top:0.6rem; text-align:right; }
.message-other { background-color:#2a2a2a; color:#eaeaea; margin-right:auto; text-align:left; }
.message-system { background:none; color:#888; margin-left:auto; margin-right:auto; text-align:center; }
.message-user { background-color:#3a3a3a; color:#f1f1f1; margin-left:auto; max-width:56%; }
.meta-sep { opacity:.6; }
.meta-time { opacity:.85; }
.meta-username { color:#cfcfcf; font-weight:600; }
.other-stack { align-items:flex-start; display:flex; flex:1 1 auto; flex-direction:column; gap:0.14rem; max-width:calc(100% - 28px - 0.6rem); min-width:0; }
.pfp { align-items:center; aspect-ratio:1/1; background:#404040; border-radius:50%; color:#e6e6e6; display:flex; flex:0 0 28px; font-size:.8rem; font-weight:700; height:28px; justify-content:center; overflow:hidden; position:relative; user-select:none; width:28px; }
.pfp-fallback { align-items:center; color:#e6e6e6; display:flex; font-size:.8rem; font-weight:700; height:100%; justify-content:center; width:100%; }
.pfp-img { border-radius:50%; display:block; height:100%; object-fit:cover; object-position:center; width:100%; }
.pfp-link { align-self:flex-start; display:inline-flex; line-height:0; }
.pfp-link:focus-visible .pfp { outline:2px solid #888; outline-offset:2px; }
.pfp-spacer { align-self:flex-start; flex:0 0 28px; height:28px; width:28px; }
.request-actions { align-items:center; display:flex; flex-wrap:wrap; gap:0.5rem; }
.request-content { align-items:center; display:flex; flex-wrap:wrap; gap:0.75rem 1rem; justify-content:space-between; width:100%; }
.request-from { color:#eaeaea; font-weight:700; }
.request-modal { background-color:#1a1a1a; border-top:1px solid #333; padding:1rem; }
.request-subtitle { color:#c9c9c9; font-size:.9rem; }
.request-text { display:flex; flex-direction:column; gap:0.25rem; min-width:0; }
.request-title { color:#f1f1f1; font-size:1rem; font-weight:800; }
.text-box { hyphens:auto; line-height:1.35; margin:0; max-width:100%; overflow-wrap:break-word; white-space:pre-wrap; word-break:break-word; }
.btn-accept, .btn-decline { border:none; border-radius:8px; color:#f1f1f1; cursor:pointer; font-weight:800; padding:0.7rem 1.1rem; transition:filter .15s ease, transform .02s ease; }
.btn-accept { background-color:#2d6a4f; }
.btn-accept:hover { filter:brightness(1.1); }
.btn-accept:active { transform:translateY(1px); }
.btn-accept:focus-visible { outline:2px solid #73d0a6; outline-offset:2px; }
.btn-decline { background-color:#7a2e2e; }
.btn-decline:hover { filter:brightness(1.1); }
.btn-decline:active { transform:translateY(1px); }
.btn-decline:focus-visible { outline:2px solid #f39aa2; outline-offset:2px; }

@media (max-width:560px) {
  .message { max-width:84%; }
  .message-user { max-width:72%; }
  .request-actions { justify-content:flex-start; width:100%; }
}
</style>

