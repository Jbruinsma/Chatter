<template>
  <div v-if="chat" ref="overlayRef" class="chatinfo-overlay" @keydown.esc="emit('close')" tabindex="-1">
    <div class="chatinfo-backdrop" @click="emit('close')"></div>

    <div class="chatinfo-modal" role="dialog" aria-modal="true" aria-labelledby="chatinfo-title" @click.stop>
      <button class="chatinfo-close" type="button" @click="emit('close')" aria-label="Close">
        <svg xmlns="http://www.w3.org/2000/svg" class="chatinfo-close-icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>

      <div class="chatinfo-header">
        <div class="chatinfo-avatar">
          <img v-if="displayAvatar" :src="displayAvatar" :alt="`${displayTitle} cover`" />
          <span v-else class="chatinfo-initials">{{ displayInitials }}</span>
        </div>
        <h2 id="chatinfo-title">{{ displayTitle }}</h2>
        <div class="chatinfo-created">Created: {{ formatDate(chat.createdAt) }}</div>

        <div class="chatinfo-actions">
          <button
            class="action-btn danger"
            type="button"
            aria-label="Leave chat"
            :title="isDirect ? 'Direct chats cannot be left' : 'Leave chat'"
            :disabled="isDirect"
            @click="openLeaveConfirm"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="action-icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15M12 9l-3 3m0 0 3 3m-3-3h12.75" />
            </svg>
          </button>

          <button
            v-if="chat.capabilities?.canEdit"
            class="action-btn"
            type="button"
            aria-label="Add or edit users"
            title="Add or edit users"
            @click="openEditor"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="action-icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
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
              <li v-for="u in participantList" :key="u.id">
                <router-link
                  :to="`/profile/${u.id}`"
                  class="user-link"
                  :aria-label="`Open profile for ${displayHandle(u)}`"
                >
                  <div class="user-avatar">
                    <img v-if="u.avatar" :src="u.avatar" :alt="`${u.username}'s avatar`" />
                    <span v-else>{{ initials(u.username || '') }}</span>
                  </div>
                  <span class="user-name">{{ displayHandle(u) }}</span>
                  <svg xmlns="http://www.w3.org/2000/svg" class="user-arrow" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M17.25 8.25 21 12m0 0-3.75 3.75M21 12H3" />
                  </svg>
                </router-link>
              </li>
            </ul>
          </div>
        </section>

        <section v-if="showInvitedSection" class="chatinfo-section">
          <h3>Invited Users</h3>
          <div class="list-frame">
            <ul>
              <li v-for="u in invitedList" :key="u.id">
                <router-link
                  :to="`/profile/${u.id}`"
                  class="user-link"
                  :aria-label="`Open profile for ${displayHandle(u)}`"
                >
                  <div class="user-avatar">
                    <img v-if="u.avatar" :src="u.avatar" :alt="`${u.username}'s avatar`" />
                    <span v-else>{{ initials(u.username || '') }}</span>
                  </div>
                  <span class="user-name">{{ displayHandle(u) }}</span>
                  <svg xmlns="http://www.w3.org/2000/svg" class="user-arrow" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M17.25 8.25 21 12m0 0-3.75 3.75M21 12H3" />
                  </svg>
                </router-link>
              </li>
            </ul>
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
          You are the owner of this chat. If you leave, a new owner will be chosen at random.
        </p>
        <div class="confirm-actions">
          <button class="confirm-btn" type="button" @click="cancelLeave">Cancel</button>
          <button class="confirm-btn danger" type="button" @click="confirmLeave">Leave</button>
        </div>
      </div>
    </div>

    <ChatEditorModal
      v-if="editorOpen"
      :key="editorKey"
      mode="edit"
      :chat="chat"
      :active-user-id="viewerId"
      :active-username="viewerUsername"
      @submit="onEditorSubmit"
      @cancel="onEditorCancel"
    />
  </div>
</template>


<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import ChatEditorModal from '@/components/ChatEditorModal.vue'
import { useUserStore } from '@/stores/userStore.js'
import { formatDate, initials } from '@/utils/formatting.js'
import { useChatStore } from '@/stores/websocket.js'

const props = defineProps({ chatInfo: { type: Object, required: false } })
const emit = defineEmits(['close', 'remove-participant', 'leave-chat'])

const chat = computed(() => props.chatInfo ?? null)

const showConfirmLeave = ref(false)
const editorOpen = ref(false)
const editorKey = ref(0)
const overlayRef = ref(null)

const userStore = useUserStore()
const viewerUsername = computed(() => userStore.username)
const viewerId = computed(() => userStore.uuid || userStore.id || null)

const isViewerOwner = computed(() => {
  if (!chat.value) return false
  if (viewerId.value && chat.value.ownerId === viewerId.value) return true
  const role = chat.value.capabilities?.role
  return role === 'Owner' || role === 'owner'
})

const isDirect = computed(() => {
  const c = chat.value
  if (!c) return false
  if (c.isDirect === true) return true
  const t = typeof c.type === 'string' ? c.type.toLowerCase() : ''
  return t === 'direct'
})

/* ---- Avatar URL normalization (handles relative /media/... paths) ---- */
const isHttp = (s) => typeof s === 'string' && /^https?:\/\//i.test(s)

const assetOrigin = computed(() => {
  const c = chat.value
  if (!c) return ''
  const candidates = [
    c.chatCover,
    c.avatar,
    c.otherParticipant?.avatar,
    ...Object.values(c.participantsById || {}).map(p => p?.avatar),
    ...Object.values(c.invitedParticipantsById || {}).map(p => p?.avatar),
  ].filter(isHttp)
  const first = candidates[0]
  try { return first ? new URL(first).origin : '' } catch { return '' }
})

function normalizeAvatar(src) {
  if (!src) return ''
  if (isHttp(src)) return src
  if (src.startsWith('/')) return assetOrigin.value ? `${assetOrigin.value}${src}` : src
  return src
}
/* --------------------------------------------------------------------- */

const displayTitle = computed(() =>
  isDirect.value ? (chat.value?.title ?? chat.value?.chatName ?? '') : (chat.value?.chatName ?? '')
)

const displayAvatar = computed(() => {
  if (!chat.value) return ''
  let src = ''
  if (isDirect.value) {
    src = chat.value.avatar || chat.value.otherParticipant?.avatar || chat.value.chatCover || ''
  } else {
    src = chat.value.chatCover || ''
  }
  return normalizeAvatar(src)
})

const displayInitials = computed(() => initials(displayTitle.value || ''))

const participantList = computed(() => {
  const ids = chat.value?.participantIds || []
  const map = chat.value?.participantsById || {}
  return ids.map(id => {
    const u = map[id] || {}
    return {
      id,
      username: u.username || id,
      avatar: normalizeAvatar(u.avatar || ''),
      role: u.role || ''
    }
  })
})

/* ---- Invited users come directly from invitedParticipantsById ---- */
const invitedList = computed(() => {
  const c = chat.value
  if (!c || isDirect.value) return []
  const map = c.invitedParticipantsById || {}
  const ids = Array.isArray(c.invitedUsers) && c.invitedUsers.length ? c.invitedUsers : Object.keys(map)
  const participantIdSet = new Set(c.participantIds || [])
  return ids
    .map(id => map[id] || null)
    .filter(Boolean)
    .filter(u => !participantIdSet.has(u.id)) // avoid duplicates if someone just joined
    .map(u => ({
      id: u.id,
      username: u.username || u.id,
      avatar: normalizeAvatar(u.avatar || ''),
      role: u.role || 'Invited',
    }))
})

const showInvitedSection = computed(() => !isDirect.value && invitedList.value.length > 0)

/* --- Self-labeling & handle prefix --- */
const SELF_LABEL = 'you'
function isSelf(u) {
  const idMatch = viewerId.value && u?.id === viewerId.value
  const nameMatch = viewerUsername.value && u?.username && String(u.username).toLowerCase() === String(viewerUsername.value).toLowerCase()
  return !!(idMatch || nameMatch)
}
function displayUserName(u) {
  return isSelf(u) ? SELF_LABEL : (u?.username || '')
}
function displayHandle(u) {
  const label = displayUserName(u)
  if (label === SELF_LABEL) return label
  return label?.startsWith('@') ? label : `@${label}`
}

function openLeaveConfirm() { if (!isDirect.value) showConfirmLeave.value = true }
function cancelLeave() { showConfirmLeave.value = false }
function confirmLeave() {
  const id = chat.value?.chatId
  console.log('confirmLeave', id)
  if (id) emit('leave-chat', id)
  showConfirmLeave.value = false
}

function openEditor() {
  if (!chat.value) return
  editorKey.value += 1
  editorOpen.value = true
}
function onEditorCancel() { editorOpen.value = false }

async function onEditorSubmit(payload) {

  if (payload?.mode === 'edit') {
    const ws = useChatStore()
    await ws.updateChat(payload)
  }
  editorOpen.value = false
}

function lockScroll() { document.documentElement.style.overflow = 'hidden' }
function unlockScroll() { document.documentElement.style.overflow = '' }
function onKeydown(e) {
  if (e.key === 'Escape') {
    if (showConfirmLeave.value) { cancelLeave(); return }
    emit('close')
  }
}

onMounted(async () => {
  lockScroll()
  document.addEventListener('keydown', onKeydown)
  await nextTick()
  overlayRef.value?.focus()
})

onUnmounted(() => {
  unlockScroll()
  document.removeEventListener('keydown', onKeydown)
})
</script>


<style scoped>
#chatinfo-title { font-size:1.2rem; margin:0; }
.action-btn { background:#232323; border:1px solid #2f2f2f; border-radius:10px; color:#ccc; cursor:pointer; display:inline-flex; gap:0.4rem; padding:6px; transition:background 0.15s ease-in-out, border-color 0.15s ease-in-out; }
.action-btn.danger { background:#281b1b; border-color:#3a2424; color:#ff6b6b; }
.action-btn.danger:hover { background:#341f1f; border-color:#4a2b2b; }
.action-btn:hover { background:#2a2a2a; border-color:#3a3a3a; }
.action-btn:disabled { cursor:not-allowed; opacity:0.55; }
.action-icon { height:18px; width:18px; }
.chatinfo-actions { display:flex; gap:0.5rem; justify-content:center; margin-top:0.25rem; }
.chatinfo-avatar { align-items:center; background:#333; border-radius:50%; display:flex; height:80px; justify-content:center; overflow:hidden; width:80px; }
.chatinfo-avatar img { display:block; height:100%; object-fit:cover; width:100%; }
.chatinfo-backdrop { backdrop-filter:blur(2px); background:rgba(0, 0, 0, 0.6); inset:0; position:fixed; }
.chatinfo-close { background:#1a1a1a; border:none; border-radius:10px; color:#ccc; cursor:pointer; padding:6px; position:absolute; right:10px; top:10px; }
.chatinfo-close:hover { background:#333; }
.chatinfo-close-icon { height:20px; width:20px; }
.chatinfo-content { overflow-y:auto; padding:1rem 1.1rem 1.1rem; }
.chatinfo-created { color:#999; font-size:0.85rem; margin-bottom:0.25rem; }
.chatinfo-header { border-bottom:1px solid #333; display:grid; gap:0.5rem; justify-items:center; padding:1.1rem 1.1rem 0.7rem; }
.chatinfo-initials { color:#e6e6e6; font-size:28px; font-weight:700; line-height:1; }
.chatinfo-modal { background-color:#1a1a1a; border:1px solid #333; border-radius:16px; box-shadow:0 10px 40px rgba(0, 0, 0, 0.6); display:flex; flex-direction:column; max-height:85vh; overflow:hidden; position:relative; width:min(560px, 92vw); }
.chatinfo-overlay { align-items:center; display:flex; inset:0; justify-content:center; min-height:100dvh; position:fixed; z-index:1000; }
.chatinfo-section + .chatinfo-section { margin-top:1rem; }
.chatinfo-section h3 { color:#ddd; font-size:1rem; margin:0 0 0.5rem; }
.confirm-title, .confirm-desc { text-align:center; }
.confirm-actions { display:flex; gap:0.5rem; justify-content:flex-end; margin-top:0.75rem; }
.confirm-backdrop { background:rgba(0, 0, 0, 0.6); inset:0; position:fixed; }
.confirm-btn { background:#232323; border:1px solid #2f2f2f; border-radius:10px; color:#e6e6e6; cursor:pointer; padding:8px 10px; transition:background 0.15s ease-in-out, border-color 0.15s ease-in-out; }
.confirm-btn.danger { background:#3a2424; border-color:#4a2b2b; color:#ff8b8b; }
.confirm-btn.danger:hover { background:#452a2a; border-color:#583333; }
.confirm-btn:hover { background:#2a2a2a; border-color:#3a3a3a; }
.confirm-desc { color:#b3b3b3; font-size:0.95rem; margin:0.25rem 0 0; }
.confirm-modal { background-color:#1a1a1a; border:1px solid #333; border-radius:14px; box-shadow:0 10px 40px rgba(0, 0, 0, 0.6); max-width:420px; padding:1rem 1.1rem 1.1rem; position:relative; width:92vw; }
.confirm-overlay { align-items:center; display:flex; inset:0; justify-content:center; position:fixed; z-index:1010; }
.confirm-title { color:#fff; font-size:1.05rem; margin:0; }
.list-frame { border:1px solid #2a2a2a; border-radius:12px; overflow:hidden; }
li { align-items:stretch; border-bottom:1px solid #2a2a2a; color:#ccc; display:flex; padding:0; }
li:last-child { border-bottom:none; }
ul { list-style:none; margin:0; padding:0; }
.user-arrow { height:18px; margin-left:auto; transition:transform 0.12s ease-in-out; width:18px; }
.user-avatar { align-items:center; background:#2a2a2a; border-radius:50%; color:#d4d4d4; display:flex; flex:none; font-size:0.8rem; font-weight:700; height:28px; justify-content:center; line-height:1; width:28px; }
.user-avatar img { border-radius:50%; display:block; height:100%; object-fit:cover; width:100%; }
.user-link { align-items:center; border-radius:10px; color:#e2e2e2; display:flex; gap:0.5rem; padding:0.65rem 0.85rem; text-decoration:none; transition:background 0.15s ease-in-out, color 0.15s ease-in-out, transform 0.08s ease-in-out; width:100%; }
.user-link:active { transform:translateY(1px); }
.user-link:focus-visible { outline:2px solid #5a5a5a; outline-offset:2px; }
.user-link:hover .user-arrow { transform:scale(1.12); }
.user-link:visited { color:#e2e2e2; }
.user-name { font-weight:500; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
#owner-note { color:#ff8b8b; margin-top:1rem; }
@media (min-width:1400px){ .chatinfo-modal { width:520px; } }
</style>
