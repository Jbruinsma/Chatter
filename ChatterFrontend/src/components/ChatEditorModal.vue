<template>
  <div class="editor-overlay" @keydown.esc="onCancel" tabindex="-1">
    <div class="editor-backdrop" @click="onCancel"></div>

    <div
      class="editor-modal"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      @click.stop
    >
      <h3 :id="titleId" class="editor-title">{{ modeTitle }}</h3>

      <div v-if="inputsLocked" class="permission-banner">
        You don’t have permission to edit this chat.
      </div>

      <div class="editor-content">
        <label class="field-label" id="cover-title">Chat cover</label>
        <div class="cover-row" aria-labelledby="cover-title">
          <label
            class="cover-wrapper"
            :class="{ 'is-disabled': inputsLocked }"
            :aria-busy="coverUploading"
            tabindex="0"
          >
            <input
              ref="coverInputRef"
              class="cover-file-input"
              type="file"
              accept="image/png,image/jpeg"
              :disabled="inputsLocked || coverUploading"
              :aria-disabled="inputsLocked || coverUploading"
              :title="inputsLocked ? 'You need edit permission to change the cover' : (coverUploading ? 'Uploading in progress…' : '')"
              aria-label="Upload chat cover"
              data-role="cover-input"
              @change="onCoverChange"
            />
            <img
              class="cover-img"
              alt="Chat cover"
              :src="coverPreviewUrl"
              :style="{ display: coverPreviewUrl ? '' : 'none' }"
            />
            <div class="cover-fallback" v-show="!coverPreviewUrl" aria-hidden="true">
              {{ coverInitials }}
            </div>
            <div class="cover-overlay">
              <svg
                class="cover-icon"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
                />
              </svg>
              <span class="cover-text">{{ coverUploading ? 'Uploading…' : 'Change' }}</span>
            </div>
          </label>
        </div>

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
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="add-icon"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
              fill="none"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            <span class="add-text">Add</span>
          </button>
        </div>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

        <div class="list-frame">
          <ul class="list">
            <!-- Participants + Invited (read-only) -->
            <li class="list-item" v-for="(id, idx) in listIds" :key="id">
              <span class="user-name" :class="{ 'is-you': id === activeUserId }">
                {{ id === activeUserId ? 'you' : displayName(id) }}
              </span>
              <span v-if="invitedSet.has(id)" class="badge">Invited</span>

              <button
                v-if="canShowEditToggle(id)"
                class="perm-btn"
                :class="userCanEdit(id) ? 'perm-on' : 'perm-off'"
                @click="onToggleEdit(id)"
                type="button"
                :aria-label="userCanEdit(id) ? 'Revoke editing for ' + (id === activeUserId ? 'you' : displayName(id)) : 'Grant editing to ' + (id === activeUserId ? 'you' : displayName(id))"
                :title="userCanEdit(id) ? 'Revoke editing' : 'Grant editing'"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke-width="1.5"
                  stroke="currentColor"
                  class="perm-icon"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13L2.25 21.75l0-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
                  />
                </svg>
              </button>

              <button
                v-if="canShowRemove(id)"
                class="remove-btn"
                @click="openRemoveConfirm(id, idx)"
                type="button"
                :aria-label="'Remove ' + (id === activeUserId ? 'you' : displayName(id))"
                title="Remove user"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="remove-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke-width="1.5"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M22 10.5h-6m-2.25-4.125a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0ZM4 19.235v-.11a6.375 6.375 0 0 1 12.75 0v.109A12.318 12.318 0 0 1 10.374 21c-2.331 0-4.512-.645-6.374-1.766Z"
                  />
                </svg>
              </button>
            </li>

            <li v-if="listIds.length === 0" class="list-empty">No participants yet.</li>
          </ul>
        </div>
      </div>

      <div class="editor-actions">
        <button class="btn primary" type="button" @click="onSubmit" :disabled="!canSubmit">
          {{ primaryText }}
        </button>
        <button class="btn" type="button" @click="onCancel">Cancel</button>
      </div>
    </div>

    <div v-if="confirmOpen" class="confirm-overlay" @keydown.esc="cancelRemove" tabindex="-1">
      <div class="confirm-backdrop" @click="cancelRemove"></div>
      <div
        class="confirm-modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-desc"
        @click.stop
      >
        <h3 id="confirm-title" class="confirm-title">Remove this user?</h3>
        <p id="confirm-desc" class="confirm-desc">
          Are you sure you want to remove
          <template v-if="targetUserId === activeUserId">you</template>
          <template v-else>@{{ displayName(targetUserId) }}</template>
          ?
        </p>
        <div class="confirm-actions">
          <button class="confirm-btn" @click="cancelRemove" type="button">Cancel</button>
          <button class="confirm-btn danger" @click="confirmRemove" type="button">Remove</button>
        </div>
      </div>
    </div>
  </div>
</template>


<script setup>
import { defineProps, defineEmits, ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { verifyUserByUsername } from '@/utils/verification.js'
import { initials } from '@/utils/formatting.js'
import { BASE_API_LINK } from '@/stores/variables.js'

const props = defineProps({
  mode: { type: String, required: true },
  chat: { type: Object, default: null },
  activeUserId: { type: String, required: true },
  activeUsername: { type: String, default: '' },
})

const emit = defineEmits(['submit', 'cancel'])

/* ========= Upload config ========= */
const CHAT_COVER_UPLOAD_URL = `${BASE_API_LINK}/chats/upload_chat_cover`
const CHAT_COVER_FORM_FIELD = 'chat_cover'
const RESPONSE_URL_KEYS = ['chat_cover', 'path']
function toAbsoluteUrl(u) {
  if (!u) return ''
  return /^https?:\/\//i.test(u) ? u : `${BASE_API_LINK}${u.startsWith('/') ? '' : '/'}${u}`
}

/* ========= Derived cover initials ========= */
const chatName = ref('')
const coverInitials = computed(() => {
  const name = (chatName.value || '').trim()
  return name ? initials(name) : 'Cover'
})

const titleId = `editor-title-${Math.random().toString(36).slice(2, 8)}`

/* ========= Original (for change detection) ========= */
const originalName = ref('')
const originalParticipantIds = ref([])
const originalPerms = ref({})

/* ========= Working state ========= */
const participantIds = ref([])
const invitedIds = ref([])
const usersById = ref({})
const permPreview = ref({})

const newParticipant = ref('')
const errorMessage = ref('')
const addInputRef = ref(null)

const confirmOpen = ref(false)
const targetIndex = ref(-1)
const targetUserId = ref('')

/* ---- Cover: preview + staged upload ---- */
const coverInputRef = ref(null)
const coverFile = ref(null)
const coverPreviewUrl = ref('')
const coverUploadedUrl = ref('')
const coverUploading = ref(false)
const COVER_MAX_BYTES = 5 * 1024 * 1024

function revokePreview() {
  const url = coverPreviewUrl.value
  if (url && url.startsWith('blob:')) URL.revokeObjectURL(url)
  coverPreviewUrl.value = ''
}
function setPreview(file) {
  revokePreview()
  coverPreviewUrl.value = URL.createObjectURL(file)
}
function validateCoverFile(file) {
  const okType = ['image/png', 'image/jpeg'].includes(file.type)
  if (!okType) return 'Only PNG or JPG files are allowed.'
  if (file.size > COVER_MAX_BYTES) return 'Image must be 5MB or smaller.'
  return null
}
function onCoverChange(e) {
  if (inputsLocked.value) return
  const f = e.target.files?.[0] || null
  if (!f) return
  const err = validateCoverFile(f)
  if (err) {
    errorMessage.value = err
    e.target.value = ''
    return
  }
  errorMessage.value = ''
  coverFile.value = f
  setPreview(f)
  coverUploadedUrl.value = ''
}
function clearCover() {
  coverFile.value = null
  coverUploadedUrl.value = ''
  revokePreview()
  if (coverInputRef.value) coverInputRef.value.value = ''
}
async function uploadCoverFile(file) {
  const fd = new FormData()
  fd.append(CHAT_COVER_FORM_FIELD, file, file.name)
  const res = await fetch(CHAT_COVER_UPLOAD_URL, { method: 'POST', body: fd })
  if (!res.ok) throw new Error(await res.text())
  const data = await res.json()
  for (const key of RESPONSE_URL_KEYS) {
    if (data && typeof data[key] === 'string' && data[key]) {
      return toAbsoluteUrl(data[key])
    }
  }
  return ''
}
onBeforeUnmount(revokePreview)

/* ========= Changes tracker (internal) ========= */
const changes = ref({
  chatName: '',
  permissions: {},
  removedParticipants: [],
  addedParticipants: [],
  uninvitedIds: [],
})

/* ========= Permissions & locking ========= */
const viewerCanEdit = computed(() => {
  if (props.mode !== 'edit') return true
  const capCanEdit = props.chat?.capabilities?.canEdit
  if (typeof capCanEdit === 'boolean') return capCanEdit
  const ownerId = props.chat?.ownerId ?? props.chat?.owner_id
  if (ownerId && ownerId === props.activeUserId) return true
  const entry = originalPerms.value?.[props.activeUserId]
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
const modeTitle = computed(() => (props.mode === 'create' ? 'Create chat' : 'Edit chat'))
const primaryText = computed(() => (props.mode === 'create' ? 'Create' : 'Save changes'))

/* ========= Derived sets/lists ========= */
const originalSet = computed(() => new Set(originalParticipantIds.value))
const invitedSet = computed(() => new Set(invitedIds.value))
const listIds = computed(() => {
  const p = participantIds.value
  const i = invitedIds.value.filter(id => !p.includes(id))
  return [...p, ...i]
})

/* ========= Helpers ========= */
function displayName(id) {
  const n = usersById.value?.[id]?.username || id
  return id === props.activeUserId ? 'you' : n
}
function isOwner(userId) {
  return !!permPreview.value?.[userId]?.can_delete
}
function canShowEditToggle(userId) {
  if (invitedSet.value.has(userId)) return false
  if (userId === props.activeUserId) return false
  if (isOwner(userId)) return false
  return props.mode === 'create' || viewerCanEdit.value
}
function canShowRemove(userId) {
  if (userId === props.activeUserId) return false
  if (isOwner(userId)) return false
  return props.mode === 'create' ? true : viewerCanEdit.value
}
function userCanEdit(userId) {
  return !!permPreview.value?.[userId]?.can_edit
}

/* ========= Seed (supports multiple shapes) ========= */
async function seedFromProps() {
  revokePreview()
  coverFile.value = null
  coverUploadedUrl.value = ''

  usersById.value = {}
  permPreview.value = {}

  if (props.mode === 'edit' && props.chat) {
    const c = props.chat
    const chatNameRaw = c.chat_name ?? c.chatName ?? ''
    const chatCoverRaw = c.chat_cover ?? c.chatCover ?? ''
    const ids = (c.participant_ids ?? c.participantIds ?? []) || []
    const perms = c.participant_permissions ?? c.participantPermissions ?? {}
    const participantsById = c.participantsById ?? {}
    const invitedRaw = (c.invited_users ?? c.invitedUsers ?? []) || []
    const invitedById = c.invited_participants_by_id ?? c.invitedParticipantsById ?? {}

    originalName.value = chatNameRaw
    originalParticipantIds.value = [...ids]
    originalPerms.value = { ...perms }

    chatName.value = originalName.value
    participantIds.value = [...originalParticipantIds.value]
    invitedIds.value = [...invitedRaw]

    const uMap = {}
    const allIds = new Set([...participantIds.value, ...invitedIds.value])
    for (const id of allIds) {
      const pdata = participantsById[id] || invitedById[id]
      if (pdata && typeof pdata === 'object') {
        uMap[id] = { username: pdata.username || '', avatar: pdata.avatar || '' }
      } else {
        uMap[id] = { username: '', avatar: '' }
      }
    }
    usersById.value = uMap

    const copy = {}
    for (const [k, v] of Object.entries(originalPerms.value)) copy[k] = { ...v }
    permPreview.value = copy

    if (chatCoverRaw) coverPreviewUrl.value = chatCoverRaw
  } else {
    originalName.value = ''
    originalParticipantIds.value = []
    originalPerms.value = {}
    chatName.value = ''
    participantIds.value = []
    invitedIds.value = []
    usersById.value = {}
    permPreview.value = {}
  }

  changes.value = {
    chatName: '',
    permissions: {},
    removedParticipants: [],
    addedParticipants: [],
    uninvitedIds: [],
  }
}
onMounted(() => { seedFromProps() })

/* ========= Focus helper ========= */
function focusAddInput() {
  if (inputsLocked.value) return
  addInputRef.value?.focus()
}

/* ========= Permission toggle ========= */
function onToggleEdit(userId) {
  if (!canShowEditToggle(userId)) return
  if (!ensureCanEdit('change permissions')) return

  const current = !!permPreview.value?.[userId]?.can_edit
  permPreview.value = {
    ...permPreview.value,
    [userId]: { ...(permPreview.value[userId] || {}), can_edit: !current },
  }
  const original = !!originalPerms.value?.[userId]?.can_edit
  const newVal = !current
  if (newVal === original) {
    if (changes.value.permissions[userId]) {
      const next = { ...changes.value.permissions }
      delete next[userId]
      changes.value.permissions = next
    }
  } else {
    changes.value.permissions = {
      ...changes.value.permissions,
      [userId]: { ...(changes.value.permissions[userId] || {}), can_edit: newVal },
    }
  }
}

/* ========= Remove / Uninvite ========= */
function openRemoveConfirm(userId, idx) {
  if (!canShowRemove(userId)) return
  if (!ensureCanEdit('remove participants')) return
  targetUserId.value = userId
  targetIndex.value = idx
  confirmOpen.value = true
}
function cancelRemove() {
  confirmOpen.value = false
  targetIndex.value = -1
  targetUserId.value = ''
}
function confirmRemove() {
  if (!ensureCanEdit('remove participants')) {
    cancelRemove()
    return
  }
  const userId = targetUserId.value

  if (invitedSet.value.has(userId)) {
    const idx = invitedIds.value.indexOf(userId)
    if (idx >= 0) invitedIds.value.splice(idx, 1)
    if (!changes.value.uninvitedIds.includes(userId)) {
      changes.value.uninvitedIds = [...changes.value.uninvitedIds, userId]
    }
    cancelRemove()
    return
  }

  const idx = participantIds.value.indexOf(userId)
  if (idx < 0) {
    cancelRemove()
    return
  }

  participantIds.value.splice(idx, 1)

  const nextPerms = { ...permPreview.value }
  delete nextPerms[userId]
  permPreview.value = nextPerms

  if (originalSet.value.has(userId)) {
    if (!changes.value.removedParticipants.includes(userId)) {
      changes.value.removedParticipants = [...changes.value.removedParticipants, userId]
    }
    if (changes.value.addedParticipants.includes(userId)) {
      changes.value.addedParticipants = changes.value.addedParticipants.filter((u) => u !== userId)
    }
  } else {
    changes.value.addedParticipants = changes.value.addedParticipants.filter((u) => u !== userId)
  }

  cancelRemove()
}

/* ========= Add participant ========= */
async function addParticipant() {
  if (!ensureCanEdit('add participants')) return

  const uname = (newParticipant.value || '').trim()
  if (!uname) return

  const userInfo = await verifyUserByUsername(uname)
  const userExists = !!(userInfo && userInfo.exists && userInfo.id)
  if (!userExists) {
    errorMessage.value = `User @${uname} does not exist.`
    return
  }
  const userId = userInfo.id

  if (userId === props.activeUserId) {
    errorMessage.value = 'You cannot add yourself to a chat.'
    return
  }
  if (participantIds.value.includes(userId) || invitedIds.value.includes(userId)) {
    errorMessage.value = `@${usersById.value[userId]?.username || uname} is already in this chat.`
    return
  }

  participantIds.value.push(userId)

  usersById.value = {
    ...usersById.value,
    [userId]: {
      username: uname,
      avatar: usersById.value[userId]?.avatar || '',
    },
  }

  permPreview.value = {
    ...permPreview.value,
    [userId]: {
      ...(permPreview.value[userId] || {}),
      can_edit: false,
      can_delete: false,
    },
  }

  errorMessage.value = ''
  newParticipant.value = ''

  if (originalSet.value.has(userId)) {
    if (changes.value.removedParticipants.includes(userId)) {
      changes.value.removedParticipants = changes.value.removedParticipants.filter((x) => x !== userId)
    }
  } else {
    if (!changes.value.addedParticipants.includes(userId)) {
      changes.value.addedParticipants = [...changes.value.addedParticipants, userId]
    }
    if (props.mode === 'edit') {
      changes.value.permissions = {
        ...changes.value.permissions,
        [userId]: { can_edit: false, can_delete: false },
      }
    }
  }
}

/* ========= Submit logic ========= */
const hasNameChange = computed(() => chatName.value.trim() !== originalName.value.trim())
const hasPermChanges = computed(() => Object.keys(changes.value.permissions).length > 0)
const hasAdds = computed(() => changes.value.addedParticipants.length > 0)
const hasRemoves = computed(() => changes.value.removedParticipants.length > 0)
const hasUninvites = computed(() => changes.value.uninvitedIds.length > 0)
const hasCoverNew = computed(() => !!coverFile.value)

const hasChanges = computed(() => {
  return props.mode === 'create'
    ? chatName.value.trim().length > 0 && participantIds.value.length > 0
    : hasNameChange.value || hasPermChanges.value || hasAdds.value || hasRemoves.value || hasUninvites.value || hasCoverNew.value
})

const canSubmit = computed(() => {
  if (props.mode === 'create') {
    return chatName.value.trim().length > 0 && participantIds.value.length > 0 && !coverUploading.value
  }
  return viewerCanEdit.value && hasChanges.value && !coverUploading.value
})

async function onSubmit() {
  if (!canSubmit.value) return
  if (!ensureCanEdit('save changes')) return

  if (props.mode === 'create') {
    errorMessage.value = ''

    const uniqueIds = new Set([props.activeUserId, ...participantIds.value])
    const participantIdsOut = [...uniqueIds]

    const permissionsById = {}
    for (const id of participantIds.value) {
      const p = permPreview.value[id] || {}
      permissionsById[id] = { can_edit: !!p.can_edit }
    }
    permissionsById[props.activeUserId] = { can_edit: true }

    const isDirect = participantIdsOut.length === 2
    if (isDirect) chatName.value = ''

    if (coverFile.value) {
      try {
        coverUploading.value = true
        const url = await uploadCoverFile(coverFile.value)
        coverUploadedUrl.value = url || ''
      } catch (e) {
        errorMessage.value = 'Failed to upload chat cover.'
        coverUploading.value = false
        return
      } finally {
        coverUploading.value = false
      }
    }

    const payload = {
      operation: 'create_chat',
      data: {
        chat_name: chatName.value.trim(),
        chat_cover: coverUploadedUrl.value || '',
        owner_id: props.activeUserId,
        participant_ids: participantIdsOut,
        participant_permissions: permissionsById,
        chat_type: isDirect ? 'direct' : 'group',
      },
    }

    emit('submit', payload)
    return
  }

  // EDIT — map to snake_case for backend
  const changesOut = {}

  if (hasNameChange.value) changesOut.chat_name = chatName.value.trim()

  let permissions = { ...changes.value.permissions }
  if (hasAdds.value) {
    for (const id of changes.value.addedParticipants) {
      if (!permissions[id]) {
        const p = permPreview.value[id] || {}
        permissions[id] = { can_edit: !!p.can_edit, can_delete: !!p.can_delete }
      }
    }
  }
  if (Object.keys(permissions).length > 0) {
    changesOut.participant_permissions = permissions
  }

  if (hasAdds.value) changesOut.added_participants = [...changes.value.addedParticipants]
  if (hasRemoves.value) changesOut.removed_participants = [...changes.value.removedParticipants]
  if (hasUninvites.value) changesOut.uninvited_ids = [...changes.value.uninvitedIds]

  if (coverFile.value) {
    try {
      coverUploading.value = true
      const url = await uploadCoverFile(coverFile.value)
      coverUploadedUrl.value = url || ''
    } catch (e) {
      errorMessage.value = 'Failed to upload chat cover.'
      coverUploading.value = false
      return
    } finally {
      coverUploading.value = false
    }
    if (coverUploadedUrl.value) changesOut.chat_cover = coverUploadedUrl.value
  }

  emit('submit', {
    mode: 'edit',
    chatId: props.chat?.chat_id ?? props.chat?.chatId ?? null,
    changes: changesOut,
  })
}

function onCancel() {
  emit('cancel')
}

/* Expose for template refs */
defineExpose({
  inputsLocked,
  viewerCanEdit,
  focusAddInput,
  onToggleEdit,
  openRemoveConfirm,
  addParticipant,
  onCoverChange,
  clearCover,
  onSubmit,
  onCancel,
  userCanEdit,
  displayName,
  usersById,
  participantIds,
  invitedIds,
  invitedSet,
  listIds,
})
</script>



<style scoped>
.add-btn { align-items:center; background:#232323; border:1px solid #2f2f2f; border-radius:10px; color:#ccc; cursor:pointer; display:inline-flex; gap:0.4rem; padding:0.55rem 0.7rem; transition:background 0.15s ease-in-out, border-color 0.15s ease-in-out; }
.add-btn:hover { background:#2a2a2a; border-color:#3a3a3a; }
.add-icon { height:18px; width:18px; }
.add-row { align-items:center; display:grid; gap:0.6rem; grid-template-columns:1fr auto; }
.add-text { font-size:0.92rem; }
.btn { background:#232323; border:1px solid #2f2f2f; border-radius:10px; color:#e6e6e6; cursor:pointer; padding:0.6rem 0.9rem; transition:background 0.15s ease-in-out, border-color 0.15s ease-in-out; }
.btn:hover { background:#2a2a2a; border-color:#3a3a3a; }
.btn.primary { background:#2d3b2d; border-color:#364936; color:#bfe4bf; }
.btn.primary:disabled { background:#242424; border-color:#2c2c2c; color:#777; cursor:not-allowed; }
.cover-file-input { cursor:pointer; height:100%; inset:0; opacity:0; position:absolute; width:100%; }
.cover-fallback { color:#bbb; font:700 0.95rem 'Roboto Mono', monospace; }
.cover-icon { height:18px; stroke:currentColor; width:18px; }
.cover-img { border-radius:50%; height:100%; object-fit:cover; width:100%; }
.cover-overlay { align-items:center; background-color:rgba(0, 0, 0, 0.5); border-radius:50%; color:#eaeaea; display:flex; inset:0; justify-content:center; opacity:0; position:absolute; transition:opacity 0.15s ease; }
.cover-row { align-items:center; display:flex; justify-content:center; }
.cover-text { font:600 0.85rem 'Roboto Mono', monospace; margin-left:0.4rem; }
.cover-wrapper { background:#1a1a1a; border:1px solid #333; border-radius:50%; cursor:pointer; display:grid; height:84px; overflow:hidden; place-items:center; position:relative; width:84px; }
.cover-wrapper.is-disabled { cursor:not-allowed; opacity:0.6; }
.cover-wrapper:hover .cover-overlay, .cover-wrapper:focus-within .cover-overlay { opacity:1; }
.confirm-actions { display:flex; gap:0.5rem; justify-content:flex-end; margin-top:0.75rem; }
.confirm-backdrop { background:rgba(0, 0, 0, 0.6); inset:0; position:fixed; }
.confirm-btn { background:#232323; border:1px solid #2f2f2f; border-radius:10px; color:#e6e6e6; cursor:pointer; padding:8px 10px; transition:background 0.15s ease-in-out, border-color 0.15s ease-in-out; }
.confirm-btn.danger { background:#3a2424; border-color:#4a2b2b; color:#ff8b8b; }
.confirm-btn.danger:hover { background:#452a2a; border-color:#583333; }
.confirm-btn:hover { background:#2a2a2a; border-color:#3a3a3a; }
.confirm-desc { color:#b3b3b3; font-size:0.95rem; margin:0.25rem 0 0; text-align:center; }
.confirm-modal { background:#1a1a1a; border:1px solid #333; border-radius:14px; box-shadow:0 10px 40px rgba(0, 0, 0, 0.6); max-width:420px; padding:1rem 1.1rem 1.1rem; position:relative; width:92vw; }
.confirm-overlay { align-items:center; display:flex; inset:0; justify-content:center; position:fixed; z-index:1200; }
.confirm-title { color:#fff; font-size:1.05rem; margin:0; text-align:center; }
.editor-actions { display:flex; gap:0.5rem; justify-content:flex-end; margin-top:0.9rem; }
.editor-backdrop { background:rgba(0, 0, 0, 0.6); inset:0; position:fixed; }
.editor-content { display:grid; gap:0.85rem; padding:0.2rem 0.5rem 0; }
.editor-modal { background:#1a1a1a; border:1px solid #333; border-radius:16px; box-shadow:0 10px 40px rgba(0, 0, 0, 0.6); max-height:85vh; overflow:hidden auto; padding:1rem 1.1rem 1.1rem; position:relative; width:min(560px, 92vw); }
.editor-overlay { align-items:center; display:flex; inset:0; justify-content:center; position:fixed; z-index:1100; }
.editor-title { color:#fff; font-size:1.15rem; margin:0 0 0.4rem; }
.error-message { color:#ff8b8b; font-size:0.95rem; margin:0.25rem 0 0; text-align:center; }
.field-label { color:#ddd; font-size:0.95rem; }
.list { list-style:none; margin:0; padding:0; }
.list-empty { color:#999; padding:0.7rem; text-align:center; }
.list-frame { border:1px solid #2a2a2a; border-radius:12px; overflow:hidden; }
.list-item { align-items:center; border-bottom:1px solid #2a2a2a; color:#ccc; display:flex; justify-content:space-between; padding:0.6rem 0.8rem; }
.list-item:last-child { border-bottom:none; }
.list-item:hover .perm-btn { opacity:1; pointer-events:auto; }
.list-item:hover .remove-btn { opacity:1; pointer-events:auto; }
.perm-btn { background:none; border:none; border-radius:8px; color:#ccc; cursor:pointer; margin-right:6px; opacity:0; padding:4px; pointer-events:none; transition:opacity 0.15s ease-in-out; }
.perm-btn:hover { background:rgba(204, 204, 204, 0.08); }
.perm-btn.perm-off { color:#ff4c4c; }
.perm-btn.perm-on { color:#4ade80; }
.perm-icon { height:16px; width:16px; }
.permission-banner { color:#dc2626; font-size:0.9rem; text-align:center; }
.remove-btn { background:none; border:none; border-radius:8px; color:#ff4c4c; cursor:pointer; opacity:0; padding:4px; pointer-events:none; transition:opacity 0.15s ease-in-out; }
.remove-btn:hover { background:rgba(255, 76, 76, 0.08); }
.remove-icon { height:16px; width:16px; }
.text-input { background:#141414; border:1px solid #2f2f2f; border-radius:10px; box-shadow:inset 0 0 0 1px rgba(255, 255, 255, 0.02); box-sizing:border-box; color:#e6e6e6; outline:none; padding:0.6rem 0.7rem; width:100%; }
.text-input:focus { border-color:#3a3a3a; box-shadow:inset 0 0 0 1px rgba(255, 255, 255, 0.06); }
.user-name { max-width:70%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.user-name::before { color:#888; content:'@'; margin-right:0; }
.user-name.is-you::before { content:''; }
@media (min-width:1400px){ .editor-modal { width:520px; } }
.list-item .perm-btn { margin-left:auto; }
.list-item .remove-btn { margin-left:0; }
.badge { background:rgba(255, 255, 255, 0.06); border:1px solid #3a3a3a; border-radius:999px; color:#bdbdbd; font-size:0.72rem; font-weight:600; letter-spacing:0.2px; line-height:1; margin-left:0.5rem; padding:0.16rem 0.45rem; vertical-align:middle; white-space:nowrap; }
.list-item:hover .badge { background:rgba(255, 255, 255, 0.08); border-color:#4a4a4a; }
</style>

