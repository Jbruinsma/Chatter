<template>
  <div class="editor-overlay" @keydown.esc="onCancel" tabindex="-1">
    <div class="editor-backdrop" @click="onCancel"></div>

    <div class="editor-modal" role="dialog" aria-modal="true" :aria-labelledby="titleId" @click.stop>
      <h3 :id="titleId" class="editor-title">{{ modeTitle }}</h3>

      <div v-if="inputsLocked" class="permission-banner">
        You don’t have permission to edit this chat.
      </div>

      <div class="editor-content">
        <label class="field-label">Chat name</label>
        <input
          v-model.trim="chatName"
          class="text-input"
          type="text"
          placeholder="Enter a chat name"
          :readonly="inputsLocked"
          :aria-readonly="inputsLocked"
          :title="inputsLocked ? 'You need edit permission to rename this chat' : ''"
          @keydown.enter.prevent="focusAddInput"
        />

        <label class="field-label">Add participant by username</label>
        <div class="add-row">
          <input
            ref="addInputRef"
            v-model.trim="newParticipant"
            class="text-input"
            type="text"
            placeholder="Type a username and press Enter"
            :disabled="inputsLocked"
            :aria-disabled="inputsLocked"
            :title="inputsLocked ? 'You need edit permission to add participants' : ''"
            @keyup.enter="addParticipant"
          />
          <button
            class="add-btn"
            type="button"
            @click="addParticipant"
            :disabled="inputsLocked"
            :aria-disabled="inputsLocked"
            :title="inputsLocked ? 'You need edit permission to add participants' : ''"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="add-icon" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" fill="none">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15"/>
            </svg>
            <span class="add-text">Add</span>
          </button>
        </div>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

        <div class="list-frame">
          <ul class="list">
            <li class="list-item" v-for="(user, idx) in participants" :key="user">
              <span class="user-name">{{ user }}</span>

              <button
                v-if="canShowEditToggle(user)"
                class="perm-btn"
                :class="userCanEdit(user) ? 'perm-on' : 'perm-off'"
                @click="onToggleEdit(user)"
                type="button"
                :aria-label="userCanEdit(user) ? 'Revoke editing for ' + user : 'Grant editing to ' + user"
                :title="userCanEdit(user) ? 'Revoke editing' : 'Grant editing'"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
                     stroke-width="1.5" stroke="currentColor" class="perm-icon">
                  <path stroke-linecap="round" stroke-linejoin="round"
                        d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13L2.25 21.75l0-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125" />
                </svg>
              </button>

              <button
                v-if="canShowRemove(user)"
                class="remove-btn"
                @click="openRemoveConfirm(user, idx)"
                type="button"
                aria-label="Remove participant"
                title="Remove user"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="remove-icon" fill="none" viewBox="0 0 24 24"
                     stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round"
                        d="M22 10.5h-6m-2.25-4.125a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0ZM4 19.235v-.11a6.375 6.375 0 0 1 12.75 0v.109A12.318 12.318 0 0 1 10.374 21c-2.331 0-4.512-.645-6.374-1.766Z" />
                </svg>
              </button>
            </li>

            <li v-if="participants.length === 0" class="list-empty">No participants yet.</li>
          </ul>
        </div>
      </div>

      <div class="editor-actions">
        <button class="btn primary" type="button" @click="onSubmit" :disabled="!canSubmit">{{ primaryText }}</button>
        <button class="btn" type="button" @click="onCancel">Cancel</button>
      </div>
    </div>

    <div v-if="confirmOpen" class="confirm-overlay" @keydown.esc="cancelRemove" tabindex="-1">
      <div class="confirm-backdrop" @click="cancelRemove"></div>
      <div class="confirm-modal" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-desc" @click.stop>
        <h3 id="confirm-title" class="confirm-title">Remove this user?</h3>
        <p id="confirm-desc" class="confirm-desc">Are you sure you want to remove @{{ targetUsername }}?</p>
        <div class="confirm-actions">
          <button class="confirm-btn" @click="cancelRemove" type="button">Cancel</button>
          <button class="confirm-btn danger" @click="confirmRemove" type="button">Remove</button>
        </div>
      </div>
    </div>
  </div>
</template>


<script setup>
import { defineProps, defineEmits, ref, computed, onMounted } from 'vue'
import {verifyUserExistence} from "@/utils/verification.js";

const props = defineProps({
  mode: { type: String, required: true },
  chat: { type: Object, default: null },
  activeUsername: { type: String, required: true },
})

const emit = defineEmits(['submit', 'cancel'])

const titleId = `editor-title-${Math.random().toString(36).slice(2, 8)}`

const originalName = ref('')
const originalParticipants = ref([])
const originalPerms = ref({})

const chatName = ref('')
const participants = ref([])
const permPreview = ref({})

const newParticipant = ref('')
const errorMessage = ref('')
const addInputRef = ref(null)

const confirmOpen = ref(false)
const targetIndex = ref(-1)
const targetUsername = ref('')

const changes = ref({
  chatName: '',
  permissions: {},
  removedParticipants: [],
  addedParticipants: [],
})

const viewerCanEdit = computed(() => {
  if (props.mode !== 'edit') return true
  const user = props.activeUsername
  const entry = originalPerms.value?.[user]
  return !!entry?.can_edit
})

function ensureCanEdit(actionLabel = 'perform this action') {
  if (props.mode === 'edit' && !viewerCanEdit.value) {
    errorMessage.value = `You don't have permission to ${actionLabel}.`
    return false
  }
  return true
}

const inputsLocked = computed(() => props.mode === 'edit' && !viewerCanEdit.value)

const modeTitle = computed(() => props.mode === 'create' ? 'Create chat' : 'Edit chat')
const primaryText = computed(() => props.mode === 'create' ? 'Create' : 'Save changes')

const originalSet = computed(() => new Set(originalParticipants.value))

function seedFromProps() {
  if (props.mode === 'edit' && props.chat) {
    originalName.value = props.chat.chat_name || ''
    originalParticipants.value = Array.isArray(props.chat.participants) ? [...props.chat.participants] : []
    originalPerms.value = { ...(props.chat.participant_permissions || {}) }

    chatName.value = originalName.value
    participants.value = [...originalParticipants.value]
    const copy = {}
    for (const [k, v] of Object.entries(originalPerms.value)) copy[k] = { ...v }
    permPreview.value = copy
  } else {
    originalName.value = ''
    originalParticipants.value = []
    originalPerms.value = {}
    chatName.value = ''
    participants.value = []
    permPreview.value = {}
  }
  changes.value = { chatName: '', permissions: {}, removedParticipants: [], addedParticipants: [] }
}

onMounted(seedFromProps)

function focusAddInput() {
  if (inputsLocked.value) return
  addInputRef.value?.focus()
}

const isOwner = (username) => !!permPreview.value?.[username]?.can_delete

function canShowEditToggle(username) {
  if (username === props.activeUsername) return false
  if (isOwner(username)) return false
  return props.mode === 'create' || viewerCanEdit.value
}

function canShowRemove(username) {
  if (username === props.activeUsername) return false
  if (isOwner(username)) return false
  return props.mode === 'create' ? true : viewerCanEdit.value
}

function userCanEdit(username) {
  return !!permPreview.value?.[username]?.can_edit
}

function onToggleEdit(username) {
  if (!canShowEditToggle(username)) return
  if (!ensureCanEdit('change permissions')) return

  const current = !!permPreview.value?.[username]?.can_edit
  permPreview.value = {
    ...permPreview.value,
    [username]: { ...(permPreview.value[username] || {}), can_edit: !current }
  }
  const original = !!originalPerms.value?.[username]?.can_edit
  const newVal = !current
  if (newVal === original) {
    if (changes.value.permissions[username]) {
      const next = { ...changes.value.permissions }
      delete next[username]
      changes.value.permissions = next
    }
  } else {
    changes.value.permissions = {
      ...changes.value.permissions,
      [username]: { ...(changes.value.permissions[username] || {}), can_edit: newVal }
    }
  }
}

function openRemoveConfirm(username, idx) {
  if (!canShowRemove(username)) return
  if (!ensureCanEdit('remove participants')) return
  targetUsername.value = username
  targetIndex.value = idx
  confirmOpen.value = true
}

function cancelRemove() {
  confirmOpen.value = false
  targetIndex.value = -1
  targetUsername.value = ''
}

function confirmRemove() {
  if (!ensureCanEdit('remove participants')) { cancelRemove(); return }

  const idx = targetIndex.value
  const user = targetUsername.value
  if (idx < 0 || idx >= participants.value.length) { cancelRemove(); return }

  participants.value.splice(idx, 1)

  const nextPerms = { ...permPreview.value }
  delete nextPerms[user]
  permPreview.value = nextPerms

  if (originalSet.value.has(user)) {
    if (!changes.value.removedParticipants.includes(user)) {
      changes.value.removedParticipants = [...changes.value.removedParticipants, user]
    }
    if (changes.value.addedParticipants.includes(user)) {
      changes.value.addedParticipants =
        changes.value.addedParticipants.filter(u => u !== user)
    }
  } else {
    changes.value.addedParticipants =
      changes.value.addedParticipants.filter(u => u !== user)
  }

  cancelRemove()
}

async function addParticipant() {
  if (!ensureCanEdit('add participants')) return

  const newParticipantUsername = (newParticipant.value || '').trim()
  if (!newParticipantUsername) return
  if (newParticipantUsername === props.activeUsername) {
    errorMessage.value = 'You cannot add yourself to a chat.'
    return
  }
  if (participants.value.includes(newParticipantUsername)) {
    errorMessage.value = `@${newParticipantUsername} is already in this chat.`
    return
  }

  const userInfo = await verifyUserExistence(newParticipantUsername)
  const userExists = userInfo.exists
  if (!userExists) {
    errorMessage.value = `User @${newParticipantUsername} does not exist.`
    return
  }

  const userData = userInfo.data
  const publicStatus = userData.public_status
  const followers = userData.followers

  if (!publicStatus && !followers.includes(props.activeUsername)) {
    errorMessage.value = `Cannot add @${newParticipantUsername} due to account privacy settings.`
    return
  }

  participants.value.push(newParticipantUsername)

  permPreview.value = {
    ...permPreview.value,
    [newParticipantUsername]: {
      ...(permPreview.value[newParticipantUsername] || {}),
      username: newParticipantUsername,
      can_edit: false,
      can_delete: false
    }
  }

  errorMessage.value = ''
  newParticipant.value = ''

  if (originalSet.value.has(newParticipantUsername)) {
    if (changes.value.removedParticipants.includes(newParticipantUsername)) {
      changes.value.removedParticipants =
        changes.value.removedParticipants.filter(x => x !== newParticipantUsername)
    }
  } else {
    if (!changes.value.addedParticipants.includes(newParticipantUsername)) {
      changes.value.addedParticipants = [
        ...changes.value.addedParticipants,
        newParticipantUsername
      ]
    }
    if (props.mode === 'edit') {
      changes.value.permissions = {
        ...changes.value.permissions,
        [newParticipantUsername]: { can_edit: false, can_delete: false }
      }
    }
  }
}

const hasNameChange = computed(() => chatName.value.trim() !== originalName.value.trim())
const hasPermChanges = computed(() => Object.keys(changes.value.permissions).length > 0)
const hasAdds = computed(() => changes.value.addedParticipants.length > 0)
const hasRemoves = computed(() => changes.value.removedParticipants.length > 0)
const hasChanges = computed(() => {
  return props.mode === 'create'
    ? chatName.value.trim().length > 0 && participants.value.length > 0
    : hasNameChange.value || hasPermChanges.value || hasAdds.value || hasRemoves.value
})

const canSubmit = computed(() => {
  if (props.mode === 'create') {
    return chatName.value.trim().length > 0 && participants.value.length > 0
  }
  return viewerCanEdit.value && hasChanges.value
})

function onSubmit() {
  if (!canSubmit.value) return
  if (!ensureCanEdit('save changes')) return

  if (props.mode === 'create') {
    const permissions = {}
    for (const u of participants.value) {
      const p = permPreview.value[u] || {}
      permissions[u] = {
        username: p.username || u,
        can_edit: !!p.can_edit,
        can_delete: !!p.can_delete,
      }
    }

    emit('submit', {
      mode: 'create',
      data: {
        chatName: chatName.value.trim(),
        participants: [...participants.value],
        permissions,
      },
    })
    return
  }

  const payload = {}

  if (hasNameChange.value) payload.chatName = chatName.value.trim()

  let permissions = { ...changes.value.permissions }

  if (hasAdds.value) {
    for (const u of changes.value.addedParticipants) {
      if (!permissions[u]) {
        const p = permPreview.value[u] || {}
        permissions[u] = {
          can_edit: !!p.can_edit,
          can_delete: !!p.can_delete,
        }
      }
    }
  }

  if (Object.keys(permissions).length > 0) {
    payload.permissions = permissions
  }

  if (hasAdds.value) payload.addedParticipants = [...changes.value.addedParticipants]
  if (hasRemoves.value) payload.removedParticipants = [...changes.value.removedParticipants]

  emit('submit', {
    mode: 'edit',
    chatId: props.chat?.chat_id || null,
    changes: payload,
  })
}

function onCancel() {
  emit('cancel')
}

defineExpose({
  inputsLocked,
  viewerCanEdit,
  focusAddInput,
  onToggleEdit,
  openRemoveConfirm,
  addParticipant,
  onSubmit,
  onCancel,
  userCanEdit,
})
</script>



<style scoped>
.add-btn { align-items:center; background:#232323; border:1px solid #2f2f2f; border-radius:10px; color:#ccc; cursor:pointer; display:inline-flex; gap:0.4rem; padding:0.55rem 0.7rem; transition:background .15s ease-in-out, border-color .15s ease-in-out; }
.add-btn:hover { background:#2a2a2a; border-color:#3a3a3a; }
.add-icon { height:18px; width:18px; }
.add-row { align-items:center; display:grid; gap:0.6rem; grid-template-columns:1fr auto; }
.add-text { font-size:0.92rem; }
.btn { background:#232323; border:1px solid #2f2f2f; border-radius:10px; color:#e6e6e6; cursor:pointer; padding:0.6rem 0.9rem; transition:background .15s ease-in-out, border-color .15s ease-in-out; }
.btn:hover { background:#2a2a2a; border-color:#3a3a3a; }
.btn.primary { background:#2d3b2d; border-color:#364936; color:#bfe4bf; }
.btn.primary:disabled { background:#242424; border-color:#2c2c2c; color:#777; cursor:not-allowed; }
.confirm-actions { display:flex; gap:0.5rem; justify-content:flex-end; margin-top:0.75rem; }
.confirm-backdrop { background:rgba(0,0,0,0.6); inset:0; position:fixed; }
.confirm-btn { background:#232323; border:1px solid #2f2f2f; border-radius:10px; color:#e6e6e6; cursor:pointer; padding:8px 10px; transition:background .15s ease-in-out, border-color .15s ease-in-out; }
.confirm-btn.danger { background:#3a2424; border-color:#4a2b2b; color:#ff8b8b; }
.confirm-btn.danger:hover { background:#452a2a; border-color:#583333; }
.confirm-btn:hover { background:#2a2a2a; border-color:#3a3a3a; }
.confirm-desc { text-align: center; color:#b3b3b3; font-size:0.95rem; margin:0.25rem 0 0; }
.confirm-modal { background:#1a1a1a; border:1px solid #333; border-radius:14px; box-shadow:0 10px 40px rgba(0,0,0,0.6); max-width:420px; padding:1rem 1.1rem 1.1rem; position:relative; width:92vw; }
.confirm-overlay { align-items:center; display:flex; inset:0; justify-content:center; position:fixed; z-index:1200; }
.confirm-title { text-align: center; color:#fff; font-size:1.05rem; margin:0; }
.editor-actions { display:flex; gap:0.5rem; justify-content:flex-end; margin-top:0.9rem; }
.editor-backdrop { background:rgba(0,0,0,0.6); inset:0; position:fixed; }
.editor-content { display:grid; gap:0.85rem; padding:0.2rem 0.5rem 0; }
.editor-modal { background:#1a1a1a; border:1px solid #333; border-radius:16px; box-shadow:0 10px 40px rgba(0,0,0,0.6); max-height:85vh; overflow:hidden auto; padding:1rem 1.1rem 1.1rem; position:relative; width:min(560px,92vw); }
.editor-overlay { align-items:center; display:flex; inset:0; justify-content:center; position:fixed; z-index:1100; }
.editor-title { color:#fff; font-size:1.15rem; margin:0 0 0.4rem; }
.error-message { text-align: center; color:#ff8b8b; font-size:0.95rem; margin:0.25rem 0 0; }
.field-label { color:#ddd; font-size:0.95rem; }
.list { list-style:none; margin:0; padding:0; }
.list-empty { color:#999; padding:0.7rem; text-align:center; }
.list-frame { border:1px solid #2a2a2a; border-radius:12px; overflow:hidden; }
.list-item { align-items:center; border-bottom:1px solid #2a2a2a; color:#ccc; display:flex; justify-content:space-between; padding:0.6rem 0.8rem; }
.list-item:last-child { border-bottom:none; }
.list-item:hover .remove-btn { opacity:1; pointer-events:auto; }
.remove-btn { background:none; border:none; border-radius:8px; color:#ff4c4c; cursor:pointer; opacity:0; padding:4px; pointer-events:none; transition:opacity .15s ease-in-out; }
.remove-btn:hover { background:rgba(255,76,76,0.08); }
.remove-icon { height:16px; width:16px; }
.text-input { background:#141414; border:1px solid #2f2f2f; border-radius:10px; box-shadow:inset 0 0 0 1px rgba(255,255,255,0.02); box-sizing:border-box; color:#e6e6e6; outline:none; padding:0.6rem 0.7rem; width:100%; }
.text-input:focus { border-color:#3a3a3a; box-shadow:inset 0 0 0 1px rgba(255,255,255,0.06); }
.user-name { max-width:70%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.user-name::before { color:#888; content:"@"; margin-right:6px; }
@media (min-width:1400px) { .editor-modal { width:520px; } }
.perm-btn { background:none; border:none; border-radius:8px; color:#ccc; cursor:pointer; opacity:0; padding:4px; pointer-events:none; transition:opacity .15s ease-in-out; margin-right:6px; }
.perm-btn:hover { background:rgba(204,204,204,0.08); }
.perm-icon { height:16px; width:16px; }
.list-item:hover .perm-btn { opacity:1; pointer-events:auto; }
.permission-banner{color:#dc2626;font-size:.9rem;text-align:center}
.perm-btn.perm-on { color:#4ade80; }  /* green when can_edit === true */
.perm-btn.perm-off { color:#ff4c4c; } /* red when can_edit === false */
</style>
