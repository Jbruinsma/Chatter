<template>
  <div class="profile-page">
    <header class="site-header" role="banner">
      <div class="header-left">
        <span class="project-name-span">| Chatter |</span>
        <span class="project-badge">a Bruinsma &amp; Co. project</span>
      </div>

      <form class="header-search" @submit.prevent="goToUser" role="search" aria-label="Go to user">
        <input v-model="searchQuery" class="search-input" type="text" placeholder="Search username..." autocomplete="off" />
        <button class="search-btn" type="submit" aria-label="Search">
          <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
        </button>
      </form>

      <nav class="header-right" aria-label="Site">
        <router-link class="link" to="/">Login</router-link>
        <router-link class="link" to="/dashboard">Dashboard</router-link>
      </nav>
    </header>

    <div v-if="loading" class="banner info" role="status">Loading…</div>

    <div
      v-else-if="error || notFound"
      class="empty-state"
      role="region"
      aria-labelledby="nf-title"
      aria-describedby="nf-desc"
    >
      <div class="fullpage-error-card">
        <h2 id="nf-title" class="nf-title">
          {{ notFound ? 'User not found' : 'Something went wrong' }}
        </h2>
        <p id="nf-desc" class="nf-desc">
          {{ notFound ? `We could not find @${username}.` : error }}
        </p>
      </div>
    </div>

    <section v-else class="profile-header" aria-label="Profile">
      <div class="pfp-wrap">
        <img v-if="user?.profilePicture" :src="user.profilePicture" alt="" class="pfp-img" />
        <div v-else class="pfp-fallback">{{ initials }}</div>
        <span v-if="user?.show_active" class="active-dot" :data-on="user?.is_active ? '1' : '0'" aria-hidden="true"></span>
      </div>

      <div class="meta">
        <h1 class="username">@{{ user?.username || username }}</h1>
        <div class="stats-row" role="group" aria-label="Profile stats">
          <span class="stat"><span class="num">{{ followersCount }}</span> Followers</span>
          <span class="sep">•</span>
          <span class="stat"><span class="num">{{ followingCount }}</span> Following</span>
        </div>
      </div>

      <div v-if="!isSelf" class="action-row">
        <button
          class="btn"
          :class="followBtnClass"
          :disabled="isSelf || followBusy"
          @click="onFollowClick"
          :title="followLabel === 'Pending' ? 'Cancel request'
          : followLabel === 'Following' ? 'Unfollow'
          : 'Follow'">
          {{ followLabel }}
        </button>
        <button v-if="showMessage" class="btn btn-secondary" @click="onMessageClick">Message</button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BASE_API_LINK } from '@/stores/variables.js'
import { fetchAPI, postToAPI } from '@/utils/api.js'
import { useUserStore } from "@/stores/userStore.js"
import { useChatStore } from '@/stores/websocket.js'

/* ---------- routing & store ---------- */
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const chatStore = useChatStore()

/* Prefer UUID in route; fall back to :username for compatibility */
const profileParam = computed(() =>
  route.params.userId || route.params.id || route.params.uuid || route.params.username || ''
)

/* Resolve viewer UUID from store */
function resolveViewerId() {
  return userStore.userId || userStore.id || userStore.uuid || userStore.user?.id || null
}

/* UUID check */
function isUUID(v) {
  return typeof v === 'string' &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
}

/* ---------- state ---------- */
const user = ref(null)             // compact profile payload from API
const loading = ref(true)
const error = ref(null)
const notFound = ref(false)
const viewerId = ref(null)
const searchQuery = ref('')

/* ---------- display helpers ---------- */
const initials = computed(() => (user.value?.username?.[0] || '?').toUpperCase())

/* Counts come from user.stats */
const followersCount = computed(() => user.value?.stats?.followersCount ?? 0)
const followingCount = computed(() => user.value?.stats?.followingCount ?? 0)

/* ---------- relationships & permissions from API ---------- */
const isSelf = computed(() => !!user.value?.relations?.isSelf)
const isPublic = computed(() => !!user.value?.publicStatus)

const inFollowers  = computed(() => !!user.value?.relations?.viewerFollowsUser)  // viewer -> user
const inFollowing  = computed(() => !!user.value?.relations?.userFollowsViewer)  // user -> viewer
const inRequests   = computed(() => !!user.value?.relations?.pendingFollowRequest)
const areFriends   = computed(() => inFollowers.value && inFollowing.value)

const canViewProfile = computed(() => !!user.value?.permissions?.canViewProfile)
const canMessage     = computed(() => !!user.value?.permissions?.canMessage)
const canFollow      = computed(() => !!user.value?.permissions?.canFollow)

const followLabel = computed(() => {
  if (isSelf.value) return ''
  if (inRequests.value) return 'Pending'
  if (areFriends.value) return 'Friends'
  if (inFollowers.value) return 'Following'
  return 'Follow'
})

const followBtnClass = computed(() => {
  switch (followLabel.value) {
    case 'Friends': return 'btn-secondary'
    case 'Following': return 'btn-muted'
    case 'Pending': return 'btn-muted'
    case 'Follow': return 'btn-primary'
    default: return ''
  }
})

const showMessage = computed(() => !isSelf.value && canMessage.value)

/* ---------- network ---------- */
async function loadProfile(){
  loading.value = true
  error.value = null
  notFound.value = false
  user.value = null

  try {
    const key = (profileParam.value || '').trim()
    // console.log("key: ", key)
    const viewer = viewerId.value
    // console.log("viewer: ", viewer)
    if (!key) { notFound.value = true; return }

    const params = new URLSearchParams()
    if (isUUID(key)) params.set('target_profile_uuid', key)
    else params.set('target_profile_username', key)
    params.set('viewer_uuid', viewer)

    const url = `${BASE_API_LINK}/users/profiles/?${params.toString()}`
    // console.log("url: ", url)
    const response = await fetchAPI(url)
    // console.log("response: ", response)

    if (response?.error || response?.permissions?.canViewProfile === false) {
      notFound.value = true
      return
    }

    user.value = response || null
    if (!user.value) notFound.value = true

  } catch (e) {
    error.value = e?.message || 'Failed to load user.'
  } finally {
    loading.value = false
  }
}

/* ---------- actions ---------- */
const followBusy = ref(false)

async function onFollowClick() {
  if (isSelf.value || !canFollow.value) return
  if (!verifyLoginStatus()) return
  if (followBusy.value) return

  followBusy.value = true
  try {
    // Keep your existing follow endpoints; payloads should be IDs.
    const actorId = viewerId.value
    const targetId = user.value?.id
    if (!actorId || !targetId) return

    if (inFollowers.value) {
      const url = `${BASE_API_LINK}/users/${encodeURIComponent(actorId)}/unfollow`
      const res = await postToAPI(url, { target_id: targetId, unfollower_id: actorId })
      if (res?.error) { error.value = res.error; return }

    } else if (inRequests.value) {
      const url = `${BASE_API_LINK}/users/${encodeURIComponent(actorId)}/cancel_follow_request`
      const res = await postToAPI(url, { target_id: targetId, request_sender_id: actorId })
      if (res?.error) { error.value = res.error; return }

    } else {
      const url = `${BASE_API_LINK}/users/${encodeURIComponent(actorId)}/follow`
      const res = await postToAPI(url, { target_id: targetId, follower_id: actorId })
      if (res?.error) { error.value = res.error; return }
      if (res?.notificationForRecipient) {
        console.log("res.notification", res.notificationForRecipient)
        await chatStore.sendNotification(res?.notificationForRecipient)
      }

    }

    // One refresh call rehydrates relations + counts safely
    await loadProfile()

  } finally {
    followBusy.value = false
  }
}

async function onMessageClick(){
  if (!verifyLoginStatus()) return
  if (!canMessage.value) return

  const targetId = user.value?.id
  const actorId = viewerId.value

  const url = `${BASE_API_LINK}/chats/${actorId}/direct_chats/${targetId}`
  const response = await fetchAPI(url)

  if (response?.error) return

  const { chatStatus, chatId } = response

  console.log("chatStatus: ", chatStatus)
  console.log("chatId: ", chatId)

  if (chatStatus && chatId !== null) {
    await router.push('/dashboard')
    chatStore.enterChat(chatId)
  } else {
    console.log("Creating direct chat...")
    await router.push('/dashboard')
    await chatStore.createDirectChat(actorId, targetId)
  }
}

function goToUser() {
  const target = (searchQuery.value || '').trim()
  if (!target || target === profileParam.value) return
  router.push({ path: `/profile/${encodeURIComponent(target)}` })
}

/* ---------- lifecycle ---------- */
onMounted(async () => {
  viewerId.value = resolveViewerId()
  await loadProfile()
})

watch(
  () => [route.params.userId, route.params.id, route.params.uuid, route.params.username],
  async () => {
    searchQuery.value = ''
    await loadProfile()
  }
)

/* ---------- auth guard ---------- */
function verifyLoginStatus() {
  if (!userStore.isLoggedIn) {
    router.push({ path: '/' })
    return false
  }
  return true
}
</script>


<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Roboto:wght@400;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');

.profile-page{color:#f1f1f1;font-family:'Roboto',sans-serif;padding:1rem}
.site-header{align-items:center;display:grid;gap:.75rem;grid-template-columns:1fr auto 1fr;margin:0 auto 1rem;max-width:1100px;padding:0 .5rem;width:100%}
.header-left{align-items:center;display:flex;gap:.5rem;justify-content:flex-start}
.header-right{align-items:center;display:flex;gap:1rem;justify-content:flex-end}
.header-search{align-items:center;display:flex;gap:.35rem;justify-content:center}
.link{color:#f1f1f1;font-weight:600;opacity:.9;text-decoration:none;transition:opacity .15s}
.link:hover{opacity:1}
.project-badge{color:#e8e8e8;font-family:'Instrument Serif',serif;font-size:1.25rem;letter-spacing:.2px;opacity:.95}
.search-input{background-color:#2a2a2a;border:1px solid #333;border-radius:10px;color:#f1f1f1;max-width:300px;padding:.45rem .65rem;width:100%}
.search-btn{align-items:center;background:transparent;border:none;border-radius:8px;color:#f1f1f1;cursor:pointer;display:flex;height:36px;justify-content:center;padding:0;transition:opacity .15s;width:36px}
.search-btn:hover{opacity:.9}
.search-icon{height:20px;stroke:#cfcfcf;width:20px}
.profile-header{align-items:center;display:flex;flex-direction:column;gap:.75rem;margin:0 auto 1rem;max-width:820px;padding:1rem 1rem 0;width:100%}
.pfp-wrap{height:136px;position:relative;width:136px}
.pfp-img{border:2px solid #2a2a2a;border-radius:50%;display:block;height:136px;object-fit:cover;width:136px}
.pfp-fallback{align-items:center;background:#404040;border:2px solid #2a2a2a;border-radius:50%;color:#e6e6e6;display:flex;font-size:1.7rem;font-weight:700;height:136px;justify-content:center;user-select:none;width:136px}
.active-dot{background:#555;border:2px solid #0d0d0d;border-radius:50%;bottom:10px;height:14px;position:absolute;right:10px;width:14px}
.active-dot[data-on="1"]{background:#19c37d}
.meta{align-items:center;display:flex;flex-direction:column;gap:.45rem;text-align:center}
.username{color:#f1f1f1;font-size:1.7rem;font-weight:700;margin:0}
.stats-row{align-items:center;color:#bbb;display:flex;font-size:1rem;gap:.7rem}
.stat .num{color:#fff;font-weight:700}
.sep{opacity:.5}
.action-row{align-items:center;display:flex;gap:.6rem;margin-top:.35rem}
.btn{background-color:#3a3a3a;border:none;border-radius:10px;color:#f1f1f1;cursor:pointer;font-weight:700;padding:.65rem 1.05rem;transition:background-color .15s,opacity .15s}
.btn:hover{background-color:#555}
.btn:disabled{cursor:default;opacity:.6}
.btn-primary{background:#3a3a3a;border:1px solid #444;border-radius:10px;color:#f1f1f1;cursor:pointer;font-weight:700;padding:.65rem 1.05rem;transition:background-color .15s,opacity .15s}
.btn-primary:hover{background:#555}
.btn-muted{background:#2f2f2f;border:1px solid #444;border-radius:10px;color:#f1f1f1;cursor:pointer;font-weight:700;padding:.65rem 1.05rem;transition:background-color .15s,opacity .15s}
.btn-muted:hover{background:#383838}
.btn-secondary{background:#2f2f2f;border:1px solid #444;border-radius:10px;color:#f1f1f1;cursor:pointer;font-weight:700;padding:.65rem 1.05rem;transition:background-color .15s,opacity .15s}
.btn-secondary:hover{background:#3a3a3a}
.banner{border-radius:8px;font-size:.95rem;margin:1rem auto 0;max-width:820px;padding:.8rem 1rem;width:100%}
.banner.info{background:#151515;border:1px solid #2a2a2a;color:#bbb}
.banner.error{background:#2a0000;border:1px solid #661b1b;color:#ffb3b3}
.project-name-span{font-family:'Roboto Mono',monospace;}
@media (max-width:980px){.pfp-wrap{height:120px;width:120px}.pfp-img{height:120px;width:120px}.pfp-fallback{font-size:1.5rem;height:120px;width:120px}.username{font-size:1.55rem}}
@media (max-width:680px){.site-header{grid-template-columns:1fr}.header-left{justify-content:center}.header-right{justify-content:center}}

/* Centered state under the header (no blocking, no dim) */
.empty-state{
  min-height: 65vh;           /* tall enough to center visually on most screens */
  display: grid;
  place-items: center;
  padding: 2rem 1rem;
}
.fullpage-error-card{
  background:#2a0000;
  border:1px solid #661b1b;
  border-radius:12px;
  color:#ffb3b3;
  max-width:680px;
  width:min(92vw,680px);
  padding:1.25rem 1.5rem;
  text-align:center;
  box-shadow:0 10px 40px rgba(0,0,0,.5);
}
.nf-title{font-size:1.5rem;margin:0 0 .25rem}
.nf-desc{font-size:1rem;opacity:.95;margin:0}
</style>
