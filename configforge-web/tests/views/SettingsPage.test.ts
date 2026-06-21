import { describe, it, expect, vi, beforeEach } from 'vitest'
import { shallowMount, flushPromises } from '@vue/test-utils'
import SettingsPage from '../../src/views/SettingsPage.vue'

// ── Mock composables ──
const mockGetAiSettings = vi.fn()
const mockUpdateAiSettings = vi.fn()
const mockTestAiConnection = vi.fn()

// Source imports { useAiApi } from '../composables/useWizardApi'
vi.mock('../../src/composables/useWizardApi', () => ({
  useAiApi: () => ({
    getAiSettings: mockGetAiSettings,
    updateAiSettings: mockUpdateAiSettings,
    testAiConnection: mockTestAiConnection,
  }),
}))

const mockSmtpRequest = vi.fn()
vi.mock('../../src/composables/useApi', () => ({
  useApi: () => ({
    request: mockSmtpRequest,
  }),
}))

// ── Mock auth store (admin by default for full tab visibility) ──
const mockAuthStore = {
  token: 'test-token',
  user: { id: '1', username: 'admin', role: 'admin', created_at: '' },
  isAuthenticated: true,
  jwtEnabled: true,
  isAdmin: true,
  canEdit: true,
  canAdmin: true,
  login: vi.fn(),
  logout: vi.fn(),
  fetchUser: vi.fn(),
  clearAuth: vi.fn(),
  checkJwtStatus: vi.fn(),
}
vi.mock('../../src/stores/auth', () => ({
  useAuthStore: () => mockAuthStore,
}))

// ── Mock naive-ui useMessage ──
vi.mock('naive-ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('naive-ui')>()
  return {
    ...actual,
    useMessage: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
  }
})

async function makeWrapper(mobile = false) {
  vi.spyOn(window, 'innerWidth', 'get').mockReturnValue(mobile ? 500 : 1024)

  mockGetAiSettings.mockResolvedValue({
    provider: 'openai',
    api_key: 'sk-****masked',
    base_url: '',
    model: '',
    temperature: 0.7,
    max_tokens: 4096,
    enabled: true,
  })
  mockSmtpRequest.mockResolvedValue({
    host: 'smtp.test.com',
    port: 587,
    user: 'test@test.com',
    sender: '',
    use_tls: true,
    password: '****',
  })

  // shallowMount auto-stubs all child components; renderStubDefaultSlot
  // renders slot content so text assertions work.
  // Naive-ui component names lack the "N" prefix (e.g. NTabs.name === "Tabs"),
  // so stub tags are <tabs-stub>, <tab-pane-stub>, etc.
  const wrapper = shallowMount(SettingsPage, {
    global: {
      renderStubDefaultSlot: true,
      stubs: {
        AppNavBar: true,
        ConnectionManager: true,
      },
    },
  })
  await flushPromises()
  return wrapper
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAuthStore.canAdmin = true
  })

  it('renders the page title', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.find('.settings__title').text()).toBe('设置')
  })

  it('renders desktop tabs layout on desktop', async () => {
    const wrapper = await makeWrapper(false)
    expect(wrapper.find('tabs-stub').exists()).toBe(true)
    expect(wrapper.find('collapse-stub').exists()).toBe(false)
  })

  it('renders mobile collapse layout on mobile', async () => {
    const wrapper = await makeWrapper(true)
    expect(wrapper.find('collapse-stub').exists()).toBe(true)
    expect(wrapper.find('tabs-stub').exists()).toBe(false)
  })

  it('renders AI settings tab on desktop', async () => {
    const wrapper = await makeWrapper(false)
    const aiTab = wrapper.find('tab-pane-stub[name="ai"]')
    expect(aiTab.exists()).toBe(true)
    expect(aiTab.attributes('tab')).toBe('AI 模型')
  })

  it('renders database connections tab on desktop', async () => {
    const wrapper = await makeWrapper(false)
    const dbTab = wrapper.find('tab-pane-stub[name="database"]')
    expect(dbTab.exists()).toBe(true)
    expect(dbTab.attributes('tab')).toBe('数据库连接')
  })

  it('renders SMTP notifications tab on desktop', async () => {
    const wrapper = await makeWrapper(false)
    const smtpTab = wrapper.find('tab-pane-stub[name="smtp"]')
    expect(smtpTab.exists()).toBe(true)
    expect(smtpTab.attributes('tab')).toBe('邮件推送')
  })

  it('renders AI section on mobile using NCollapseItem', async () => {
    const wrapper = await makeWrapper(true)
    const aiItem = wrapper.find('collapse-item-stub[name="ai"]')
    expect(aiItem.exists()).toBe(true)
    expect(aiItem.attributes('title')).toBe('AI 模型')
  })

  it('renders database section on mobile using NCollapseItem', async () => {
    const wrapper = await makeWrapper(true)
    const dbItem = wrapper.find('collapse-item-stub[name="database"]')
    expect(dbItem.exists()).toBe(true)
    expect(dbItem.attributes('title')).toBe('数据库连接')
  })

  it('renders SMTP section on mobile using NCollapseItem', async () => {
    const wrapper = await makeWrapper(true)
    const smtpItem = wrapper.find('collapse-item-stub[name="smtp"]')
    expect(smtpItem.exists()).toBe(true)
    expect(smtpItem.attributes('title')).toBe('邮件推送')
  })

  it('renders AI settings form fields', async () => {
    const wrapper = await makeWrapper(false)
    const text = wrapper.text()
    expect(text).toContain('启用 AI')
    expect(text).toContain('提供商')
    expect(text).toContain('模型')
    expect(text).toContain('API Key')
    expect(text).toContain('Base URL')
    expect(text).toContain('Temperature')
    expect(text).toContain('Max Tokens')
  })

  it('renders SMTP settings form fields', async () => {
    const wrapper = await makeWrapper(false)
    const text = wrapper.text()
    expect(text).toContain('SMTP 服务器')
    expect(text).toContain('端口')
    expect(text).toContain('用户名')
    expect(text).toContain('密码 / 授权码')
    expect(text).toContain('发件人地址')
    expect(text).toContain('启用 TLS')
  })

  it('renders action buttons (test + save)', async () => {
    const wrapper = await makeWrapper(false)
    const text = wrapper.text()
    // AI section has test + save, SMTP section has test + save
    expect(text.split('测试连接').length - 1).toBeGreaterThanOrEqual(2)
    expect(text.split('保存设置').length - 1).toBeGreaterThanOrEqual(2)
  })

  it('renders ConnectionManager in the database tab', async () => {
    const wrapper = await makeWrapper(false)
    expect(wrapper.find('connection-manager-stub').exists()).toBe(true)
  })

  it('loads AI settings on mount', async () => {
    await makeWrapper()
    expect(mockGetAiSettings).toHaveBeenCalled()
  })

  it('loads SMTP settings on mount', async () => {
    await makeWrapper()
    expect(mockSmtpRequest).toHaveBeenCalledWith('GET', '/api/notifications/smtp-settings')
  })

  it('hides AI and database tabs when user is not admin', async () => {
    mockAuthStore.canAdmin = false
    const wrapper = await makeWrapper(false)
    expect(wrapper.find('tab-pane-stub[name="ai"]').exists()).toBe(false)
    expect(wrapper.find('tab-pane-stub[name="database"]').exists()).toBe(false)
  })

  it('always shows SMTP tab regardless of admin status', async () => {
    mockAuthStore.canAdmin = false
    const wrapper = await makeWrapper(false)
    expect(wrapper.find('tab-pane-stub[name="smtp"]').exists()).toBe(true)
  })
})
