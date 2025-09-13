<template>
  <!-- Parent should mount/unmount this with v-if -->
  <div
    class="fr-modal-overlay"
    @click.self="onClose"
    role="dialog"
    aria-modal="true"
    aria-labelledby="fr-title"
  >
    <div class="fr-modal">
      <!-- Header -->
      <header class="fr-header">
        <h3 id="fr-title" class="fr-title">Follow Requests</h3>
        <div class="hdr-actions">
          <button class="icon-btn" @click="refresh" :disabled="loading" aria-label="Refresh">
            <!-- refresh icon (exact as requested) -->
            <svg
              class="icon"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
              />
            </svg>
          </button>
          <button class="icon-btn close-btn" @click="onClose" aria-label="Close">
            <!-- close icon (exact as requested) -->
            <svg
              class="icon"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </header>

      <!-- Banners -->
      <div v-if="errorMessage" class="fr-banner error" role="alert">{{ errorMessage }}</div>
      <div v-if="infoMessage" class="fr-banner info" role="status">{{ infoMessage }}</div>

      <!-- Body -->
      <section class="fr-body">
        <div v-if="loading" class="fr-empty" role="status">Loading…</div>

        <template v-else>
          <!-- Not logged in -->
          <div v-if="!ownerUuid" class="fr-empty" role="status">
            You must be logged in to manage follow requests.
          </div>

          <!-- Public account -->
          <div v-else-if="isPublic" class="fr-empty" role="status">
            No follow requests — you can toggle public status in Settings.
          </div>

          <!-- Private account: requests -->
          <template v-else>
            <div v-if="requestsLocal.length === 0" class="fr-empty" role="status">
              No follow requests right now.
            </div>

            <!-- Uses array of objects: { id, username, profilePicture, publicStatus } -->
            <ul v-else class="fr-list" role="list">
              <li v-for="req in requestsLocal" :key="req.id || req.username" class="fr-item">
                <div class="fr-left">
                  <!-- Avatar with profile picture fallback -->
                  <div class="avatar" :aria-label="`Avatar for ${req.username}`">
                    <img v-if="req.profilePicture" :src="req.profilePicture" alt="" />
                    <template v-else>{{ initial(req.username) }}</template>
                  </div>

                  <div class="req-meta">
                    <div class="uname">@{{ req.username }}</div>
                  </div>
                </div>

                <div class="fr-actions" role="group" :aria-label="`Actions for ${req.username}`">
                  <!-- Accept -->
                  <button
                    class="icon-btn accept"
                    :disabled="isBusyId(req.id)"
                    @click="accept(req)"
                    :title="isBusyId(req.id) ? 'Accepting…' : 'Accept request'"
                    aria-label="Accept request"
                  >
                    <svg
                      class="icon"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke-width="1.5"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="m4.5 12.75 6 6 9-13.5"
                      />
                    </svg>
                  </button>

                  <!-- Deny -->
                  <button
                    class="icon-btn deny"
                    :disabled="isBusyId(req.id)"
                    @click="deny(req)"
                    :title="isBusyId(req.id) ? 'Denying…' : 'Deny request'"
                    aria-label="Deny request"
                  >
                    <svg
                      class="icon"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke-width="1.5"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M6 18 18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              </li>
            </ul>
          </template>
        </template>
      </section>

      <footer class="fr-footer">
        <span class="hint"
          >Accepting requests adds them to your followers; denying removes the request.</span
        >
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/userStore.js'
import { BASE_API_LINK } from '@/stores/variables.js'
import { deleteToAPI, fetchAPI, postToAPI } from '@/utils/api.js'
import { useChatStore } from '@/stores/websocket.js'

/* ---------- props (optional override) ---------- */
const props = defineProps({
  /** (Optional) Owner's UUID override. If omitted, uses userStore.uuid */
  userId: { type: String, default: '' },
})

/* ---------- stores & identity ---------- */
const userStore = useUserStore()
const wsStore = useChatStore()
const ownerUuid = computed(() => props.userId || userStore?.uuid || '')
const ownerUsername = computed(() => userStore?.username || '') // for fallback payload if needed

/* ---------- state ---------- */
const loading = ref(true)
const errorMessage = ref('')
const infoMessage = ref('')

/** This endpoint now returns only the array of requests; owner's public status is not provided here */
const isPublic = ref(false)
const requestsLocal = ref([]) // [{id, username, profilePicture, publicStatus}]
const followersLocal = ref([]) // optional/local only

/* Track busy by requester UUID */
const busySet = ref(new Set())

/* ---------- utils ---------- */
const isBusyId = (id) => busySet.value.has(id)
const initial = (name) => (name?.[0] || '?').toUpperCase()

function removeReqById(id) {
  requestsLocal.value = (requestsLocal.value ?? []).filter((r) => r?.id !== id)
}
function addReqIfMissing(obj) {
  const id = obj?.id
  if (!id) return
  if (!(requestsLocal.value ?? []).some((r) => r?.id === id)) {
    requestsLocal.value = [...(requestsLocal.value ?? []), obj]
  }
}

/* ---------- network ---------- */
async function refresh() {
  if (!ownerUuid.value) {
    loading.value = false
    return
  }
  loading.value = true
  errorMessage.value = ''
  infoMessage.value = ''
  try {
    // Endpoint unchanged; now use UUID
    const url = `${BASE_API_LINK}/users/${encodeURIComponent(ownerUuid.value)}/follow_requests`
    const data = await fetchAPI(url)

    // New shape: array of objects
    requestsLocal.value = Array.isArray(data) ? data : []
    // Owner public status is not on this response anymore
    isPublic.value = false
  } catch (e) {
    errorMessage.value = e?.message || 'Failed to load follow requests.'
  } finally {
    loading.value = false
  }
}

const acceptUrl = () =>
  `${BASE_API_LINK}/users/${encodeURIComponent(ownerUuid.value)}/follow_requests`
const denyUrl = () =>
  `${BASE_API_LINK}/users/${encodeURIComponent(ownerUuid.value)}/follow_requests`

/**
 * Prefer UUIDs. Try ID-based payload first; if API rejects, fall back to username payload.
 * @param {{id:string, username:string}} req
 */
async function accept(req) {
  const requesterId = req?.id
  const requesterUsername = req?.username
  if (!ownerUuid.value || !requesterId || isBusyId(requesterId)) return

  errorMessage.value = ''
  infoMessage.value = ''
  busySet.value.add(requesterId)

  const prevReqs = [...(requestsLocal.value ?? [])]
  removeReqById(requesterId)

  try {
    // ID-first payload
    let response = await postToAPI(acceptUrl(), {
      follower_id: requesterId,
      target_id: ownerUuid.value,
    })
    if (response?.error) throw new Error(response.error)

    if (response?.notificationForRecipient) {
      await wsStore.sendNotification(response?.notificationForRecipient)
    }

    infoMessage.value = `Accepted @${requesterUsername}`
  } catch (e1) {
    try {
      // Fallback: username payload (for any legacy code paths)
      let response2 = await postToAPI(acceptUrl(), {
        follower_username: requesterUsername,
        target_username: ownerUsername.value,
      })
      if (response2?.error) throw new Error(response2.error)
      infoMessage.value = `Accepted @${requesterUsername}`
    } catch (e2) {
      requestsLocal.value = prevReqs
      errorMessage.value = e2?.message || e1?.message || 'Failed to accept request.'
    }
  } finally {
    busySet.value.delete(requesterId)
  }
}

/**
 * Deny by UUID, fallback to username if needed.
 * @param {{id:string, username:string}} req
 */
async function deny(req) {
  const requesterId = req?.id
  const requesterUsername = req?.username
  if (!ownerUuid.value || !requesterId || isBusyId(requesterId)) return

  errorMessage.value = ''
  infoMessage.value = ''
  busySet.value.add(requesterId)

  const prevReqs = [...(requestsLocal.value ?? [])]
  removeReqById(requesterId)

  try {
    // ID-first payload
    let response = await deleteToAPI(denyUrl(), {
      follower_id: requesterId,
      target_id: ownerUuid.value,
    })
    if (response?.error) throw new Error(response.error)
    infoMessage.value = `Denied @${requesterUsername}`
  } catch (e1) {
    try {
      // Fallback: username payload
      let response2 = await postToAPI(denyUrl(), {
        follower_username: requesterUsername,
        target_username: ownerUsername.value,
      })
      if (response2?.error) throw new Error(response2.error)
      infoMessage.value = `Denied @${requesterUsername}`
    } catch (e2) {
      requestsLocal.value = prevReqs
      errorMessage.value = e2?.message || e1?.message || 'Failed to deny request.'
    }
  } finally {
    busySet.value.delete(requesterId)
  }
}

/* ---------- events ---------- */
const emit = defineEmits(['close'])
function onClose() {
  emit('close')
}

onMounted(refresh)

/* ---------- expose to template (script setup auto-exposes) ---------- */
</script>

<style scoped>
.fr-modal-overlay {
  align-items: center;
  background: rgba(0, 0, 0, 0.6);
  color: #f1f1f1;
  display: flex;
  font-family: 'Roboto Mono', monospace;
  inset: 0;
  justify-content: center;
  padding: 1rem;
  position: fixed;
  z-index: 1000;
}
.fr-modal {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  max-height: 85vh;
  overflow: hidden;
  width: min(720px, 92vw);
}
.fr-header {
  align-items: center;
  border-bottom: 1px solid #2a2a2a;
  display: flex;
  justify-content: space-between;
  padding: 0.9rem 1rem;
}
.fr-title {
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0;
}
.hdr-actions {
  display: flex;
  gap: 0.4rem;
}
.fr-banner {
  border: 1px solid transparent;
  border-radius: 8px;
  font-size: 0.9rem;
  margin: 0.5rem 1rem 0;
  padding: 0.6rem 0.75rem;
}
.fr-banner.info {
  background: #151515;
  border-color: #2a2a2a;
  color: #bbb;
}
.fr-banner.error {
  background: #2a0000;
  border-color: #661b1b;
  color: #ffb3b3;
}
.icon-btn {
  align-items: center;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #f1f1f1;
  cursor: pointer;
  display: inline-flex;
  justify-content: center;
  padding: 0.4rem;
  transition:
    background 0.15s,
    border-color 0.15s,
    opacity 0.15s;
}
.icon-btn:hover {
  background: #333;
  border-color: #4a4a4a;
}
.icon-btn:disabled {
  cursor: default;
  opacity: 0.6;
}
.icon {
  height: 20px;
  width: 20px;
}
.close-btn {
  background: #2a2a2a;
}
.close-btn:hover {
  background: #333;
}
.fr-body {
  overflow: auto;
  padding: 0.5rem 1rem;
}
.fr-empty {
  background: #151515;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  color: #bbb;
  margin: 0.75rem 0;
  padding: 1rem;
  text-align: center;
}
.fr-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  list-style: none;
  margin: 0.25rem 0 1rem;
  padding: 0;
}
.fr-item {
  align-items: center;
  background: #202020;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  display: flex;
  justify-content: space-between;
  padding: 0.6rem 0.75rem;
}
.fr-left {
  align-items: center;
  display: flex;
  gap: 0.6rem;
  min-width: 0;
}
.avatar {
  align-items: center;
  background: #404040;
  border: 1px solid #2a2a2a;
  border-radius: 50%;
  color: #eaeaea;
  display: flex;
  font-weight: 700;
  height: 36px;
  justify-content: center;
  overflow: hidden;
  user-select: none;
  width: 36px;
}
.avatar img {
  border-radius: 50%;
  display: block;
  height: 100%;
  object-fit: cover;
  width: 100%;
}
.req-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.uname {
  color: #f1f1f1;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fr-actions {
  align-items: center;
  display: flex;
  gap: 0.4rem;
}
.icon-btn.accept {
  background: #20301f;
  border-color: #2f4d2c;
}
.icon-btn.accept:hover {
  background: #294029;
  border-color: #3d6a3b;
}
.icon-btn.deny {
  background: #301f1f;
  border-color: #4d2c2c;
}
.icon-btn.deny:hover {
  background: #402929;
  border-color: #6a3b3b;
}
.fr-footer {
  border-top: 1px solid #2a2a2a;
  display: flex;
  justify-content: center;
  padding: 0.75rem 1rem;
}
.hint {
  color: #9a9a9a;
  font-size: 0.85rem;
  text-align: center;
}
</style>
