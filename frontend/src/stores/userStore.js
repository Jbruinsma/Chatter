// stores/user.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore(
  'user',
  () => {
    const username = ref('')
    const uuid = ref('')
    const isLoggedIn = ref(false)

    function login(loggedInUsername, loggedInId) {
      username.value = loggedInUsername
      uuid.value = loggedInId
      isLoggedIn.value = true
      console.log('User logged in:', loggedInUsername, loggedInId)
    }

    function logout() {
      username.value = ''
      uuid.value = ''
      isLoggedIn.value = false
    }

    // ✅ expose uuid
    return { username, uuid, isLoggedIn, login, logout }
  },
  {
    persist: {
      key: 'bruinsma-user',
      storage: localStorage,
      // ✅ persist uuid too (optional but usually desired)
      paths: ['username', 'uuid', 'isLoggedIn'],
    },
  }
)
