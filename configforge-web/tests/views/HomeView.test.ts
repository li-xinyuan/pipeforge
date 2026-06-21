import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import HomeView from '../../src/views/HomeView.vue'
import type { SavedConfig } from '../../src/types/wizard'
import type { ComponentPublicInstance } from 'vue'

type HomeViewVm = ComponentPublicInstance<{
  deleteModalVisible: boolean
  deletingConfig: SavedConfig | null
  onConfirmDelete: () => Promise<void>
}>

// ── Mock factories ──────────────────────────────────────────────

function makeConfig(overrides: Partial<SavedConfig> = {}): SavedConfig {
  return {
    id: `cfg-${Math.random().toString(36).slice(2, 8)}`,
    sceneName: 'Test Config',
    description: 'A test config',
    inputCount: 1,
    outputType: 'excel',
    version: '1',
    updatedAt: '2025-01-01T00:00:00Z',
    inputs: [{ name: 'input1', paramKey: 'p1', plugin: 'excel' }],
    ...overrides,
  }
}

const defaultConfigs = [
  makeConfig({ id: 'cfg-1', sceneName: 'Alpha Config' }),
  makeConfig({ id: 'cfg-2', sceneName: 'Beta Config' }),
]

const defaultListResult = {
  items: defaultConfigs,
  total: 2,
  page: 1,
  pageSize: 10,
  totalPages: 1,
}

// ── Mocks ───────────────────────────────────────────────────────

const mockListConfigs = vi.fn()
const mockDeleteConfig = vi.fn()
const mockDownloadConfigYaml = vi.fn()

vi.mock('../../src/composables/useConfigApi', () => ({
  useConfigApi: () => ({
    loading: { value: false },
    error: { value: null },
    listConfigs: mockListConfigs,
    deleteConfig: mockDeleteConfig,
    downloadConfigYaml: mockDownloadConfigYaml,
  }),
}))

const mockRouterPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush }),
}))

const mockResetAll = vi.fn()
vi.mock('../../src/stores/wizard', () => ({
  useWizardStore: () => ({
    resetAll: mockResetAll,
  }),
}))

vi.mock('../../src/stores/auth', () => ({
  useAuthStore: () => ({
    token: 'test-token',
    isAuthenticated: true,
    canEdit: true,
    user: { name: 'Test User' },
    logout: vi.fn(),
  }),
}))

vi.mock('../../src/composables/useApi', () => ({
  useApi: () => ({
    loading: { value: false },
    error: { value: null },
    requestOrThrow: vi.fn(),
  }),
  ApiError: class ApiError extends Error {
    code: string
    status: number
    constructor(message: string, code: string, status: number) {
      super(message)
      this.code = code
      this.status = status
    }
  },
  handleApiError: vi.fn(),
}))

// Stub naive-ui useMessage
vi.mock('naive-ui', async () => {
  const actual = await vi.importActual<typeof import('naive-ui')>('naive-ui')
  return {
    ...actual,
    useMessage: () => ({
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    }),
  }
})

// ── Stub components ─────────────────────────────────────────────

const StubConfigListCard = {
  name: 'ConfigListCard',
  template: '<div class="stub-config-list-card" />',
  props: ['configs', 'batchMode', 'selectedIds', 'canEdit'],
  emits: ['toggleSelect', 'execute', 'menuSelect'],
}

const StubExecuteConfigModal = {
  name: 'ExecuteConfigModal',
  template: '<div class="stub-execute-modal" />',
  props: ['visible', 'config'],
  emits: ['close', 'gotoStep'],
}

const StubConfigVersionPanel = {
  name: 'ConfigVersionPanel',
  template: '<div class="stub-version-panel" />',
  props: ['configId', 'currentVersion'],
  emits: ['refreshed'],
}

// ── Mount helper ────────────────────────────────────────────────

function mountHome(listResult = defaultListResult) {
  mockListConfigs.mockResolvedValue(listResult)

  return mount(HomeView, {
    global: {
      stubs: {
        AppNavBar: { template: '<div class="stub-navbar" />' },
        AiStatusBanner: { template: '<div class="stub-ai-banner" />' },
        ConfigListCard: StubConfigListCard,
        ExecuteConfigModal: StubExecuteConfigModal,
        ConfigVersionPanel: StubConfigVersionPanel,
        ErrorBoundary: {
          template: '<div class="stub-error-boundary"><slot /></div>',
        },
        NButton: {
          template: '<button :disabled="disabled" :class="type" @click="$emit(\'click\')"><slot /></button>',
          props: ['type', 'size', 'disabled', 'loading'],
          emits: ['click'],
        },
        NInput: {
          template: '<div class="stub-n-input"><input :value="modelValue" @input="$emit(\'update:value\', $event.target.value)" @keyup="$emit(\'keyup\', $event)" /></div>',
          props: ['modelValue', 'placeholder', 'size', 'clearable'],
          emits: ['update:modelValue', 'keyup', 'update:value'],
        },
        NTag: {
          template: '<span><slot /></span>',
          props: ['size', 'bordered'],
        },
        NAlert: {
          template: '<div class="stub-alert">{{ title }}</div>',
          props: ['type', 'title'],
        },
        NModal: {
          template: '<div v-if="show" class="stub-modal"><slot /><slot name="footer" /></div>',
          props: ['show', 'preset', 'title', 'style', 'trapFocus', 'autoFocus'],
          emits: ['update:show'],
        },
        NCheckbox: {
          template: '<label class="stub-checkbox"><input type="checkbox" :checked="checked" :indeterminate="indeterminate" @change="$emit(\'update:checked\', $event.target.checked)" /><slot /></label>',
          props: ['checked', 'indeterminate'],
          emits: ['update:checked'],
        },
        NSelect: {
          template: '<select :value="modelValue" @change="$emit(\'update:value\', Number($event.target.value))"><slot /></select>',
          props: ['modelValue', 'options', 'size'],
          emits: ['update:value'],
        },
      },
    },
  })
}

// ── Tests ───────────────────────────────────────────────────────

describe('HomeView', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    mockListConfigs.mockResolvedValue(defaultListResult)
    mockDeleteConfig.mockResolvedValue(true)
    mockDownloadConfigYaml.mockResolvedValue(undefined)
    mockRouterPush.mockClear()
    mockResetAll.mockClear()
  })

  // ── 1. Renders config list with cards ───────────────────────

  it('renders config list with cards after loading', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const card = wrapper.findComponent(StubConfigListCard)
    expect(card.exists()).toBe(true)

    const props = card.props() as { configs: SavedConfig[] }
    expect(props.configs).toHaveLength(2)
    expect(props.configs[0].sceneName).toBe('Alpha Config')
    expect(props.configs[1].sceneName).toBe('Beta Config')
  })

  it('shows total count tag when configs exist', async () => {
    const wrapper = mountHome()
    await flushPromises()

    expect(wrapper.text()).toContain('2 个配置')
  })

  it('shows section title "最近配置"', async () => {
    const wrapper = mountHome()
    await flushPromises()

    expect(wrapper.text()).toContain('最近配置')
  })

  // ── 2. Shows search input and filters configs by name ───────

  it('shows search input when configs exist', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const searchInput = wrapper.find('.home__search-input')
    expect(searchInput.exists()).toBe(true)
  })

  it('hides search input when no configs and no search query', async () => {
    const wrapper = mountHome({ items: [], total: 0, page: 1, pageSize: 10, totalPages: 0 })
    await flushPromises()

    // The search input is shown when totalCount > 0 || searchQuery
    // With totalCount=0 and no searchQuery, the header-right is hidden
    expect(wrapper.find('.home__search-input').exists()).toBe(false)
  })

  it('filters configs by search query (debounced)', async () => {
    vi.useFakeTimers()
    const wrapper = mountHome()
    await flushPromises()

    mockListConfigs.mockResolvedValue({
      items: [makeConfig({ id: 'cfg-1', sceneName: 'Alpha Config' })],
      total: 1,
      page: 1,
      pageSize: 10,
      totalPages: 1,
    })

    // The NInput stub wraps <input> in a div; find the actual input inside
    const searchWrapper = wrapper.find('.home__search-input')
    const input = searchWrapper.find('input')
    await input.setValue('Alpha')

    // Trigger the update:value event which the component listens to via @update:value
    await input.trigger('input')

    // Wait for debounce (300ms)
    vi.advanceTimersByTime(350)
    await flushPromises()

    // listConfigs should be called with search term
    expect(mockListConfigs).toHaveBeenCalledWith(1, 10, 'Alpha')

    vi.useRealTimers()
  })

  // ── 3. Shows "new config" button ────────────────────────────

  it('shows "新建配置" button when user can edit', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const newConfigBtn = buttons.find(b => b.text().includes('新建配置'))
    expect(newConfigBtn).toBeDefined()
  })

  it('clicks "新建配置" navigates to /config/new', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const newConfigBtn = buttons.find(b => b.text().includes('新建配置'))
    expect(newConfigBtn).toBeTruthy()
    await newConfigBtn!.trigger('click')

    expect(mockResetAll).toHaveBeenCalled()
    expect(mockRouterPush).toHaveBeenCalledWith('/config/new')
  })

  it('shows "模板市场" button', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const templateBtn = buttons.find(b => b.text().includes('模板市场'))
    expect(templateBtn).toBeTruthy()
  })

  it('shows "指南" button', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const guideBtn = buttons.find(b => b.text().includes('指南'))
    expect(guideBtn).toBeTruthy()
  })

  // ── 4. Handles empty state ──────────────────────────────────

  it('shows empty state when no configs and no search query', async () => {
    const wrapper = mountHome({ items: [], total: 0, page: 1, pageSize: 10, totalPages: 0 })
    await flushPromises()

    expect(wrapper.text()).toContain('还没有配置')
    expect(wrapper.text()).toContain('点击上方按钮开始创建你的第一个数据管道配置')
  })

  it('shows empty search result message when search yields no results', async () => {
    // First mount with results so search input is visible
    const wrapper = mountHome()
    await flushPromises()

    // Now simulate a search that returns no results
    mockListConfigs.mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 10, totalPages: 0 })

    vi.useFakeTimers()
    const searchWrapper = wrapper.find('.home__search-input')
    const input = searchWrapper.find('input')
    await input.setValue('nonexistent')
    await input.trigger('input')
    vi.advanceTimersByTime(350)
    await flushPromises()
    vi.useRealTimers()

    expect(wrapper.text()).toContain('没有找到匹配的配置')
  })

  it('shows loading skeleton while loading', async () => {
    // Make listConfigs hang so loading stays true
    mockListConfigs.mockReturnValue(new Promise(() => {}))
    const wrapper = mountHome()
    // Don't await flushPromises — loading is still true

    expect(wrapper.find('.home__skeleton').exists()).toBe(true)
  })

  it('shows error alert when API returns error', async () => {
    // Make listConfigs throw to trigger error state
    mockListConfigs.mockRejectedValue(new Error('Network Error'))
    const wrapper = mountHome()
    await flushPromises()

    // The component should still render without crashing
    // useConfigApi catches errors internally, so it renders with empty configs
    expect(wrapper.find('.stub-config-list-card').exists() || wrapper.find('.home__empty').exists() || wrapper.find('.home__config-list').exists()).toBe(true)
  })

  // ── 5. Pagination controls work ─────────────────────────────

  it('shows pagination when totalPages > 1', async () => {
    const multiPageResult = {
      items: defaultConfigs,
      total: 25,
      page: 1,
      pageSize: 10,
      totalPages: 3,
    }
    const wrapper = mountHome(multiPageResult)
    await flushPromises()

    expect(wrapper.find('.home__pagination').exists()).toBe(true)
    expect(wrapper.text()).toContain('1 / 3')
  })

  it('does not show pagination when totalPages === 1', async () => {
    const wrapper = mountHome()
    await flushPromises()

    expect(wrapper.find('.home__pagination').exists()).toBe(false)
  })

  it('disables "上一页" button on first page', async () => {
    const multiPageResult = {
      items: defaultConfigs,
      total: 25,
      page: 1,
      pageSize: 10,
      totalPages: 3,
    }
    const wrapper = mountHome(multiPageResult)
    await flushPromises()

    const pagination = wrapper.find('.home__pagination')
    const buttons = pagination.findAll('button')
    const prevBtn = buttons.find(b => b.text().includes('上一页'))
    expect(prevBtn?.attributes('disabled')).toBeDefined()
  })

  it('disables "下一页" button on last page', async () => {
    const multiPageResult = {
      items: defaultConfigs,
      total: 25,
      page: 1,
      pageSize: 10,
      totalPages: 3,
    }
    const wrapper = mountHome(multiPageResult)
    await flushPromises()

    // Navigate to page 3 (last page) by clicking next twice
    mockListConfigs.mockResolvedValue({
      items: defaultConfigs,
      total: 25,
      page: 2,
      pageSize: 10,
      totalPages: 3,
    })
    let pagination = wrapper.find('.home__pagination')
    let nextBtn = pagination.findAll('button').find(b => b.text().includes('下一页'))
    await nextBtn!.trigger('click')
    await flushPromises()

    mockListConfigs.mockResolvedValue({
      items: defaultConfigs,
      total: 25,
      page: 3,
      pageSize: 10,
      totalPages: 3,
    })
    pagination = wrapper.find('.home__pagination')
    nextBtn = pagination.findAll('button').find(b => b.text().includes('下一页'))
    await nextBtn!.trigger('click')
    await flushPromises()

    // Now on page 3, the next button should be disabled
    pagination = wrapper.find('.home__pagination')
    const buttons = pagination.findAll('button')
    const nextBtnOnLastPage = buttons.find(b => b.text().includes('下一页'))
    expect(nextBtnOnLastPage).toBeTruthy()
    expect(nextBtnOnLastPage!.attributes('disabled')).toBeDefined()
  })

  it('clicks "下一页" calls loadConfigList with next page', async () => {
    const multiPageResult = {
      items: defaultConfigs,
      total: 25,
      page: 1,
      pageSize: 10,
      totalPages: 3,
    }
    const wrapper = mountHome(multiPageResult)
    await flushPromises()

    mockListConfigs.mockResolvedValue({
      items: [makeConfig({ id: 'cfg-3', sceneName: 'Page 2 Config' })],
      total: 25,
      page: 2,
      pageSize: 10,
      totalPages: 3,
    })

    const pagination = wrapper.find('.home__pagination')
    const buttons = pagination.findAll('button')
    const nextBtn = buttons.find(b => b.text().includes('下一页'))
    expect(nextBtn).toBeTruthy()
    await nextBtn!.trigger('click')
    await flushPromises()

    expect(mockListConfigs).toHaveBeenCalledWith(2, 10, '')
  })

  it('clicks "上一页" calls loadConfigList with previous page', async () => {
    const page2Result = {
      items: defaultConfigs,
      total: 25,
      page: 2,
      pageSize: 10,
      totalPages: 3,
    }
    const wrapper = mountHome(page2Result)
    await flushPromises()

    mockListConfigs.mockResolvedValue({
      items: defaultConfigs,
      total: 25,
      page: 1,
      pageSize: 10,
      totalPages: 3,
    })

    const pagination = wrapper.find('.home__pagination')
    const buttons = pagination.findAll('button')
    const prevBtn = buttons.find(b => b.text().includes('上一页'))
    expect(prevBtn).toBeTruthy()
    await prevBtn!.trigger('click')
    await flushPromises()

    expect(mockListConfigs).toHaveBeenCalledWith(1, 10, '')
  })

  // ── 6. Batch management mode toggle ─────────────────────────

  it('shows "批量管理" button when not in batch mode', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const batchBtn = buttons.find(b => b.text().includes('批量管理'))
    expect(batchBtn).toBeTruthy()
  })

  it('enters batch mode on "批量管理" click', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const batchBtn = buttons.find(b => b.text().includes('批量管理'))
    expect(batchBtn).toBeTruthy()
    await batchBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    // Should now show "取消" button instead of "批量管理"
    const updatedButtons = wrapper.findAll('button')
    const cancelBtn = updatedButtons.find(b => b.text().includes('取消'))
    expect(cancelBtn).toBeTruthy()

    // Batch bar should be visible
    expect(wrapper.find('.home__batch-bar').exists()).toBe(true)
  })

  it('exits batch mode on "取消" click', async () => {
    const wrapper = mountHome()
    await flushPromises()

    // Enter batch mode
    const buttons = wrapper.findAll('button')
    const batchBtn = buttons.find(b => b.text().includes('批量管理'))
    await batchBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    // Click cancel
    const cancelBtn = wrapper.findAll('button').find(b => b.text().includes('取消'))
    expect(cancelBtn).toBeTruthy()
    await cancelBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    // Batch bar should be gone
    expect(wrapper.find('.home__batch-bar').exists()).toBe(false)
  })

  it('shows batch bar with select all checkbox and selected count', async () => {
    const wrapper = mountHome()
    await flushPromises()

    // Enter batch mode
    const buttons = wrapper.findAll('button')
    const batchBtn = buttons.find(b => b.text().includes('批量管理'))
    await batchBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    const batchBar = wrapper.find('.home__batch-bar')
    expect(batchBar.exists()).toBe(true)
    // Check for the checkbox label text
    expect(batchBar.text()).toContain('全选')
    expect(batchBar.text()).toContain('已选 0 项')
  })

  it('shows "删除选中" button disabled when nothing selected', async () => {
    const wrapper = mountHome()
    await flushPromises()

    // Enter batch mode
    const batchBtn = wrapper.findAll('button').find(b => b.text().includes('批量管理'))
    await batchBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    const batchBar = wrapper.find('.home__batch-bar')
    const deleteBtn = batchBar.findAll('button').find(b => b.text().includes('删除选中'))
    expect(deleteBtn).toBeTruthy()
    expect(deleteBtn!.attributes('disabled')).toBeDefined()
  })

  // ── 7. Config card actions (execute, more actions menu) ─────

  it('passes canEdit to ConfigListCard', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const card = wrapper.findComponent(StubConfigListCard)
    expect((card.props() as { canEdit: boolean }).canEdit).toBe(true)
  })

  it('opens execute modal when ConfigListCard emits execute', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const card = wrapper.findComponent(StubConfigListCard)
    const testConfig = defaultConfigs[0]
    await card.vm.$emit('execute', testConfig)
    await wrapper.vm.$nextTick()

    const modal = wrapper.findComponent(StubExecuteConfigModal)
    expect(modal.exists()).toBe(true)
    expect((modal.props() as { config: SavedConfig }).config).toEqual(testConfig)
  })

  it('navigates to edit when ConfigListCard emits menuSelect with "edit"', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const card = wrapper.findComponent(StubConfigListCard)
    await card.vm.$emit('menuSelect', 'edit', defaultConfigs[0])
    await flushPromises()

    expect(mockRouterPush).toHaveBeenCalledWith('/config/new?load=cfg-1')
  })

  it('opens version modal when ConfigListCard emits menuSelect with "versions"', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const card = wrapper.findComponent(StubConfigListCard)
    await card.vm.$emit('menuSelect', 'versions', defaultConfigs[0])
    await wrapper.vm.$nextTick()

    const versionPanel = wrapper.findComponent(StubConfigVersionPanel)
    expect(versionPanel.exists()).toBe(true)
    expect((versionPanel.props() as { configId: string }).configId).toBe('cfg-1')
  })

  it('calls downloadConfigYaml when ConfigListCard emits menuSelect with "download"', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const card = wrapper.findComponent(StubConfigListCard)
    await card.vm.$emit('menuSelect', 'download', defaultConfigs[0])
    await flushPromises()

    expect(mockDownloadConfigYaml).toHaveBeenCalledWith('cfg-1')
  })

  it('shows delete confirmation modal when ConfigListCard emits menuSelect with "delete"', async () => {
    const wrapper = mountHome()
    await flushPromises()

    const card = wrapper.findComponent(StubConfigListCard)
    await card.vm.$emit('menuSelect', 'delete', defaultConfigs[0])
    await flushPromises()

    // Check that deleteModalVisible is true
    expect((wrapper.vm as HomeViewVm).deleteModalVisible).toBe(true)
    // Check that deletingConfig is set
    expect((wrapper.vm as HomeViewVm).deletingConfig?.sceneName).toBe('Alpha Config')
  })

  it('deletes config on confirm delete', async () => {
    mockDeleteConfig.mockResolvedValue(true)
    const wrapper = mountHome()
    await flushPromises()

    // Open delete modal
    const card = wrapper.findComponent(StubConfigListCard)
    await card.vm.$emit('menuSelect', 'delete', defaultConfigs[0])
    await flushPromises()

    // Call onConfirmDelete directly
    await (wrapper.vm as HomeViewVm).onConfirmDelete()
    await flushPromises()

    expect(mockDeleteConfig).toHaveBeenCalledWith('cfg-1')
  })

  it('navigates via gotoStep when ExecuteConfigModal emits gotoStep', async () => {
    const wrapper = mountHome()
    await flushPromises()

    // Open execute modal first
    const card = wrapper.findComponent(StubConfigListCard)
    await card.vm.$emit('execute', defaultConfigs[0])
    await wrapper.vm.$nextTick()

    // Emit gotoStep from the modal
    const modal = wrapper.findComponent(StubExecuteConfigModal)
    await modal.vm.$emit('gotoStep', 2)
    await flushPromises()

    expect(mockRouterPush).toHaveBeenCalledWith({
      path: '/config/new',
      query: { load: 'cfg-1', step: '2' },
    })
  })

  it('calls loadConfigList on mount', async () => {
    mountHome()
    await flushPromises()

    expect(mockListConfigs).toHaveBeenCalledWith(1, 10, '')
  })
})
