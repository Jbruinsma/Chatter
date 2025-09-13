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

export async function putToAPI(endpoint, payload) {
  try {
    const response = await fetch(endpoint, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.error || 'API PUT request failed')
    }

    return data
  } catch (error) {
    console.error(`PUT ${endpoint} failed:`, error.message)
    throw error
  }
}

export async function deleteToAPI(endpoint, payload = null) {
  try {
    const options = {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    }

    if (payload !== null) {
      options.body = JSON.stringify(payload)
    }

    const response = await fetch(endpoint, options)

    // Handle JSON and 204 No Content gracefully
    let data = null
    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      data = await response.json()
    }

    if (!response.ok) {
      throw new Error((data && data.error) || 'API DELETE request failed')
    }

    return data ?? { success: true }
  } catch (error) {
    console.error(`DELETE ${endpoint} failed:`, error.message)
    throw error
  }
}

export function getWebSocketUrl(path) {
  const apiUrl = new URL(BASE_API_LINK);
  const wsProtocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
  return `${wsProtocol}//${apiUrl.host}${path}`;
}

