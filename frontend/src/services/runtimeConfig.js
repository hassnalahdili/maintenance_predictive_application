const devApiBaseUrl = 'http://localhost:8000'

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? '/api' : devApiBaseUrl)

export function buildLiveSocketUrl(token) {
  if (import.meta.env.VITE_WS_BASE_URL) {
    return `${import.meta.env.VITE_WS_BASE_URL}/ws/live?token=${encodeURIComponent(token)}`
  }
  if (import.meta.env.PROD) {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    return `${protocol}://${window.location.host}/ws/live?token=${encodeURIComponent(token)}`
  }
  return `ws://${window.location.hostname}:8000/ws/live?token=${encodeURIComponent(token)}`
}
