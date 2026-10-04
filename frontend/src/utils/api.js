// Shared API client: attaches the stored API key to every request and
// broadcasts an event when the server rejects it, so the app can show
// the login screen.

const API_KEY_STORAGE = 'taskd:apiKey'

export const UNAUTHORIZED_EVENT = 'taskd:unauthorized'

export const getStoredApiKey = () => localStorage.getItem(API_KEY_STORAGE)

export const storeApiKey = (key) => localStorage.setItem(API_KEY_STORAGE, key)

export const clearStoredApiKey = () => localStorage.removeItem(API_KEY_STORAGE)

export async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const apiKey = getStoredApiKey()
  if (apiKey) headers['X-API-Key'] = apiKey

  const response = await fetch(path, { ...options, headers })

  if (response.status === 401) {
    clearStoredApiKey()
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
  }
  return response
}
