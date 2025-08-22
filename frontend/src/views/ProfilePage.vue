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
        <img v-if="user?.profile_picture" :src="user.profile_picture" alt="" class="pfp-img" />
        <div v-else class="pfp-fallback">{{ initials }}</div>
        <span v-if="user?.show_active" class="active-dot" :data-on="user?.is_active ? '1' : '0'" aria-hidden="true"></span>
      </div>

      <div class="meta">
        <h1 class="username">{{ user?.username || username }}</h1>
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
          :disabled="isSelf || followBusy || !userStore.isLoggedIn"
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

const route = useRoute()
const router = useRouter()
const username = computed(() => route.params.username)

const user = ref(null)
const followers = ref([])
const following = ref([])
const loading = ref(true)
const error = ref(null)
const notFound = ref(false)

const userStore = useUserStore()
const viewer = ref(null)

const searchQuery = ref('')

const initials = computed(() => (user.value?.username?.[0] || '?').toUpperCase())
const followersCount = computed(() => followers.value.length)
const followingCount = computed(() => following.value.length)

const followBusy = ref(false)

const isSelf = computed(() => {
  const v = (viewer.value || '').trim().toLowerCase()
  const u = (username.value || '').trim().toLowerCase()
  return !!v && !!u && v === u
})

const isPublic = computed(() => !!user.value?.public_status)
const inFollowers = computed(() => !!user.value?.followers?.includes(viewer.value))
const inFollowing = computed(() => !!user.value?.following?.includes(viewer.value))
const inRequests = computed(() => !!user.value?.follow_requests?.includes(viewer.value))
const areFriends = computed(() => inFollowers.value && inFollowing.value)

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

const showMessage = computed(() => !isSelf.value && (isPublic.value || inFollowers.value || areFriends.value))

async function loadProfile(){
  loading.value = true
  error.value = null
  notFound.value = false
  user.value = null
  try {
    const url = `${BASE_API_LINK}/users/user/${encodeURIComponent(username.value)}`
    const response = await fetchAPI(url)
    if (response.error) {
      notFound.value = true
      return
    }
    if (response.blocked_users.includes(viewer.value)){
      notFound.value = true
      return
    }
    user.value = response
    if (!user.value) notFound.value = true

    console.log("USER", user.value)
  } catch (e) {
    error.value = e?.message || 'Failed to load user.'
  } finally {
    loading.value = false
  }
}

async function loadSocialCounts(){
  if (notFound.value || !username.value) return
  loading.value = true
  error.value = null
  try {
    const followersURL = `${BASE_API_LINK}/users/user/${encodeURIComponent(username.value)}/followers`
    const followingURL = `${BASE_API_LINK}/users/user/${encodeURIComponent(username.value)}/following`
    const followersResponse = await fetchAPI(followersURL)
    const followingResponse = await fetchAPI(followingURL)
    followers.value = Array.isArray(followersResponse) ? followersResponse : (followersResponse?.followers ?? [])
    following.value = Array.isArray(followingResponse) ? followingResponse : (followingResponse?.following ?? [])
  } catch (e) {
    error.value = e?.message || 'Failed to load follower data.'
  } finally {
    loading.value = false
  }
}

function goToUser() {
  const target = (searchQuery.value || '').trim()
  if (!target || target === username.value) return
  router.push({ path: `/profile/${encodeURIComponent(target)}` })
}

async function onFollowClick() {
  if (isSelf.value) return
  if (!verifyLoginStatus()) return
  if (followBusy.value) return

  followBusy.value = true
  try {
    if (inFollowers.value) {
      console.log("UNFOLLOWING")
      const url = `${BASE_API_LINK}/users/user/${encodeURIComponent(viewer.value)}/unfollow`
      const response = await postToAPI(url, {
        'target_username': user.value.username,
        'unfollower_username': viewer.value
      })
      if (response.error) {
        console.error("Failed to unfollow:", response.error)
        error.value = response.error
        return
      }
      await loadProfile()
      await loadSocialCounts()

    } else if (inRequests.value) {
      console.log("CANCELING REQUEST")
      const url = `${BASE_API_LINK}/users/user/${encodeURIComponent(viewer.value)}/cancel_follow_request`
      const response = await postToAPI(url, {
        'target_username': user.value.username,
        'request_sender_username': viewer.value
      })
      if (response.error) {
        console.error("Failed to cancel request:", response.error)
        error.value = response.error
        return
      }
      await loadProfile()
      await loadSocialCounts()

    } else {
      const url = `${BASE_API_LINK}/users/user/${encodeURIComponent(viewer.value)}/follow`
      const response = await postToAPI(url, {
        'target_username': user.value.username,
        'follower_username': viewer.value
      })
      if (response.error) {
        console.error("Failed to follow:", response.error)
        error.value = response.error
        return
      }
      await loadProfile()
      await loadSocialCounts()
    }
  } finally {
    followBusy.value = false
  }
}

function onMessageClick(){
  if (!verifyLoginStatus()) return
  router.push("/Dashboard")
}

onMounted(async () => {
  viewer.value = userStore.username
  await loadProfile()
  if (!notFound.value) await loadSocialCounts()
})

watch(() => route.params.username, async () => {
  searchQuery.value = ''
  await loadProfile()
  if (!notFound.value) await loadSocialCounts()
})

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
