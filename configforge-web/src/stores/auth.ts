import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '../router'
import { ApiError, handleApiError, useApi } from '../composables/useApi'

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
    // Use raw fetch (not useApi) so a 401 probe response does not trigger
    // the global 401 handler that would clearAuth() + redirect to /login.
    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: '__probe__', password: '__probe__' }),
      })
      const data = await resp.json().catch(() => null) as { detail?: { code?: string } } | null
      if (resp.status === 400 && data?.detail?.code === 'AUTH_DISABLED') {
        jwtEnabled.value = false
        return false
      }
      // Any other response (401 AUTH_FAILED, 200, etc.) means JWT is enabled
      jwtEnabled.value = true
      return true
    } catch {
      // Network error — assume JWT is enabled to be safe (will be re-checked on login)
      jwtEnabled.value = true
      return true
    }
  }

  /** Login with username and password */
  async function login(username: string, password: string): Promise<{ success: boolean; error?: string }> {
    try {
      const api = useApi()
      const data = await api.requestOrThrow<{ access_token: string; user: AuthUser; code?: string }>('POST', '/api/auth/login', {
        username,
        password,
      })

      token.value = data.access_token
      user.value = data.user
      mustChangePassword.value = data.user.must_change_password || false
      jwtEnabled.value = true
      return { success: true }
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.code === 'AUTH_DISABLED') {
          jwtEnabled.value = false
          return { success: false, error: '认证服务未启用' }
        }
        if (e.code === 'AUTH_FAILED') {
          return { success: false, error: '用户名或密码错误' }
        }
        return { success: false, error: e.message || '登录失败' }
      }
      return { success: false, error: '网络连接失败' }
    }
  }

  /** Fetch current user info */
  async function fetchUser(): Promise<boolean> {
    if (!token.value) return false
    try {
      const api = useApi()
      const data = await api.requestOrThrow<AuthUser>('GET', '/api/auth/me')
      user.value = data
      return true
    } catch (e) {
      if (e instanceof ApiError) {
        handleApiError(e)
      }
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
  persist: {
    key: 'configforge_auth',
    paths: ['token', 'user', 'mustChangePassword'],
  },
})
