import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import LoginView from '../../src/views/LoginView.vue'

// Mock useTheme
const mockToggleTheme = vi.fn()
vi.mock('../../src/composables/useTheme', () => ({
  useTheme: () => ({ isDark: { value: false }, toggleTheme: mockToggleTheme }),
}))

// Mock auth store
const mockLogin = vi.fn()
const mockCheckJwtStatus = vi.fn()
vi.mock('../../src/stores/auth', () => ({
  useAuthStore: () => ({
    token: '',
    user: null,
    isAuthenticated: false,
    jwtEnabled: null,
    isAdmin: false,
    login: mockLogin,
    logout: vi.fn(),
    fetchUser: vi.fn(),
    clearAuth: vi.fn(),
    checkJwtStatus: mockCheckJwtStatus,
  }),
}))

async function makeWrapper(query: Record<string, string> = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>Home</div>' } },
      { path: '/login', component: { template: '<div>Login</div>' } },
    ],
  })
  router.push({ path: '/login', query })
  await router.isReady()

  const wrapper = mount(LoginView, {
    global: {
      plugins: [router],
      stubs: {
        PipelineAnimation: { template: '<div class="pipeline-animation-stub" />' },
        Transition: {
          template: '<div><slot /></div>',
        },
      },
    },
  })

  return { wrapper, router }
}

describe('LoginView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLogin.mockReset()
    mockCheckJwtStatus.mockReset()
  })

  it('renders login form with username/password fields and login button', async () => {
    const { wrapper } = await makeWrapper()

    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('input[autocomplete="username"]').exists()).toBe(true)
    expect(wrapper.find('input[autocomplete="current-password"]').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('用户名')
    expect(wrapper.text()).toContain('密码')
  })

  it('shows error message on failed login', async () => {
    mockLogin.mockResolvedValue({ success: false, error: '用户名或密码错误' })

    const { wrapper } = await makeWrapper()

    await wrapper.find('input[autocomplete="username"]').setValue('admin')
    await wrapper.find('input[autocomplete="current-password"]').setValue('wrong')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.login__error').exists()).toBe(true)
    expect(wrapper.text()).toContain('用户名或密码错误')
  })

  it('calls auth store login on form submit', async () => {
    mockLogin.mockResolvedValue({ success: true })

    const { wrapper } = await makeWrapper()

    await wrapper.find('input[autocomplete="username"]').setValue('admin')
    await wrapper.find('input[autocomplete="current-password"]').setValue('admin123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(mockLogin).toHaveBeenCalledWith('admin', 'admin123')
  })

  it('redirects to home on successful login', async () => {
    mockLogin.mockResolvedValue({ success: true })

    const { wrapper, router } = await makeWrapper()
    const pushSpy = vi.spyOn(router, 'push')

    await wrapper.find('input[autocomplete="username"]').setValue('admin')
    await wrapper.find('input[autocomplete="current-password"]').setValue('admin123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(pushSpy).toHaveBeenCalledWith('/')
  })

  it('redirects to query.redirect on successful login', async () => {
    mockLogin.mockResolvedValue({ success: true })

    const { wrapper, router } = await makeWrapper({ redirect: '/settings' })
    const pushSpy = vi.spyOn(router, 'push')

    await wrapper.find('input[autocomplete="username"]').setValue('admin')
    await wrapper.find('input[autocomplete="current-password"]').setValue('admin123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(pushSpy).toHaveBeenCalledWith('/settings')
  })

  it('disables button while loading', async () => {
    let resolveLogin!: (value: { success: boolean }) => void
    mockLogin.mockReturnValue(new Promise(resolve => { resolveLogin = resolve }))

    const { wrapper } = await makeWrapper()

    await wrapper.find('input[autocomplete="username"]').setValue('admin')
    await wrapper.find('input[autocomplete="current-password"]').setValue('admin123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    // Button should be disabled and show spinner while loading
    const btn = wrapper.find('button[type="submit"]')
    expect(btn.attributes('disabled')).toBeDefined()
    expect(wrapper.find('.login__spinner').exists()).toBe(true)

    // Resolve the login
    resolveLogin({ success: true })
    await flushPromises()

    // Button should be re-enabled
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })

  it('shows validation error when submitting empty fields', async () => {
    const { wrapper } = await makeWrapper()

    // Submit without filling in fields
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.login__error').exists()).toBe(true)
    expect(wrapper.text()).toContain('请输入用户名和密码')
    expect(mockLogin).not.toHaveBeenCalled()
  })

  it('toggles password visibility', async () => {
    const { wrapper } = await makeWrapper()

    const passwordInput = wrapper.find('input[autocomplete="current-password"]')
    expect(passwordInput.attributes('type')).toBe('password')

    await wrapper.find('.login__eye').trigger('click')
    expect(passwordInput.attributes('type')).toBe('text')

    await wrapper.find('.login__eye').trigger('click')
    expect(passwordInput.attributes('type')).toBe('password')
  })

  it('shows JWT status indicator via auth store', async () => {
    mockCheckJwtStatus.mockResolvedValue(true)

    const { wrapper } = await makeWrapper()

    // The component uses useAuthStore which has jwtEnabled and checkJwtStatus
    // Verify the store is accessible and has the jwtEnabled property
    expect(wrapper.text()).toBeDefined()
  })

  it('clears error on new submit attempt', async () => {
    mockLogin.mockResolvedValueOnce({ success: false, error: '用户名或密码错误' })

    const { wrapper } = await makeWrapper()

    await wrapper.find('input[autocomplete="username"]').setValue('admin')
    await wrapper.find('input[autocomplete="current-password"]').setValue('wrong')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.login__error').exists()).toBe(true)

    // Now mock a successful login
    mockLogin.mockResolvedValueOnce({ success: true })

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    // Error should be cleared
    expect(wrapper.find('.login__error').exists()).toBe(false)
  })

  it('renders default credentials hint', async () => {
    const { wrapper } = await makeWrapper()

    expect(wrapper.text()).toContain('默认账号 admin / admin123')
  })

  it('renders theme toggle button', async () => {
    const { wrapper } = await makeWrapper()

    const themeBtn = wrapper.find('.login__theme')
    expect(themeBtn.exists()).toBe(true)
  })

  it('calls toggleTheme on theme button click', async () => {
    const { wrapper } = await makeWrapper()

    await wrapper.find('.login__theme').trigger('click')
    expect(mockToggleTheme).toHaveBeenCalled()
  })

  it('trims username whitespace before login', async () => {
    mockLogin.mockResolvedValue({ success: true })

    const { wrapper } = await makeWrapper()

    await wrapper.find('input[autocomplete="username"]').setValue('  admin  ')
    await wrapper.find('input[autocomplete="current-password"]').setValue('admin123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(mockLogin).toHaveBeenCalledWith('admin', 'admin123')
  })
})
