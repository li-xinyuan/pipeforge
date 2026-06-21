import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ExecutionHistoryView from '../../src/views/ExecutionHistoryView.vue'
import type { ExecutionItem } from '../../src/composables/useApi'

// ── Mock API ──
const mockGetExecutions = vi.fn()
const mockDeleteExecution = vi.fn()

vi.mock('../../src/composables/useApi', () => ({
  useApi: () => ({
    getExecutions: mockGetExecutions,
    deleteExecution: mockDeleteExecution,
  }),
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

const sampleExecutions: ExecutionItem[] = [
  {
    id: 'exec-1',
    config_id: 'cfg-1',
    config_version: 1,
    scene_name: 'Daily Report',
    status: 'success',
    started_at: '2025-06-01T08:00:00Z',
    finished_at: '2025-06-01T08:00:05Z',
    duration_ms: 5000,
    inputs_summary: [{ name: 'db1', plugin: 'database' }],
    processors_summary: [{ plugin: 'sql', name: 'Transform' }],
    output_type: 'excel',
    checks_summary: [],
    error_message: null,
    output_file_name: 'report.xlsx',
    diagnosis: null,
  },
  {
    id: 'exec-2',
    config_id: 'adhoc',
    config_version: null,
    scene_name: 'Ad-hoc Query',
    status: 'failed',
    started_at: '2025-06-01T09:00:00Z',
    finished_at: '2025-06-01T09:00:02Z',
    duration_ms: 2000,
    inputs_summary: [],
    processors_summary: [],
    output_type: '',
    checks_summary: [],
    error_message: 'Connection refused',
    output_file_name: null,
    diagnosis: {
      cause: 'Database unreachable',
      suggestions: ['Check connection string'],
      severity: 'error',
    },
  },
  {
    id: 'exec-3',
    config_id: 'cfg-2',
    config_version: 2,
    scene_name: 'Failed with diagnosis',
    status: 'failed',
    started_at: '2025-06-01T10:00:00Z',
    finished_at: '2025-06-01T10:00:03Z',
    duration_ms: 3000,
    inputs_summary: [],
    processors_summary: [],
    output_type: '',
    checks_summary: [],
    error_message: 'SQL syntax error',
    output_file_name: null,
    diagnosis: {
      cause: 'Invalid SQL syntax',
      suggestions: ['Review SQL query'],
      severity: 'warning',
    },
  },
]

// Naive-ui component names lack the "N" prefix (e.g. NButton.name === "Button").
// VTU matches stub keys by component name, so we use "Button", "Tag", etc.
const stubs = {
  AppNavBar: true,
  DiagnosisPanel: true,
  Button: { template: '<button><slot /></button>' },
  Tag: { template: '<span><slot /></span>' },
  Modal: { template: '<div class="modal-stub" v-if="show"><slot /></div>', props: ['show'] },
  Pagination: { template: '<div class="pagination-stub"><slot /></div>' },
  Tabs: { template: '<div class="tabs-stub"><slot /></div>' },
  Tab: { template: '<div class="tab-stub"><slot /></div>' },
}

async function makeWrapper() {
  mockGetExecutions.mockResolvedValue({
    items: sampleExecutions,
    total: sampleExecutions.length,
  })

  const wrapper = mount(ExecutionHistoryView, { global: { stubs } })
  await flushPromises()
  return wrapper
}

describe('ExecutionHistoryView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page title', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('执行历史')
  })

  it('renders the refresh button', async () => {
    const wrapper = await makeWrapper()
    const buttons = wrapper.findAll('button')
    const refreshBtn = buttons.find(b => b.text().includes('刷新'))
    expect(refreshBtn).toBeDefined()
  })

  it('renders execution list with scene names', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('Daily Report')
    expect(wrapper.text()).toContain('Ad-hoc Query')
    expect(wrapper.text()).toContain('Failed with diagnosis')
  })

  it('renders status indicators (success/failure)', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('成功')
    const failCount = wrapper.text().split('失败').length - 1
    expect(failCount).toBeGreaterThanOrEqual(2)
  })

  it('renders AI diagnosis tag for executions with diagnosis', async () => {
    const wrapper = await makeWrapper()
    const diagCount = wrapper.text().split('AI 诊断').length - 1
    expect(diagCount).toBeGreaterThanOrEqual(2)
  })

  it('renders detail button for each execution', async () => {
    const wrapper = await makeWrapper()
    const buttons = wrapper.findAll('button')
    const detailBtns = buttons.filter(b => b.text() === '详情')
    expect(detailBtns.length).toBe(3)
  })

  it('renders download button only for executions with output file', async () => {
    const wrapper = await makeWrapper()
    const buttons = wrapper.findAll('button')
    const downloadBtns = buttons.filter(b => b.text() === '下载')
    expect(downloadBtns.length).toBe(1)
  })

  it('renders delete button for each execution', async () => {
    const wrapper = await makeWrapper()
    const buttons = wrapper.findAll('button')
    const deleteBtns = buttons.filter(b => b.text() === '删除')
    expect(deleteBtns.length).toBe(3)
  })

  it('shows empty state when no executions exist', async () => {
    mockGetExecutions.mockResolvedValue({ items: [], total: 0 })
    const wrapper = mount(ExecutionHistoryView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('暂无执行记录')
  })

  it('shows loading state', async () => {
    mockGetExecutions.mockReturnValue(new Promise(() => {}))
    const wrapper = mount(ExecutionHistoryView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('加载中')
  })

  it('loads executions on mount', async () => {
    await makeWrapper()
    expect(mockGetExecutions).toHaveBeenCalledWith(1, 20)
  })

  it('renders tabs for records and trends', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('执行记录')
    expect(wrapper.text()).toContain('诊断趋势')
  })

  it('renders duration for each execution', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('5000ms')
    expect(wrapper.text()).toContain('2000ms')
    expect(wrapper.text()).toContain('3000ms')
  })

  it('opens detail view when detail button is clicked', async () => {
    const wrapper = await makeWrapper()
    const buttons = wrapper.findAll('button')
    const detailBtns = buttons.filter(b => b.text() === '详情')
    // Click detail for the second execution (exec-2)
    await detailBtns[1].trigger('click')
    await flushPromises()
    // The modal should be visible with detail content
    expect(wrapper.find('.modal-stub').exists()).toBe(true)
    expect(wrapper.text()).toContain('执行 ID')
  })

  it('calls window.open when download button is clicked', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    const wrapper = await makeWrapper()
    const buttons = wrapper.findAll('button')
    const downloadBtn = buttons.find(b => b.text() === '下载')
    expect(downloadBtn).toBeDefined()
    await downloadBtn!.trigger('click')
    expect(openSpy).toHaveBeenCalledWith('/api/executions/exec-1/download', '_blank')
    openSpy.mockRestore()
  })

  it('renders pagination when total exceeds page size', async () => {
    mockGetExecutions.mockResolvedValue({
      items: sampleExecutions,
      total: 50,
    })
    const wrapper = mount(ExecutionHistoryView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('共 50 条')
  })

  it('does not render pagination when total is within page size', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).not.toContain('共 3 条')
  })
})
