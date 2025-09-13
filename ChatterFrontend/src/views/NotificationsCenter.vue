<template>
  <div class="notifications-root">
    <header class="site-header" role="banner">
      <div class="header-left">
        <span class="project-name-span">| Chatter |</span>
        <span class="project-badge">a Bruinsma & Co. project</span>
      </div>
      <nav class="header-right" aria-label="Site">
        <router-link class="link" to="/dashboard">Dashboard</router-link>
      </nav>
    </header>

    <main class="notifications-page" role="main">
      <div class="top-bar">
        <h2>Notifications</h2>
        <div class="top-actions">
          <button
            class="icon-btn"
            type="button"
            title="Clear all"
            aria-label="Clear all notifications"
            @click="clearAllNotifications"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              aria-hidden="true"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
              />
            </svg>
            <span class="btn-label">Clear all</span>
          </button>
        </div>
      </div>

      <div v-if="error" class="error-message">{{ error }}</div>

      <div v-else-if="loading" class="notif-skeleton-wrap">
        <div class="notif-skeleton" v-for="i in 5" :key="i"></div>
      </div>

      <div v-else-if="isEmpty" class="empty-state">No notifications yet.</div>

      <div v-else class="notif-scroll" role="region" aria-label="Notifications list">
        <div class="notif-list newest-first" role="list">
          <div
            v-for="(n, idx) in wsStore.notificationStore"
            :key="idx + '-' + n.timestamp"
            class="notice"
            :class="[typeToClass(n.type), { 'is-clickable': !!n?.extra?.chatId || !!n?.extra?.uuid }]"
            role="article"
            aria-live="off"
            :tabindex="n?.extra?.chatId ? 0 : null"
            @click="goToRelated(n)"
            @keydown.enter.prevent="goToRelated(n)"
            @keydown.space.prevent="goToRelated(n)"
          >
            <div class="notice-content">
              <svg
                class="notice-icon"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <template v-if="n.type === 'success'">
                  <path
                    d="M12 2a10 10 0 1 0 .001 20.001A10 10 0 0 0 12 2zm-1 14.2-4.2-4.2 1.4-1.4L11 13.6l4.8-4.8 1.4 1.4L11 16.2z"
                  />
                </template>
                <template v-else-if="n.type === 'error'">
                  <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" />
                </template>
                <template v-else>
                  <path
                    d="M12 2a10 10 0 1 0 .001 20.001A10 10 0 0 0 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"
                  />
                </template>
              </svg>

              <div class="notice-text">
                <strong class="notice-title">{{ typeToTitle(n.type) }}</strong>
                <p class="notice-message">{{ n.message }}</p>
                <span class="notif-time" :title="new Date(n.timestamp).toString()">{{
                  formatTime(n.timestamp)
                }}</span>
              </div>

              <button
                class="notice-close"
                type="button"
                aria-label="Dismiss notification"
                @click.stop="dismissAt(idx)"
              >
                &times;
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/userStore.js'
import { BASE_API_LINK } from '@/stores/variables.js'
import { deleteToAPI, fetchAPI, putToAPI } from '@/utils/api.js'
import { useChatStore } from '@/stores/websocket.js'
import router from '@/router/index.js'

const userStore = useUserStore()
const wsStore = useChatStore()
const loading = ref(true)
const error = ref(null)

const busyWithNotification = ref(false)

function typeToTitle(t) {
  if (t === 'success') return 'Success'
  if (t === 'error') return 'Error'
  if (t === 'warning') return 'Warning'
  return 'Notification'
}
function typeToClass(t) {
  if (t === 'success') return 'notice-success'
  if (t === 'error') return 'notice-error'
  if (t === 'warning') return 'notice-notification'
  return 'notice-notification'
}

function formatTime(ts) {
  try {
    const d = new Date(ts)
    const date = d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
    })
    const time = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) // add hour12:false for 24h
    return `${date}, ${time}`
  } catch {
    return ts
  }
}

async function dismissAt(index) {
  if (index === -1 || index >= wsStore.notificationStore.length) return
  if (busyWithNotification.value) return

  busyWithNotification.value = true
  try {
    try {
      await clearNotification(index)
      wsStore.notificationStore.splice(index, 1)
    } catch (e) {
      console.error('Error clearing notification:', e)
    }
  } finally {
    busyWithNotification.value = false
  }
}

const isEmpty = computed(() => !loading.value && !error.value && wsStore.notificationStore.length === 0)

onMounted(async () => {
  wsStore.connect(userStore.uuid)
  try {
    const userUUID = userStore.uuid
    const url = `${BASE_API_LINK}/users/${userUUID}/notifications`
    const response = await fetchAPI(url)
    if (response?.error) throw new Error('Failed to fetch notifications')
    wsStore.notificationStore = Array.isArray(response)
      ? response
      : Array.isArray(response?.data)
        ? response.data
        : []
  } catch (e) {
    error.value = e?.message || 'Error loading notifications'
  } finally {
    loading.value = false
  }
})

async function goToRelated(n) {
  const type = n.type

  if (type === 'profile' && !n?.extra?.uuid) return
  if (type === 'success' && !n?.extra?.chatId) return

  if (type === 'profile') {

    const uuid = n?.extra?.uuid
    if (!uuid) return
    busyWithNotification.value = true
    try {
      await router.push(`/profile/${uuid}`)
    } finally { busyWithNotification.value = false }

  } else if (type === 'success') {

    const chatId = n?.extra?.chatId
    if (!chatId) return
    if (busyWithNotification.value) return
    busyWithNotification.value = true
    try {
      const chatStore = useChatStore()
      await router.push('/dashboard')
      chatStore.enterChat(chatId)
    } finally { busyWithNotification.value = false }

  }
}

async function clearNotification(index) {
  const url = `${BASE_API_LINK}/users/${userStore.uuid}/notifications`
  const response = await putToAPI(url, {
    notification_index: index,
  })
  if (response?.error) throw new Error('Failed to clear notifications')
}

async function clearAllNotifications() {
  const url = `${BASE_API_LINK}/users/${userStore.uuid}/notifications`
  const response = await deleteToAPI(url)
  if (response?.error) throw new Error('Failed to clear notifications')
  wsStore.notificationStore = []
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
.header-left { align-items:center; display:flex; gap:0.5rem; justify-content:flex-start; }
.header-right { align-items:center; display:flex; gap:1rem; justify-content:flex-end; }
.link { color:#f1f1f1; font-weight:600; opacity:0.9; text-decoration:none; transition:opacity 0.15s; }
.link:hover { opacity:1; }
.project-badge { color:#e8e8e8; font-family:'Instrument Serif', serif; font-size:1.25rem; letter-spacing:0.2px; opacity:0.95; }
.project-name-span { color:#f1f1f1; font-family:'Roboto Mono', monospace; font-weight:700; letter-spacing:0.2px; }
.site-header { align-items:center; display:grid; gap:0.75rem; grid-template-columns:1fr auto; margin:1rem auto 1rem; max-width:1100px; padding:0 0.5rem; width:100%; }
.btn-label { font:600 0.85rem 'Roboto Mono', monospace; letter-spacing:0.2px; opacity:0.95; }
.empty-state { align-items:center; color:#888; display:flex; font-size:0.95rem; justify-content:center; margin:0.75rem 0; text-align:center; width:100%; }
.error-message { background-color:#2a0000; border-left:4px solid #ff4c4c; border-radius:6px; color:#ffb3b3; font-size:0.9rem; margin-bottom:1rem; padding:0.75rem 1rem; text-align:left; }
.icon-btn { align-items:center; background:none; border:1px solid #555; border-radius:9999px; color:#f1f1f1; cursor:pointer; display:inline-flex; gap:8px; height:32px; justify-content:center; outline:none; padding:0 10px; transition:background-color 0.2s ease, border-color 0.2s ease; }
.icon-btn:hover { background-color:#2a2a2a; border-color:#666; }
.icon-btn svg { display:block; height:16px; width:16px; }
.notif-list { display:flex; flex-direction:column; gap:8px; margin:0 auto; max-width:720px; min-width:0; width:100%; }
.notif-list.newest-first { flex-direction:column-reverse; }
.notif-scroll { flex:1; margin:0 auto; max-width:720px; min-height:0; overflow-x:hidden; overflow-y:auto; padding:0 12px; scrollbar-gutter:stable both-edges; width:100%; }
.notif-skeleton { animation:pulse 1.2s ease-in-out infinite; background:linear-gradient(90deg, #262626 25%, #2f2f2f 37%, #262626 63%); border-radius:10px; height:64px; margin:8px 0; width:100%; }
.notif-skeleton-wrap { margin:0 auto; max-width:720px; width:100%; }
.notif-time { color:#bbb; display:block; font-size:0.8rem; margin-top:2px; opacity:0.9; }
.notifications-page { display:flex; flex:1; flex-direction:column; gap:12px; min-height:0; overflow-x:hidden; padding:1rem; }
.notifications-root { background-color:#0d0d0d; color:#f1f1f1; display:flex; flex-direction:column; font-family:'Roboto Mono', monospace; min-height:100vh; overflow-x:hidden; }
.notice { align-items:center; background-color:#1f1f1f; border:1px solid #333; border-left:4px solid #9e9e9e; border-radius:10px; box-shadow:0 8px 24px rgba(0, 0, 0, 0.35); color:#e0e0e0; margin:8px 0; max-width:720px; overflow-x:hidden; width:100%; }
.notice-close { background:transparent; border:none; color:inherit; cursor:pointer; font-size:1.25rem; line-height:1; margin-left:auto; opacity:0.9; padding:0.25rem 0.4rem; transition:opacity 0.2s ease; }
.notice-close:hover { opacity:1; }
.notice-content { align-items:center; display:flex; gap:12px; min-width:0; padding:0.9rem 1rem; }
.notice-error { border-left-color:#ff4c4c; }
.notice-icon { flex:0 0 20px; height:20px; opacity:0.95; width:20px; }
.notice-message { font-size:0.9rem; line-height:1.35; margin:0; opacity:0.95; overflow-wrap:anywhere; word-break:break-word; }
.notice-notification { border-left-color:#9e9e9e; }
.notice-slide-enter-active, .notice-slide-leave-active { transition:opacity 0.25s ease, transform 0.25s ease; }
.notice-slide-enter-from, .notice-slide-leave-to { opacity:0; transform:translateY(-12px); }
.notice-success { border-left-color:#2bd46b; }
.notice.is-clickable { cursor:pointer; }
.notice.is-clickable:hover { background-color:#222; }
.notice.is-clickable:focus-visible { outline:2px solid #666; outline-offset:2px; }
.notice-text { display:flex; flex-direction:column; gap:2px; min-width:0; }
.notice-title { font-size:0.95rem; font-weight:700; line-height:1.2; margin:0; }
.top-actions { align-items:center; display:flex; gap:8px; }
.top-bar { align-items:center; background-color:#0d0d0d; display:flex; justify-content:space-between; margin:0 auto 0.75rem; max-width:720px; padding:0 12px; position:sticky; top:0; width:100%; z-index:3; }
@keyframes pulse {
  0% { opacity:1; }
  50% { opacity:0.6; }
  100% { opacity:1; }
}
</style>
