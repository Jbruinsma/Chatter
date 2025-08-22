<template>
  <div class="chat-area">
    <div class="chat-header">
      <h3 class="chat-title">{{ chatName }}</h3>
      <svg @click="$emit('showChatInfo', chatId)" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="chat-icon">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
      </svg>
    </div>

    <div class="message-list" ref="messageListRef">
      <div
        v-for="(message, idx) in webSocket.activeChatMessageStore"
        :key="message.message_id ?? `${message.sender}-${idx}`"
        class="message-container"
        :class="{
          'other-message': message.sender !== props.currentUser && message.sender !== 'System',
          'self-message': message.sender === props.currentUser,
          'system-message': message.sender === 'System'
        }"
      >
        <template v-if="message.sender !== props.currentUser && message.sender !== 'System'">
          <router-link
            v-if="idx === 0 || webSocket.activeChatMessageStore[idx - 1]?.sender !== message.sender"
            class="pfp-link"
            :to="`/profile/${message.sender}`"
            :title="message.sender"
          >
            <div class="pfp">{{ (message.sender?.[0] || '').toUpperCase() }}</div>
          </router-link>
          <div v-else class="pfp-spacer" aria-hidden="true"></div>

          <div class="other-stack">
            <div
              class="message-meta other"
              v-if="idx > 0 && webSocket.activeChatMessageStore[idx - 1]?.sender !== message.sender"
            >
              <span class="meta-username">{{ message.sender }}</span>
              <span class="meta-sep">•</span>
              <span class="meta-time">
                {{
                  (message.time_sent || message.time_created || message.timeStamp || message.timestamp)
                    ? (new Date(message.time_sent || message.time_created || message.timeStamp || message.timestamp).toLocaleDateString() + ', ' +
                      new Date(message.time_sent || message.time_created || message.timeStamp || message.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }))
                    : ''
                }}
              </span>
            </div>

            <div class="message message-other">
              <div class="text-box">{{ message.message }}</div>
            </div>
          </div>
        </template>

        <template v-else-if="message.sender === props.currentUser">
          <div
            class="message-meta self"
            v-if="idx > 0 && webSocket.activeChatMessageStore[idx - 1]?.sender !== props.currentUser"
          >
            <span class="meta-username">{{ props.currentUser }}</span>
            <span class="meta-sep">•</span>
            <span class="meta-time">
              {{
                (message.time_sent || message.time_created || message.timeStamp || message.timestamp)
                  ? (new Date(message.time_sent || message.time_created || message.timeStamp || message.timestamp).toLocaleDateString() + ', ' +
                    new Date(message.time_sent || message.time_created || message.timeStamp || message.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }))
                  : ''
              }}
            </span>
          </div>

          <div class="message message-user">
            <div class="text-box">{{ message.message }}</div>
          </div>
        </template>

        <template v-else>
          <div class="message message-system">
            <div class="text-box">{{ message.message }}</div>
          </div>
        </template>
      </div>
    </div>

    <div class="message-input">
      <input v-model="newMessage" type="text" placeholder="Type your message..." @keyup.enter="sendMessage" />
      <button @click="sendMessage">Send</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/websocket.js'

const props = defineProps({
  chatId: { type: String, required: true },
  chatName: { type: String, required: true },
  currentUser: { type: String, required: true }
})

defineEmits(['showChatInfo', 'newMessage'])

const messageListRef = ref(null)
const newMessage = ref('')
const webSocket = ref(useChatStore())

function scrollMessagesToBottom(opts = {}) {
  const { behavior = 'auto', force = true, threshold = 40 } = opts
  const el = messageListRef.value
  if (!el) return
  if (force || el.scrollTop >= el.scrollHeight - el.clientHeight - threshold) {
    if (el.scrollTo) el.scrollTo({ top: el.scrollHeight, behavior })
    else el.scrollTop = el.scrollHeight
  }
}

onMounted(async () => {
  await loadChat()
})

watch(
  () => webSocket.value.activeChatID,
  async (newValue, oldValue) => {
    if (oldValue === null) return
    await loadChat()
  }
)

watch(
  () => webSocket.value.activeChatMessageStore,
  async () => {
    await nextTick()
    scrollMessagesToBottom({ behavior: 'smooth', force: true })
  },
  { deep: true }
)

async function loadChat(){
  await fetchChatMessages()
  await nextTick()
  scrollMessagesToBottom({ behavior: 'auto', force: true })
  await sendReadReceipt()
}

async function fetchChatMessages() {
  await webSocket.value.fetchChatMessages()
}

async function sendMessage() {
  webSocket.value.sendMessage(props.chatId, props.currentUser, newMessage.value)
  newMessage.value = ''
}

async function sendReadReceipt(){
  webSocket.value.sendReadReceipt()
}

</script>

<style scoped>
.chat-area { display:flex; flex-direction:column; flex-grow:1; min-width:0; }
.chat-header { align-items:center; background-color:#1a1a1a; border-bottom:1px solid #333; display:flex; justify-content:space-between; padding:1rem; }
.chat-icon { cursor:pointer; height:22px; stroke:#ccc; width:22px; }
.chat-title { font-size:1.1rem; font-weight:700; }
.message-list { flex-grow:1; overflow-x:hidden; overflow-y:auto; padding:1rem; }
.message-container { align-items:flex-start; display:flex; gap:0.6rem; margin-bottom:0.8rem; width:100%; }
.message-container.other-message { justify-content:flex-start; margin-top:0.85rem; }
.message-container.self-message { align-items:flex-end; flex-direction:column; gap:0.14rem; justify-content:flex-end; }
.message-container.system-message { justify-content:center; }
.other-stack { align-items:flex-start; display:flex; flex:1 1 auto; flex-direction:column; gap:0.14rem; max-width:calc(100% - 28px - 0.6rem); min-width:0; }
.pfp { align-items:center; background:#404040; border-radius:50%; color:#e6e6e6; display:flex; flex:0 0 28px; font-size:.8rem; font-weight:700; height:28px; justify-content:center; user-select:none; width:28px; }
.pfp-link { align-self:flex-start; display:inline-flex; line-height:0; text-decoration:none; }
.pfp-link:focus-visible .pfp { outline:2px solid #888; outline-offset:2px; }
.pfp-spacer { align-self:flex-start; flex:0 0 28px; height:28px; width:28px; }
.message { border-radius:12px; display:inline-block; max-width:68%; padding:0.5rem 0.7rem; width:auto; }
.message-other { background-color:#2a2a2a; color:#eaeaea; margin-right:auto; text-align:left; }
.message-system { background:none; color:#888; margin-left:auto; margin-right:auto; text-align:center; }
.message-user { background-color:#3a3a3a; color:#f1f1f1; margin-left:auto; max-width:56%; }
.message-container.self-message .message-user { margin-left:0; }
.text-box { hyphens:auto; line-height:1.35; margin:0; max-width:100%; overflow-wrap:break-word; white-space:pre-wrap; word-break:break-word; }
.message-meta { align-items:center; color:#aaa; display:flex; font-size:.75rem; gap:0.35rem; margin:0; }
.message-meta.other { align-self:flex-start; margin-top:0.6rem; text-align:left; }
.message-meta.self { align-self:flex-end; margin-top:0.6rem; text-align:right; }
.meta-sep { opacity:.6; }
.meta-time { opacity:.85; }
.meta-username { color:#cfcfcf; font-weight:600; }
.message-input { background-color:#1a1a1a; border-top:1px solid #333; display:flex; gap:0.5rem; padding:1rem; }
.message-input button { background-color:#3a3a3a; border:none; border-radius:8px; color:#f1f1f1; cursor:pointer; font-weight:700; padding:0.75rem 1.25rem; }
.message-input button:hover { filter:brightness(1.1); }
.message-input input { background-color:#2a2a2a; border:none; border-radius:6px; color:#f1f1f1; flex-grow:1; padding:0.75rem; }
</style>
