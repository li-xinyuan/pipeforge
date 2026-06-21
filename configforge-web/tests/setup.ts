import { vi } from 'vitest'

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
