import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import SchedulesPage from '../../src/views/SchedulesPage.vue'
import type { ScheduleItem } from '../../src/composables/useApi'

// ── Mock API ──
const mockGetSchedules = vi.fn()
const mockGetConfigs = vi.fn()
const mockCreateSchedule = vi.fn()
const mockUpdateSchedule = vi.fn()
const mockToggleSchedule = vi.fn()
const mockDeleteSchedule = vi.fn()

vi.mock('../../src/composables/useApi', () => ({
  useApi: () => ({
    getSchedules: mockGetSchedules,
    getConfigs: mockGetConfigs,
    createSchedule: mockCreateSchedule,
    updateSchedule: mockUpdateSchedule,
    toggleSchedule: mockToggleSchedule,
    deleteSchedule: mockDeleteSchedule,
  }),
}))

// ── Mock auth store ──
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

// ── Mock naive-ui dialog and message ──
vi.mock('naive-ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('naive-ui')>()
  return {
    ...actual,
    useDialog: () => ({ warning: vi.fn() }),
    useMessage: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
  }
})

// ── Mock formatDateTime ──
vi.mock('../../src/utils/format', () => ({
  formatDateTime: (d: string) => d || '',
}))

const sampleSchedules: ScheduleItem[] = [
  {
    id: 'sched-1',
    config_id: 'cfg-1',
    config_name: 'Test Config A',
    cron_expression: '0 8 * * *',
    enabled: true,
    description: 'Daily morning run',
    created_at: '2025-01-01T00:00:00Z',
    last_run_at: '2025-06-01T08:00:00Z',
    last_run_status: 'success',
    next_run_time: '2025-06-02T08:00:00Z',
  },
  {
    id: 'sched-2',
    config_id: 'cfg-2',
    config_name: 'Test Config B',
    cron_expression: '0 */2 * * *',
    enabled: false,
    description: 'Every 2 hours (disabled)',
    created_at: '2025-02-01T00:00:00Z',
    last_run_at: '2025-05-15T10:00:00Z',
    last_run_status: 'failed',
    next_run_time: null,
  },
]

const sampleConfigResponse = {
  items: [
    { id: 'cfg-1', scene_name: 'Test Config A', inputs: [{ plugin: 'database' }] },
    { id: 'cfg-2', scene_name: 'Test Config B', inputs: [{ plugin: 'excel' }] },
  ],
}

const stubs = {
  AppNavBar: true,
  NButton: { template: '<button><slot /></button>' },
  NTag: { template: '<span><slot /></span>' },
  NModal: { template: '<div class="n-modal-stub" v-if="show"><slot /><slot name="footer" /></div>', props: ['show'] },
  NSelect: true,
  NInput: true,
}

async function makeWrapper() {
  mockGetSchedules.mockResolvedValue(sampleSchedules)
  mockGetConfigs.mockResolvedValue(sampleConfigResponse)

  const wrapper = mount(SchedulesPage, { global: { stubs } })
  await flushPromises()
  return wrapper
}

describe('SchedulesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page title', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('定时任务')
  })

  it('renders the create button when user can edit', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('新建定时任务')
  })

  it('hides the create button when user cannot edit', async () => {
    mockAuthStore.canEdit = false
    const wrapper = await makeWrapper()
    expect(wrapper.text()).not.toContain('新建定时任务')
    mockAuthStore.canEdit = true
  })

  it('renders schedule cards with config names', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('Test Config A')
    expect(wrapper.text()).toContain('Test Config B')
  })

  it('renders cron expressions in schedule cards', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('0 8 * * *')
    expect(wrapper.text()).toContain('0 */2 * * *')
  })

  it('renders enabled/disabled status tags', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('已启用')
    expect(wrapper.text()).toContain('已禁用')
  })

  it('renders last run status tags', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('上次: 成功')
    expect(wrapper.text()).toContain('上次: 失败')
  })

  it('renders schedule descriptions', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('Daily morning run')
    expect(wrapper.text()).toContain('Every 2 hours (disabled)')
  })

  it('renders toggle buttons (enable/disable) for each schedule', async () => {
    const wrapper = await makeWrapper()
    const buttons = wrapper.findAll('button')
    const buttonTexts = buttons.map(b => b.text())
    expect(buttonTexts).toContain('禁用')
    expect(buttonTexts).toContain('启用')
  })

  it('renders edit and delete buttons for each schedule', async () => {
    const wrapper = await makeWrapper()
    const buttons = wrapper.findAll('button')
    const buttonTexts = buttons.map(b => b.text())
    expect(buttonTexts.filter(t => t === '编辑').length).toBe(2)
    expect(buttonTexts.filter(t => t === '删除').length).toBe(2)
  })

  it('shows empty state when no schedules exist', async () => {
    mockGetSchedules.mockResolvedValue([])
    mockGetConfigs.mockResolvedValue({ items: [] })
    const wrapper = mount(SchedulesPage, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('暂无定时任务')
  })

  it('shows loading state', async () => {
    mockGetSchedules.mockReturnValue(new Promise(() => {}))
    mockGetConfigs.mockResolvedValue({ items: [] })
    const wrapper = mount(SchedulesPage, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('加载中')
  })

  it('loads schedules on mount', async () => {
    await makeWrapper()
    expect(mockGetSchedules).toHaveBeenCalled()
  })

  it('calls toggleSchedule when toggle button is clicked', async () => {
    mockToggleSchedule.mockResolvedValue({})
    const wrapper = await makeWrapper()
    const buttons = wrapper.findAll('button')
    const disableBtn = buttons.find(b => b.text() === '禁用')
    expect(disableBtn).toBeDefined()
    await disableBtn!.trigger('click')
    await flushPromises()
    expect(mockToggleSchedule).toHaveBeenCalledWith('sched-1')
  })

  it('renders next run time for schedules that have one', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('下次运行')
  })

  it('renders last run time for schedules that have one', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('上次运行')
  })
})
