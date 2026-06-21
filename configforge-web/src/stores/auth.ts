import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '../router'
import { ApiError, handleApiError } from '../composables/useApi'

export interface AuthUser {
  id: string
  username: string
  role: string
  created_at: string
  must_change_password?: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>('')
  const user = ref<AuthUser | null>(null)
  const jwtEnabled = ref<boolean | null>(null) // null = unknown (not checked yet)
  const mustChangePassword = ref(false)

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const canEdit = computed(() => user.value?.role === 'admin' || user.value?.role === 'editor')
  const canAdmin = computed(() => user.value?.role === 'admin')
  const needChangePassword = computed(() => mustChangePassword.value)

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
      mustChangePassword.value = data.user.must_change_password || false
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
      if (resp.status === 401) {
        handleApiError(new ApiError('登录已过期，请重新登录', 'AUTH_FAILED', 401))
        return false
      }
      if (resp.status === 403) {
        handleApiError(new ApiError('权限不足', 'FORBIDDEN', 403))
        return false
      }
      if (!resp.ok) {
        handleApiError(new ApiError(`请求失败 (${resp.status})`, 'API_ERROR', resp.status))
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
    mustChangePassword,
    isAuthenticated,
    isAdmin,
    canEdit,
    canAdmin,
    needChangePassword,
    checkJwtStatus,
    login,
    fetchUser,
    logout,
    clearAuth,
  }
}, {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- pinia-plugin-persistedstate pick type mismatch
  persist: {
    key: 'configforge_auth',
    pick: ['token', 'user', 'mustChangePassword'],
  } as any,
})
