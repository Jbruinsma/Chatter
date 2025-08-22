import {BASE_API_LINK} from "@/stores/variables.js";

export async function postToAPI(endpoint, payload) {
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.error || 'API POST request failed')
    }

    return data
  } catch (error) {
    console.error(`POST ${endpoint} failed:`, error.message)
    throw error
  }
}

export async function fetchAPI(endpoint) {
  try {
    const response = await fetch(endpoint)

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.error || 'API GET request failed')
    }

    return data
  } catch (error) {
    console.error(`GET ${endpoint} failed:`, error.message)
    throw error
  }
}

export function getWebSocketUrl(path) {
  const apiUrl = new URL(BASE_API_LINK);
  const wsProtocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
  return `${wsProtocol}//${apiUrl.host}${path}`;
}
