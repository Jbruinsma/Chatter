import { BASE_API_LINK } from '@/stores/variables.js'
import { fetchAPI } from '@/utils/api.js'


export async function getUserChatInfoById(userId, chatId) {
  const url = `${BASE_API_LINK}/users/?user_uuid=${userId}`
  const response = await fetchAPI(url)

  if (response.error) { return null }

  return {
    id: userId,
    username: response.username,
    avatar: response.profile_picture,
    role: response.chat_requests.includes(chatId) ? 'Invited' : 'Participant',
  }

}
