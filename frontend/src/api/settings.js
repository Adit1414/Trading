import api from '../lib/axiosClient'

async function withRetry(fn, retries = 2, delayMs = 250) {
  let lastError
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      return await fn()
    } catch (err) {
      lastError = err
      // Retry only transient network failures (no HTTP response).
      if (err?.response || attempt === retries) break
      await new Promise((resolve) => setTimeout(resolve, delayMs * (attempt + 1)))
    }
  }
  throw lastError
}

export async function getProfile() {
  const { data } = await withRetry(() => api.get('/users/profile'))
  return data
}

export async function updateProfile(payload) {
  const { data } = await api.put('/users/profile', payload)
  return data
}

export async function updateAvatar(payload) {
  const { data } = await api.post('/users/profile/avatar', payload)
  return data
}

export async function getNotificationPreferences() {
  const { data } = await withRetry(() => api.get('/users/preferences/notifications'))
  return data
}

export async function updateNotificationPreferences(payload) {
  const { data } = await api.put('/users/preferences/notifications', payload)
  return data
}

export async function getTradingPreferences() {
  const { data } = await withRetry(() => api.get('/users/preferences/trading'))
  return data
}

export async function updateTradingPreferences(payload) {
  const { data } = await api.put('/users/preferences/trading', payload)
  return data
}

export async function getActiveSessions() {
  const { data } = await withRetry(() => api.get('/users/sessions/active'))
  return data
}

export async function revokeAllSessions() {
  const { data } = await api.delete('/users/sessions/revoke_all')
  return data
}

export async function setupTwoFA() {
  const { data } = await api.post('/users/security/2fa/setup')
  return data
}

export async function verifyTwoFA(code) {
  const { data } = await api.post('/users/security/2fa/verify', { code })
  return data
}

export async function exportUserData() {
  const { data } = await api.get('/users/export-data')
  return data
}

export async function deleteUserAccount() {
  const { data } = await api.delete('/users/account')
  return data
}
