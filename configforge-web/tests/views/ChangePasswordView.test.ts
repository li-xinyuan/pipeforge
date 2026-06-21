import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ChangePasswordView from '../../src/views/ChangePasswordView.vue'

const mockPush = vi.fn()
const mockAuthStore = {
  token: 'test-token',
  mustChangePassword: true,
}

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
}))

vi.mock('../../src/stores/auth', () => ({
  useAuthStore: () => mockAuthStore,
}))

function mountComponent() {
  return mount(ChangePasswordView, {
    global: {
      stubs: {
        Transition: {
          template: '<div><slot /></div>',
        },
      },
    },
  })
}

describe('ChangePasswordView', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    mockPush.mockClear()
    mockAuthStore.mustChangePassword = true
  })

  it('renders change password form with old/new/confirm fields', () => {
    const wrapper = mountComponent()

    const inputs = wrapper.findAll('input')
    expect(inputs).toHaveLength(3)
    expect(inputs[0].attributes('type')).toBe('password')
    expect(inputs[0].attributes('placeholder')).toBe('请输入旧密码')
    expect(inputs[1].attributes('type')).toBe('password')
    expect(inputs[1].attributes('placeholder')).toBe('至少 6 个字符')
    expect(inputs[2].attributes('type')).toBe('password')
    expect(inputs[2].attributes('placeholder')).toBe('再次输入新密码')

    expect(wrapper.text()).toContain('旧密码')
    expect(wrapper.text()).toContain('新密码')
    expect(wrapper.text()).toContain('确认新密码')
    expect(wrapper.text()).toContain('确认修改')
  })

  it('shows error when passwords don\'t match', async () => {
    const wrapper = mountComponent()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('oldpass')
    await inputs[1].setValue('newpass123')
    await inputs[2].setValue('different123')

    await wrapper.find('form').trigger('submit')

    expect(wrapper.text()).toContain('两次输入的新密码不一致')
  })

  it('calls API to change password on submit', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    })
    vi.stubGlobal('fetch', mockFetch)

    const wrapper = mountComponent()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('oldpass')
    await inputs[1].setValue('newpass123')
    await inputs[2].setValue('newpass123')

    await wrapper.find('form').trigger('submit')
    await vi.waitFor(() => expect(mockFetch).toHaveBeenCalled())

    expect(mockFetch).toHaveBeenCalledWith('/api/auth/change-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token',
      },
      body: JSON.stringify({
        old_password: 'oldpass',
        new_password: 'newpass123',
      }),
    })
  })

  it('shows success message and redirects on success', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    })
    vi.stubGlobal('fetch', mockFetch)

    const wrapper = mountComponent()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('oldpass')
    await inputs[1].setValue('newpass123')
    await inputs[2].setValue('newpass123')

    await wrapper.find('form').trigger('submit')
    await vi.waitFor(() => expect(mockPush).toHaveBeenCalledWith('/'))

    expect(mockAuthStore.mustChangePassword).toBe(false)
  })

  it('shows error when old password is wrong (INVALID_PASSWORD)', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ code: 'INVALID_PASSWORD' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    const wrapper = mountComponent()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('wrongold')
    await inputs[1].setValue('newpass123')
    await inputs[2].setValue('newpass123')

    await wrapper.find('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.text()).toContain('旧密码错误'))
  })

  it('shows generic error on API failure', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: '服务器内部错误' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    const wrapper = mountComponent()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('oldpass')
    await inputs[1].setValue('newpass123')
    await inputs[2].setValue('newpass123')

    await wrapper.find('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.text()).toContain('服务器内部错误'))
  })

  it('shows network error on fetch failure', async () => {
    const mockFetch = vi.fn().mockRejectedValue(new Error('Network error'))
    vi.stubGlobal('fetch', mockFetch)

    const wrapper = mountComponent()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('oldpass')
    await inputs[1].setValue('newpass123')
    await inputs[2].setValue('newpass123')

    await wrapper.find('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.text()).toContain('网络连接失败'))
  })

  it('validates password length requirements', async () => {
    const wrapper = mountComponent()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('oldpass')
    await inputs[1].setValue('short')
    await inputs[2].setValue('short')

    await wrapper.find('form').trigger('submit')

    expect(wrapper.text()).toContain('新密码长度不能少于 6 个字符')
  })

  it('validates old password is required', async () => {
    const wrapper = mountComponent()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('')
    await inputs[1].setValue('newpass123')
    await inputs[2].setValue('newpass123')

    await wrapper.find('form').trigger('submit')

    expect(wrapper.text()).toContain('请输入旧密码')
  })

  it('disables submit while loading', async () => {
    let resolveFetch!: () => void
    const mockFetch = vi.fn().mockReturnValue(
      new Promise((resolve) => { resolveFetch = resolve }),
    )
    vi.stubGlobal('fetch', mockFetch)

    const wrapper = mountComponent()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('oldpass')
    await inputs[1].setValue('newpass123')
    await inputs[2].setValue('newpass123')

    await wrapper.find('form').trigger('submit')

    // Button should be disabled while loading
    const button = wrapper.find('button')
    expect(button.attributes('disabled')).toBeDefined()
    expect(wrapper.find('.change-password__spinner').exists()).toBe(true)

    // Resolve the fetch to finish
    resolveFetch()
    await vi.waitFor(() => {
      expect(wrapper.find('button').attributes('disabled')).toBeUndefined()
    })
  })
})
