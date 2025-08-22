<template>
  <div class="settings-root">
    <header class="site-header" role="banner">
      <div class="header-left">
        <span class="project-name-span">| Chatter |</span> <span class="project-badge">a Bruinsma & Co. project</span>
      </div>
      <nav class="header-right" aria-label="Site">
        <router-link class="link" to="/dashboard">Dashboard</router-link>
      </nav>
    </header>

    <div class="settings-page">
      <header class="settings-header">
        <h1 class="title">Settings</h1>
        <p class="subtitle">Manage your account, profile, and privacy.</p>
      </header>

      <div class="settings-stack">
        <section class="card">
          <h2 class="card-title">Profile photo</h2>
          <p class="card-hint">Upload a picture for your profile. PNG or JPG, up to 5 MB.</p>

          <div class="pfp-row">
            <label class="avatar-wrapper" :class="{ 'has-image': !!avatarPreview, 'is-loading': loading.avatar }" tabindex="0">
              <input class="file-input" type="file" accept="image/*" @change="onFileChange" aria-label="Upload new profile photo" />
              <img v-if="avatarPreview" :src="avatarPreview" alt="Profile photo" class="avatar" />
              <div v-else class="avatar-fallback">{{ initials }}</div>
              <div class="avatar-overlay">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="avatar-icon"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"/></svg>
                <span class="avatar-text">Change</span>
              </div>
            </label>
          </div>
        </section>

        <section class="card">
          <h2 class="card-title">Username</h2>
          <p class="card-hint">Change how others see you in chats.</p>
          <div class="field-row">
            <input
              v-model.trim="username"
              class="input"
              type="text"
              name="username"
              autocomplete="username"
              placeholder="Enter new username"
              @keydown.enter.prevent="saveUsername"
            />
            <button class="btn" :disabled="loading.username || username === currentUsername" @click="saveUsername">
              <span v-if="!loading.username">Save username</span>
              <span v-else>Saving…</span>
            </button>
          </div>

          <transition name="fade">
            <p v-if="usernameSuccess" class="alert success">{{ usernameSuccess }}</p>
          </transition>

          <transition name="fade">
            <p v-if="usernameError" class="alert error">{{ usernameError }}</p>
          </transition>
        </section>

        <section class="card">
          <h2 class="card-title">Public profile</h2>
          <p class="card-hint">Control who can message you.</p>

          <label class="switch" :aria-checked="publicStatus ? 'true' : 'false'" role="switch">
            <input
              id="public-toggle"
              type="checkbox"
              :checked="publicStatus"
              @change="togglePublic"
              :disabled="loading.public"
            />
            <span class="slider" aria-hidden="true"></span>
            <span class="switch-label">{{ publicStatus ? 'Public' : 'Private' }}</span>
          </label>

          <transition name="fade">
            <p v-if="publicToggleSuccess" class="alert success">{{ publicToggleSuccess }}</p>
          </transition>
          <transition name="fade">
            <p v-if="publicToggleError" class="alert error">{{ publicToggleError }}</p>
          </transition>

        </section>

        <section class="card danger">
          <h2 class="card-title">Log out</h2>
          <p class="card-hint">You will be signed out on this device.</p>
          <button class="btn danger" :disabled="loading.logout" @click="logout">
            <span v-if="!loading.logout">Log out</span>
            <span v-else>Logging out…</span>
          </button>
        </section>
      </div>

      <transition name="fade">
        <p v-if="success" class="alert success">{{ success }}</p>
      </transition>
      <transition name="fade">
        <p v-if="error" class="alert error">{{ error }}</p>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from "@/stores/userStore.js"
import {verifyLogin, verifyUserExistence} from "@/utils/verification.js";
import {BASE_API_LINK} from "@/stores/variables.js";
import {fetchAPI, postToAPI} from "@/utils/api.js";
import {useChatStore} from "@/stores/websocket.js";

const userStore = useUserStore()
const webSocket = useChatStore()
const router = useRouter()

const currentUsername = computed(() => userStore.username)
const username = ref(currentUsername.value)
const publicStatus = ref(false)
const avatarPreview = ref(null)
const avatarFile = ref(null)
const loading = ref({ avatar:false, username:false, public:false, logout:false })


const usernameSuccess = ref('')
const publicToggleSuccess = ref('')
const success = ref('')


const usernameError = ref('')
const publicToggleError = ref('')
const error = ref('')

const initials = computed(() => {
  const name = (currentUsername.value || '').trim()
  if (!name) return ';)'
  const parts = name.split(/\s+|_/).filter(Boolean)
  const letters = (parts[0]?.[0] || '') + (parts[1]?.[0] || '')
  return letters.toUpperCase() || name.slice(0, 2).toUpperCase()
})

onMounted(async () => {
  await verifyLogin()
  const url = `${BASE_API_LINK}/users/user/${userStore.username}`
  const response = await fetchAPI(url)

  if (response.error) {
    error.value = response.error
    return
  }

  const userPublicStatus = response.public_status
  const pfpURL = response.profile_picture

  publicStatus.value = userPublicStatus
  avatarPreview.value = pfpURL

})

function onFileChange(e) {}



async function saveUsername() {
  if (/\s/.test(username.value) || !username.value.trim()) {
    usernameError.value = "Username cannot contain spaces"
    return
  }

  const exists = await verifyUserExistence(username.value).exists

  if (exists) {
    usernameError.value = "Username already exists"
    return
  }

  const newUsername = username.value

  const url = `${BASE_API_LINK}/users/user/${currentUsername.value}/update_username`

  const response = await postToAPI(url, {
    'old_username': currentUsername.value,
    'new_username': newUsername
  })

  if (response.error) {
    usernameError.value = response.error
    return
  }

  userStore.username = newUsername
  currentUsername.value = newUsername
  await webSocket.updateUsername(newUsername)

  usernameError.value = ""
  usernameSuccess.value = "Username updated successfully"

}

async function togglePublic() {
  publicStatus.value = !publicStatus.value
  const url = `${BASE_API_LINK}/users/user/${userStore.username}/update_public_status`
  const response = await postToAPI(url, {
    'is_public': publicStatus.value
  })

  console.log("RESPONSE: ", response)

  if (response.error) {
    publicToggleError.value = response.error
    return
  }

  publicToggleSuccess.value = response.message
  publicToggleError.value = ""
}

async function logout() {
  userStore.logout()
  webSocket.disconnect()
  await router.push("/")
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
:root {}
.settings-page { color:#e6e6e6; display:flex; flex-direction:column; gap:1rem; margin:0 auto; max-width:720px; padding:1.25rem; }
.settings-header { background-color:#1a1a1a; border:1px solid #333; border-radius:10px; padding:1rem 1.25rem; }
.title { font:700 1.25rem/1.2 'Roboto Mono', monospace; margin:0 0 .25rem; }
.subtitle { color:#aaa; font:400 .95rem/1.4 'Roboto Mono', monospace; margin:0; }
.settings-stack { display:flex; flex-direction:column; gap:1rem; }
.card { background-color:#262626; border:1px solid #333; border-radius:12px; padding:1rem; }
.card.danger { background-color:#2a1f1f; border-color:#433; }
.card-title { font:700 1.05rem/1.2 'Roboto Mono', monospace; margin:0 0 .25rem 0; }
.card-hint { color:#9a9a9a; font-size:.9rem; margin:0 0 .75rem; }
.pfp-row { align-items:center; display:flex; flex-wrap:wrap; gap:1rem; justify-content:center; }
.avatar-wrapper { background:#1a1a1a; border:1px solid #333; border-radius:50%; cursor:pointer; display:grid; height:84px; place-items:center; position:relative; width:84px; }
.avatar { border-radius:50%; height:100%; object-fit:cover; width:100%; }
.avatar-fallback { color:#bbb; font:700 1.1rem 'Roboto Mono', monospace; }
.avatar-overlay { align-items:center; background-color:rgba(0,0,0,.5); border-radius:50%; color:#eaeaea; display:flex; inset:0; justify-content:center; opacity:0; position:absolute; transition:opacity .15s ease; }
.avatar-wrapper:hover .avatar-overlay, .avatar-wrapper:focus-within .avatar-overlay { opacity:1; }
.avatar-icon { height:18px; stroke:currentColor; width:18px; }
.avatar-text { font:600 .85rem 'Roboto Mono', monospace; margin-left:.4rem; }
.file-input { cursor:pointer; height:100%; inset:0; opacity:0; position:absolute; width:100%; }
.field-row { align-items:center; display:flex; flex-wrap:wrap; gap:.6rem; }
.input { background:#1b1b1b; border:1px solid #3a3a3a; border-radius:8px; color:#eee; min-width:220px; outline:none; padding:.6rem .7rem; }
.input:focus { border-color:#6a6a6a; box-shadow:0 0 0 2px rgba(255,255,255,0.04); }
.btn { background:#2f2f2f; border:1px solid #464646; border-radius:8px; color:#f3f3f3; cursor:pointer; font:700 .95rem 'Roboto Mono', monospace; padding:.55rem .8rem; }
.btn:hover { background:#373737; }
.btn:disabled { cursor:not-allowed; opacity:.6; }
.btn.danger { background:#3a2222; border-color:#5a2a2a; }
.btn.danger:hover { background:#452525; }
.switch { align-items:center; cursor:pointer; display:inline-flex; gap:.7rem; user-select:none; }
.switch input { opacity:0; pointer-events:none; position:absolute; }
.slider { background:#3a3a3a; border:1px solid #555; border-radius:999px; height:26px; position:relative; transition:background .15s ease; width:44px; }
.slider::after { background:#d6d6d6; border-radius:50%; content:""; height:20px; left:2px; position:absolute; top:2px; transition:transform .18s ease; width:20px; will-change:transform; }
.switch input:checked + .slider { background:#266; border-color:#3a8; }
.switch input:checked + .slider::after { transform:translateX(18px); }
.switch-label { color:#ddd; font:600 .95rem 'Roboto Mono', monospace; }
.alert { border:1px solid; border-radius:8px; margin-top:.5rem; padding:.6rem .8rem; }
.alert.success { background:#1f2a1f; border-color:#2c5a2c; color:#cae9ca; }
.alert.error { background:#2a1f1f; border-color:#5a2c2c; color:#f0cccc; }
.fade-enter-active, .fade-leave-active { transition:opacity .18s ease; }
.fade-enter-from, .fade-leave-to { opacity:0; }
.header-left { align-items:center; display:flex; gap:.5rem; justify-content:flex-start; }
.header-right { align-items:center; display:flex; gap:1rem; justify-content:flex-end; }
.link { color:#f1f1f1; font-weight:600; opacity:.9; text-decoration:none; transition:opacity .15s; }
.link:hover { opacity:1; }
.project-badge { color:#e8e8e8; font-family:'Instrument Serif', serif; font-size:1.25rem; letter-spacing:.2px; opacity:.95; }
.project-name-span { color:#f1f1f1; font-family:'Roboto Mono', monospace; font-weight:700; letter-spacing:.2px; }
.site-header { align-items:center; display:grid; gap:.75rem; grid-template-columns:1fr auto; margin:1rem auto 1rem; max-width:1100px; padding:0 .5rem; width:100%; }
</style>
