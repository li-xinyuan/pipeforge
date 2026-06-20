import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '../router'

export interface AuthUser {
  id: string
  username: string
  role: string
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>('')
  const user = ref<AuthUser | null>(null)
  const jwtEnabled = ref<boolean | null>(null) // null = unknown (not checked yet)

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  /** Check if JWT auth is enabled on the backend */
  async function checkJwtStatus(): Promise<boolean> {
    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: '__probe__', password: '__probe__' }),
      })
      const data = await resp.json()
      // If AUTH_DISABLED, JWT is not enabled
      if (data.code === 'AUTH_DISABLED') {
        jwtEnabled.value = false
        return false
      }
      // Any other response means JWT is enabled
      jwtEnabled.value = true
      return true
    } catch {
      // Network error — assume no auth
      jwtEnabled.value = false
      return false
    }
  }

  /** Login with username and password */
  async function login(username: string, password: string): Promise<{ success: boolean; error?: string }> {
    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await resp.json()

      if (!resp.ok) {
        if (data.code === 'AUTH_DISABLED') {
          jwtEnabled.value = false
          return { success: false, error: '认证服务未启用' }
        }
        if (data.code === 'AUTH_FAILED') {
          return { success: false, error: '用户名或密码错误' }
        }
        return { success: false, error: data.error || '登录失败' }
      }

      token.value = data.access_token
      user.value = data.user
      jwtEnabled.value = true
      return { success: true }
    } catch {
      return { success: false, error: '网络连接失败' }
    }
  }

  /** Fetch current user info */
  async function fetchUser(): Promise<boolean> {
    if (!token.value) return false
    try {
      const resp = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${token.value}` },
      })
      if (!resp.ok) {
        // Token invalid or expired
        logout()
        return false
      }
      user.value = await resp.json()
      return true
    } catch {
      return false
    }
  }

  /** Logout: clear auth state and navigate to login page */
  function logout() {
    token.value = ''
    user.value = null
    router.push('/login')
  }

  /** Clear auth state (for route guard) */
  function clearAuth() {
    token.value = ''
    user.value = null
  }

  return {
    token,
    user,
    jwtEnabled,
    isAuthenticated,
    isAdmin,
    checkJwtStatus,
    login,
    fetchUser,
    logout,
    clearAuth,
  }
}, {
  persist: {
    key: 'configforge_auth',
    pick: ['token', 'user'],
  },
})
