import { createDiscreteApi } from 'naive-ui'
import { ApiError, handleApiError } from './useApi'
import { useAuthStore } from '../stores/auth'
import router from '../router'

const { notification } = createDiscreteApi(['notification'])

/**
 * Composable for unified API error handling with Naive UI notifications.
 *
 * Usage:
 *   const { showError } = useApiError()
 *   try { ... } catch (e) { showError(e) }
 */
export function useApiError() {
  function showError(error: unknown, fallbackMessage = '操作失败') {
    if (error instanceof ApiError) {
      switch (error.status) {
        case 401:
          useAuthStore().clearAuth()
          router.push('/login')
          notification.warning({ title: '登录已过期', content: '请重新登录', duration: 3000 })
          break
        case 403:
          notification.warning({ title: '权限不足', content: error.message, duration: 3000 })
          break
        case 500:
          notification.error({ title: '服务器错误', content: error.message, duration: 5000 })
          break
        default:
          handleApiError(error)
          break
      }
    } else {
      notification.error({ title: fallbackMessage, content: String(error), duration: 3000 })
    }
  }

  return { showError }
}
