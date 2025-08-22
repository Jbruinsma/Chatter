import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore(
  'user',
  () => {
    const username = ref('')
    const isLoggedIn = ref(false)

    function login(user) {
      username.value = user
      isLoggedIn.value = true
    }

    function logout() {
      username.value = ''
      isLoggedIn.value = false
    }

    return { username, isLoggedIn, login, logout }
  },
  {
    // pinia-plugin-persistedstate config
    persist: {
      key: 'bruinsma-user',
      storage: localStorage,        // use sessionStorage if you prefer tab-only
      paths: ['username', 'isLoggedIn'],
    },
  }
)
