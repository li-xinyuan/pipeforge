import { vi } from 'vitest'
import { config } from '@vue/test-utils'

// Mock IntersectionObserver for jsdom environment
if (typeof window !== 'undefined' && !window.IntersectionObserver) {
  class MockIntersectionObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() { return [] }
  }
  window.IntersectionObserver = MockIntersectionObserver as unknown as typeof IntersectionObserver
}

// Mock window.alert for happy-dom environment
if (typeof window !== 'undefined' && !window.alert) {
  window.alert = vi.fn()
}

// Mock auth store for all tests
vi.mock('../src/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    token: '',
    user: null,
    isAuthenticated: false,
    jwtEnabled: null,
    isAdmin: false,
    login: vi.fn(),
    logout: vi.fn(),
    fetchUser: vi.fn(),
    clearAuth: vi.fn(),
    checkJwtStatus: vi.fn(),
  })),
}))

// Mock router for all tests
const mockPush = vi.fn()
const mockReplace = vi.fn()
vi.mock('../src/router', () => ({
  default: {
    push: mockPush,
    replace: mockReplace,
    currentRoute: { value: { query: {}, path: '/' } },
  },
}))

// Register vue-i18n globally so all mounted components can use t()
import i18n from '../src/i18n'
config.global.plugins = [i18n]
// Force zh-CN locale for consistent test assertions (test environment's
// navigator.language may default to en-US, breaking Chinese string checks)
i18n.global.locale.value = 'zh-CN'

// Mock virtual:pwa-register (only available in production builds via vite-plugin-pwa)
vi.mock('virtual:pwa-register', () => ({
  registerSW: vi.fn(() => vi.fn()),
}))
