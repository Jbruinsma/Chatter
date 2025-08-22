import {useUserStore} from "@/stores/userStore.js";
import router from "@/router/index.js";
import {BASE_API_LINK} from "@/stores/variables.js";
import {fetchAPI} from "@/utils/api.js";

export async function verifyLogin(){
  const userStore = useUserStore()
  const currentUser = userStore.username
  if (currentUser === null || currentUser === undefined || currentUser === '' || userStore.isLoggedIn === false) {
    await router.push('/')
  }
}


export async function verifyUserExistence(username){
  const url = `${BASE_API_LINK}/users/user/${username}`
  const response = await fetchAPI(url)
  const exists = !response.error
  return {exists: exists, data: response}
}
