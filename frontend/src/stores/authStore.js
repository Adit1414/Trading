import { create } from 'zustand'
import { supabase } from '../lib/supabaseClient'

export const useAuthStore = create((set, get) => ({
  user: null,
  session: null,
  loading: true,

  initialize: () => {
    // Listen for auth state changes
    supabase.auth.onAuthStateChange((event, session) => {
      console.log('[Auth] State changed:', event, session?.user?.email)
      set({
        session,
        user: session?.user ?? null,
        loading: false,
      })
    })

    // Get initial session
    supabase.auth.getSession().then(({ data }) => {
      console.log('[Auth] Initial session:', data.session?.user?.email ?? 'none')
      set({
        session: data.session,
        user: data.session?.user ?? null,
        loading: false,
      })
    })
  },

  login: async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    if (error) {
      console.error('[Auth] Login failed:', error.message)
      throw error
    }
    console.log('[Auth] Login success:', data.user.email)
    set({ user: data.user, session: data.session, loading: false })
    return data
  },

  signup: async (email, password) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
    })
    if (error) {
      console.error('[Auth] Signup failed:', error.message)
      throw error
    }
    console.log('[Auth] Signup success:', data.user?.email)
    // Supabase auto-logins after signup if email confirmations are disabled
    if (data.session) {
      set({ user: data.user, session: data.session, loading: false })
    }
    return data
  },

  loginAsGuest: () => {
    console.log('[Auth] Logging in as Guest')
    // Provide a mocked user session
    const mockUser = { id: 'guest-123', email: 'guest@algotrading.local' }
    const mockSession = { access_token: 'guest-token', user: mockUser }
    set({ user: mockUser, session: mockSession, loading: false })
    return { user: mockUser, session: mockSession }
  },

  logout: async () => {
    const { error } = await supabase.auth.signOut()
    if (error) {
      console.error('[Auth] Logout failed:', error.message)
    }
    set({ user: null, session: null })
  },
}))
