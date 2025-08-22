<template>
  <div class="landing-wrapper">
    <div class="card">
      <h1 class="title">Welcome to Chatter</h1>
      <div class="header-left">
        <span class="project-badge">a Bruinsma &amp; Co. project</span>
      </div>

      <div class="tab-toggle">
        <button :class="{ active: isLogin }" @click="setEntryPoint('login')">Log In</button>
        <button :class="{ active: !isLogin }" @click="setEntryPoint('register')">Register</button>
      </div>

      <form class="form" @submit.prevent="handleSubmit">
        <input v-model="username" type="text" placeholder="Username" name="username" />
        <input v-model="password" type="password" placeholder="Password" name="password" />
        <input
          v-if="!isLogin"
          v-model="confirmPassword"
          type="password"
          placeholder="Confirm Password"
          name="confirm_password"
        />

        <div v-if="!isLogin" class="option" role="group" aria-labelledby="public-title">
          <div class="option-label">
            <div id="public-title" class="option-title">{{ publicStatus }} profile</div>
            <div class="option-hint">{{ statusMessage }} can message you.</div>
          </div>

          <label class="switch" :aria-checked="isPublic ? 'true' : 'false'" role="switch" aria-labelledby="public-title">
            <input id="publicToggle" type="checkbox" :checked="isPublic" @click="switchPublicStatus" />
            <span class="slider"></span>
          </label>
        </div>

        <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        <div v-if="successMessage" class="success-message">{{ successMessage }}</div>

        <button type="submit">{{ isLogin ? 'Log In' : 'Register' }}</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { postToAPI } from "@/utils/api.js";
import { useChatStore } from "@/stores/websocket.js";
import router from "@/router/index.js";
import {useUserStore} from "@/stores/userStore.js";
import {BASE_API_LINK} from "@/stores/variables.js";

const isLogin = ref(true)
const username = ref('')
const password = ref('')
const confirmPassword = ref('')

const isPublic = ref(true)
const publicStatus = computed(() => isPublic.value ? 'Public' : 'Private')
const statusMessage = computed(() => isPublic.value ? 'Anyone' : 'Only friends')

const errorMessage = ref('')
const successMessage = ref('')

onMounted(() => {
  const chatStore = useChatStore()
  const userStore = useUserStore()
  if (userStore.isLoggedIn) {
    userStore.logout()
    chatStore.disconnect()
  }
})

function setErrorMessage(msg){ errorMessage.value = msg; successMessage.value = '' }
function setSuccessMessage(msg){ successMessage.value = msg; errorMessage.value = '' }

function setEntryPoint(point){
  isLogin.value = point === 'login'
  errorMessage.value = ''
  successMessage.value = ''
}

function switchPublicStatus(event){
  if (event && event.target) {
    isPublic.value = event.target.checked
  } else {
    isPublic.value = !isPublic.value
  }
}

async function handleSubmit(){
  errorMessage.value = ''
  successMessage.value = ''

  if (!username.value.trim() || !password.value) { setErrorMessage('Please fill in all fields'); return }

  if (isLogin.value) {
    try {
      const url = `${BASE_API_LINK}/users/login`
      const response = await postToAPI(url, { username: username.value, password: password.value })
      if (response.error){ setErrorMessage(response.error) }
      else {
        const userStore = useUserStore()
        userStore.login(username.value)
        await router.push('/dashboard')
      }
    } catch (e) { setErrorMessage(e.message) }
    return
  }

  if (password.value !== confirmPassword.value) { setErrorMessage('Passwords do not match'); return }
  try {
    const url = `${BASE_API_LINK}/users/register`
    const response = await postToAPI(url, { username: username.value, password: password.value, is_public: isPublic.value })
    if (response.error){ setErrorMessage(response.error) }
    else {
      setSuccessMessage('Registration successful')
      const userStore = useUserStore()
      userStore.login(username.value)
      await router.push('/dashboard')
    }
  } catch (e) { setErrorMessage(e.message) }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');

.card {background-color:#1a1a1a; border-radius:12px; box-shadow:0 10px 30px rgba(0,0,0,0.6); max-width:400px; padding:2rem 2.5rem; text-align:center; width:100%;}
.error-message {background-color:#2a0000; border-left:4px solid #b33; border-radius:6px; color:#f7dada; font-size:0.9rem; margin-bottom:1rem; padding:0.75rem 1rem; text-align:left;}
.form {display:flex; flex-direction:column; gap:1rem;}
.form button[type="submit"] {background-color:#3a3a3a; border:none; border-radius:6px; color:#f1f1f1; cursor:pointer; font-weight:700; padding:0.75rem; transition:background-color .2s ease;}
.form button[type="submit"]:hover {background-color:#555;}
.form input {background-color:#2a2a2a; border:none; border-radius:6px; color:#f1f1f1; font-size:0.95rem; padding:0.75rem;}
.form input:focus {background-color:#333; outline:none;}
.landing-wrapper {align-items:center; background-color:#0d0d0d; background-image:radial-gradient(ellipse at top,#1f1f1f 0%,transparent 60%), radial-gradient(ellipse at bottom,#1a1a1a 0%,transparent 60%); display:flex; font-family:'Roboto Mono', monospace; height:100vh; justify-content:center;}
.project-badge {color:#e8e8e8; font-family:'Instrument Serif', serif; font-size:1.25rem; letter-spacing:.2px; opacity:.95;}
.tab-toggle {display:flex; justify-content:center; margin-bottom:1rem;}
.tab-toggle button {background:none; border:none; color:#ccc; cursor:pointer; font-size:1rem; font-weight:600; padding:0.5rem 1rem; transition:color .2s ease;}
.tab-toggle button.active {border-bottom:2px solid #888; color:#fff;}
.tab-toggle button:hover {color:#fff;}
.title {color:#f1f1f1; font-size:1.75rem; margin-bottom:0.25rem;}

.option {align-items:center; background-color:#161616; border:1px solid #2a2a2a; border-radius:10px; display:grid; gap:.25rem; grid-template-columns:1fr auto; padding:.85rem 1rem;}
.option-label {display:flex; flex-direction:column; gap:.25rem;}
.option-title {color:#e6e6e6; font-size:.95rem; font-weight:700; letter-spacing:.2px;}
.option-hint {color:#9a9a9a; font-size:.8rem;}

.switch {align-items:center; display:flex; height:28px; position:relative; width:48px;}
.switch input {appearance:none; background-color:#2b2b2b; border:1px solid #3a3a3a; border-radius:9999px; cursor:pointer; height:28px; margin:0; outline:none; position:relative; transition:background-color .2s,border-color .2s; width:48px;}
.switch input:focus-visible {box-shadow:0 0 0 2px rgba(255,255,255,.12);}
.switch .slider {border-radius:9999px; inset:0; pointer-events:none; position:absolute;}
.switch input::before {background-color:#f1f1f1; border-radius:50%; content:""; height:22px; left:3px; position:absolute; top:3px; transition:transform .2s; width:22px;}
.switch input:checked {background:#266; border-color:#3a8;}
.switch input:checked::before {transform:translateX(18px);}
</style>
