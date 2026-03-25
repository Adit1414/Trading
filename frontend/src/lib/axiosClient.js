import axios from 'axios'
import toast from 'react-hot-toast'
import { supabase } from './supabaseClient'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Request interceptor: attach JWT ─────────────────────────────
api.interceptors.request.use(
  async (config) => {
    try {
      const { data } = await supabase.auth.getSession()
      const token = data?.session?.access_token
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    } catch (err) {
      console.error('[axiosClient] Failed to get Supabase session:', err)
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── Response interceptor: handle errors ─────────────────────────
api.interceptors.response.use(
  (response) => {
    console.log(`[API] ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data)
    return response
  },
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail

    console.error(`[API ERROR] ${status} — ${error.config?.url}`, error.response?.data)

    switch (status) {
      case 401:
        toast.error('Session expired. Redirecting to login…')
        // Force redirect to login
        window.location.href = '/login'
        break
      case 422:
        console.error('[API 422] Validation errors:', detail)
        if (typeof detail === 'string') {
          toast.error(detail)
        } else if (Array.isArray(detail)) {
          detail.forEach((err) =>
            toast.error(`${err.loc?.join('.')}: ${err.msg}`)
          )
        } else {
          toast.error('Validation error — check console for details.')
        }
        break
      case 429:
        toast.error('Rate limit exceeded. Please wait before trying again.')
        break
      case 500:
        toast.error('Server error. Please try again later.')
        break
      default:
        if (detail) {
          toast.error(typeof detail === 'string' ? detail : 'An error occurred.')
        } else {
          toast.error('Network error. Check your connection.')
        }
    }

    return Promise.reject(error)
  }
)

export default api
