<template>
  <div v-if="chat" class="chatinfo-overlay" @keydown.esc="emit('close')" tabindex="-1">
    <div class="chatinfo-backdrop" @click="emit('close')"></div>

    <div class="chatinfo-modal" role="dialog" aria-modal="true" aria-labelledby="chatinfo-title" @click.stop>
      <button class="chatinfo-close" @click="emit('close')" aria-label="Close">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="chatinfo-close-icon">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"/>
        </svg>
      </button>

      <div class="chatinfo-header">
        <div class="chatinfo-avatar"></div>
        <h2 id="chatinfo-title">{{ chat.chat_name }}</h2>
        <div class="chatinfo-created">Created: {{ formatDate(chat.time_created) }}</div>

        <div class="chatinfo-actions">
          <button class="action-btn danger" aria-label="Leave chat" title="Leave chat" @click="openLeaveConfirm">
            <svg xmlns="http://www.w3.org/2000/svg" class="action-icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15M12 9l-3 3m0 0 3 3m-3-3h12.75"/>
            </svg>
          </button>
          <button class="action-btn" aria-label="Add or edit users" title="Add or edit users" @click="openEditor">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="action-icon">
              <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125" />
            </svg>
          </button>
        </div>
      </div>

      <div class="chatinfo-content">
        <section class="chatinfo-section">
          <h3>Participants</h3>
          <div class="list-frame">
            <ul>
              <li v-for="(user, idx) in chat.participants" :key="idx">
                <router-link :to="`/profile/${user}`" class="user-link">
                  <span class="user-name">{{ user }}</span>
                </router-link>
              </li>
            </ul>
          </div>
        </section>

        <section v-if="chat.messages?.length" class="chatinfo-section">
          <h3>Latest Message</h3>
          <div class="latest-msg">
            <div class="meta">
              <span class="sender">{{ chat.messages[chat.messages.length - 1].sender }}</span>
              <span class="time">{{ formatDate(chat.messages[chat.messages.length - 1].time_sent) }}</span>
            </div>
            <p class="body">{{ chat.messages[chat.messages.length - 1].message }}</p>
          </div>
        </section>
      </div>
    </div>

    <div v-if="showConfirmLeave" class="confirm-overlay" @keydown.esc="cancelLeave" tabindex="-1">
      <div class="confirm-backdrop" @click="cancelLeave"></div>
      <div
        class="confirm-modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        :aria-describedby="isViewerOwner ? 'confirm-desc owner-note' : 'confirm-desc'"
        @click.stop
      >
        <h3 id="confirm-title" class="confirm-title">Leave this chat?</h3>

        <p id="confirm-desc" class="confirm-desc">
          You won’t receive new messages from this chat unless someone adds you back.
        </p>

        <p v-if="isViewerOwner" id="owner-note" class="confirm-desc">
          You are the owner; a new random owner will be chosen.
        </p>

        <div class="confirm-actions">
          <button class="confirm-btn" @click="cancelLeave" type="button">Cancel</button>
          <button class="confirm-btn danger" @click="confirmLeave" type="button">Leave</button>
        </div>
      </div>
    </div>

    <ChatEditorModal
      v-if="editorOpen"
      :key="editorKey"
      mode="edit"
      :chat="chat"
      :active-username="viewerUsername"
      @submit="onEditorSubmit"
      @cancel="onEditorCancel"
    />
  </div>
</template>

<script setup>
import { defineProps, defineEmits, ref, computed } from 'vue'
import ChatEditorModal from '@/components/ChatEditorModal.vue'
import { useUserStore } from '@/stores/userStore.js'
import { formatDate } from '@/utils/formatting.js'
import {useChatStore} from "@/stores/websocket.js";

const props = defineProps({ chat: { type: Object, required: false }})
const emit = defineEmits(['close', 'remove-participant', 'leave-chat'])

const showConfirmLeave = ref(false)
function openLeaveConfirm () { showConfirmLeave.value = true }
function cancelLeave () { showConfirmLeave.value = false }
function confirmLeave () {
  const id = props.chat?.chat_id ?? props.chat?.id
  emit('leave-chat', id)
  showConfirmLeave.value = false
}

const editorOpen = ref(false)
const editorKey = ref(0)

const userStore = useUserStore()
const viewerUsername = computed(() => userStore.username)

function openEditor () {
  if (!props.chat) return
  editorKey.value += 1
  editorOpen.value = true
}
function onEditorCancel () {
  editorOpen.value = false
}
async function onEditorSubmit (payload) {

  const mode = payload.mode

  if (mode === 'edit') {
    const changes = payload.changes

    const chatID = payload.chatId
    const updatedChatName = changes.chatName
    const updatedPermissions = changes.permissions || {}
    const removedParticipants = changes.removedParticipants || []
    const addedParticipants = changes.addedParticipants || []

    const webSocket = useChatStore()
    await webSocket.updateChat(chatID, updatedChatName, addedParticipants, removedParticipants, updatedPermissions)
  }
  editorOpen.value = false
}

const isViewerOwner = computed(() => {
  const perms = props.chat?.participant_permissions || {}
  const user = userStore.username
  return !!(user && perms[user]?.can_delete)
})

</script>


<style scoped>
#chatinfo-title { font-size: 1.2rem; margin: 0; }
.action-btn { background: #232323; border: 1px solid #2f2f2f; border-radius: 10px; color: #ccc; cursor: pointer; display: inline-flex; gap: 0.4rem; padding: 6px; transition: background .15s ease-in-out, border-color .15s ease-in-out; }
.action-btn.danger { background: #281b1b; border-color: #3a2424; color: #ff6b6b; }
.action-btn.danger:hover { background: #341f1f; border-color: #4a2b2b; }
.action-btn:hover { background: #2a2a2a; border-color: #3a3a3a; }
.action-icon { height: 18px; width: 18px; }
.chatinfo-actions { display: flex; gap: 0.5rem; justify-content: center; margin-top: 0.25rem; }
.chatinfo-avatar { background: #333; border-radius: 50%; height: 80px; width: 80px; }
.chatinfo-backdrop { backdrop-filter: blur(2px); background: rgba(0,0,0,0.6); inset: 0; position: fixed; }
.chatinfo-close { background: #1a1a1a; border: none; border-radius: 10px; color: #ccc; cursor: pointer; padding: 6px; position: absolute; right: 10px; top: 10px; }
.chatinfo-close:hover { background: #333; }
.chatinfo-close-icon { height: 20px; width: 20px; }
.chatinfo-content { overflow-y: auto; padding: 1rem 1.1rem 1.1rem; }
.chatinfo-created { color: #999; font-size: 0.85rem; margin-bottom: 0.25rem; }
.chatinfo-header { border-bottom: 1px solid #333; display: grid; gap: 0.5rem; justify-items: center; padding: 1.1rem 1.1rem 0.7rem; }
.chatinfo-modal { background-color: #1a1a1a; border: 1px solid #333; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.6); display: flex; flex-direction: column; max-height: 85vh; overflow: hidden; position: relative; width: min(560px,92vw); }
.chatinfo-overlay { align-items: center; display: flex; inset: 0; justify-content: center; min-height: 100dvh; position: fixed; z-index: 1000; }
.chatinfo-section + .chatinfo-section { margin-top: 1rem; }
.chatinfo-section h3 { color: #ddd; font-size: 1rem; margin: 0 0 0.5rem; }
.list-frame { border: 1px solid #2a2a2a; border-radius: 12px; overflow: hidden; }
ul { list-style: none; margin: 0; padding: 0; }
li { align-items: stretch; border-bottom: 1px solid #2a2a2a; color: #ccc; display: flex; padding: 0; }
li:last-child { border-bottom: none; }
.user-link { align-items: center; border-radius: 10px; color: #e2e2e2; display: flex; gap: 0.5rem; padding: 0.65rem 0.85rem; text-decoration: none; transition: background .15s ease-in-out, color .15s ease-in-out, transform .08s ease-in-out; width: 100%; }
.user-link:visited { color: #e2e2e2; }
.user-link:hover .user-name { font-style: italic; }
.user-link:active { transform: translateY(1px); }
.user-link:focus-visible { outline: 2px solid #5a5a5a; outline-offset: 2px; }
.user-name { font-weight: 500; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-name::before { color: #888; content: "@"; margin-right: 6px; }
.confirm-title, .confirm-desc { text-align: center; }
.confirm-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 0.75rem; }
.confirm-backdrop { background: rgba(0,0,0,0.6); inset: 0; position: fixed; }
.confirm-btn { background: #232323; border: 1px solid #2f2f2f; border-radius: 10px; color: #e6e6e6; cursor: pointer; padding: 8px 10px; transition: background .15s ease-in-out, border-color .15s ease-in-out; }
.confirm-btn.danger { background: #3a2424; border-color: #4a2b2b; color: #ff8b8b; }
.confirm-btn.danger:hover { background: #452a2a; border-color: #583333; }
.confirm-btn:hover { background: #2a2a2a; border-color: #3a3a3a; }
.confirm-desc { color: #b3b3b3; font-size: 0.95rem; margin: 0.25rem 0 0; }
.confirm-modal { background-color: #1a1a1a; border: 1px solid #333; border-radius: 14px; box-shadow: 0 10px 40px rgba(0,0,0,0.6); max-width: 420px; padding: 1rem 1.1rem 1.1rem; position: relative; width: 92vw; }
.confirm-overlay { align-items: center; display: flex; inset: 0; justify-content: center; position: fixed; z-index: 1010; }
.confirm-title { color: #fff; font-size: 1.05rem; margin: 0; }
.latest-msg .body { color: #e6e6e6; margin: 0.35rem 0 0; }
.latest-msg .meta { color: #aaa; display: flex; font-size: 0.85rem; gap: 0.5rem; }
#owner-note { color: #ff8b8b; margin-top: 1rem; }
@media (min-width: 1400px) { .chatinfo-modal { width: 520px; } }
</style>
