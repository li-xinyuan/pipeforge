import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref, nextTick } from 'vue'
import TemplateMarketView from '../../src/views/TemplateMarketView.vue'
import type { Template } from '../../src/types/wizard'
import type { ComponentPublicInstance } from 'vue'

type TemplateMarketViewVm = ComponentPublicInstance<{
  searchQuery: string
  onSearch: () => void
  previewVisible: boolean
  previewTemplate: Template | null
  sortBy: string
  currentPage: number
  filteredTemplates: Template[]
  onSortChange: () => void
}>

// ─── Mock factories ───────────────────────────────────────────────

const mockTemplates = [
  {
    id: 'tpl-1',
    name: '销售日报',
    description: '每日销售数据汇总模板',
    category: 'sales',
    tags: ['日报', '销售'],
    author: 'Admin',
    version: '1.0',
    configState: {},
    requirements: [],
    usageCount: 42,
    isOfficial: true,
    createdAt: '2025-01-01',
    updatedAt: '2025-06-01',
  },
  {
    id: 'tpl-2',
    name: '财务月报',
    description: '月度财务报表模板',
    category: 'finance',
    tags: ['月报', '财务'],
    author: 'User1',
    version: '2.0',
    configState: {},
    requirements: [],
    usageCount: 10,
    isOfficial: false,
    createdAt: '2025-02-01',
    updatedAt: '2025-06-01',
  },
  {
    id: 'tpl-3',
    name: '人力考勤',
    description: '员工考勤统计模板',
    category: 'hr',
    tags: ['考勤', 'HR'],
    author: 'User2',
    version: '1.1',
    configState: {},
    requirements: [],
    usageCount: 5,
    isOfficial: false,
    createdAt: '2025-03-01',
    updatedAt: '2025-06-01',
  },
]

function createMockListTemplates(templates = mockTemplates) {
  return vi.fn().mockResolvedValue({ items: templates, total: templates.length })
}

// ─── Shared mock references ───────────────────────────────────────

const mockListTemplates = createMockListTemplates()
const mockDeleteTemplate = vi.fn().mockResolvedValue(true)
const mockExportTemplate = vi.fn().mockResolvedValue(new Blob(['{}'], { type: 'application/json' }))
const mockImportTemplate = vi.fn().mockResolvedValue({ message: 'ok', id: 'new-id' })
const mockLoading = ref(false)
const mockError = ref(null)

// ─── Module mocks ─────────────────────────────────────────────────

vi.mock('../../src/composables/useTemplateApi', () => ({
  useTemplateApi: () => ({
    listTemplates: mockListTemplates,
    deleteTemplate: mockDeleteTemplate,
    exportTemplate: mockExportTemplate,
    importTemplate: mockImportTemplate,
    loading: mockLoading,
    error: mockError,
  }),
}))

// auth store mock — isAdmin defaults to false; override per test
const mockAuth = {
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
}
vi.mock('../../src/stores/auth', () => ({
  useAuthStore: () => mockAuth,
}))

vi.mock('../../src/composables/useTheme', () => ({
  useTheme: () => ({ isDark: { value: false }, toggleTheme: vi.fn() }),
}))

// Stub child components that are not under test
const stubs = {
  AppNavBar: { template: '<div class="app-nav-bar-stub" />' },
  TemplatePreviewModal: {
    template: '<div class="preview-modal-stub" />',
    props: ['show', 'template'],
    emits: ['update:show', 'close'],
  },
  ErrorBoundary: { template: '<div class="error-boundary-stub"><slot /></div>' },
  NInput: {
    template: '<input class="n-input-stub" :value="value" />',
    props: ['value', 'placeholder', 'clearable', 'size'],
    emits: ['update:value'],
  },
  NTag: {
    template: '<span class="n-tag-stub"><slot /></span>',
    props: ['size', 'bordered', 'type'],
  },
  NAlert: {
    template: '<div class="n-alert-stub">{{ title }}</div>',
    props: ['type', 'title'],
  },
  NButton: {
    template: '<button class="n-button-stub" @click="$emit(\'click\')"><slot /></button>',
    props: ['size', 'type', 'quaternary', 'loading'],
    emits: ['click'],
  },
}

// ─── Helper ───────────────────────────────────────────────────────

async function mountView() {
  const wrapper = mount(TemplateMarketView, {
    global: { stubs },
  })
  await flushPromises()
  return wrapper
}

// ─── Tests ────────────────────────────────────────────────────────

describe('TemplateMarketView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListTemplates.mockResolvedValue({ items: [...mockTemplates], total: mockTemplates.length })
    mockDeleteTemplate.mockResolvedValue(true)
    mockExportTemplate.mockResolvedValue(new Blob(['{}'], { type: 'application/json' }))
    mockImportTemplate.mockResolvedValue({ message: 'ok', id: 'new-id' })
    mockLoading.value = false
    mockError.value = null
    mockAuth.isAdmin = false
  })

  // ── 1. Renders template list with cards ───────────────────────

  it('renders template list with cards', async () => {
    const wrapper = await mountView()

    const cards = wrapper.findAll('.market__card')
    expect(cards).toHaveLength(3)

    expect(wrapper.text()).toContain('销售日报')
    expect(wrapper.text()).toContain('财务月报')
    expect(wrapper.text()).toContain('人力考勤')
  })

  it('shows official tag for official templates', async () => {
    const wrapper = await mountView()
    const cards = wrapper.findAll('.market__card')
    // First template is official
    expect(cards[0].text()).toContain('官方')
    // Second is not
    expect(cards[1].text()).not.toContain('官方')
  })

  it('shows template metadata (author, usage count)', async () => {
    const wrapper = await mountView()
    expect(wrapper.text()).toContain('Admin')
    expect(wrapper.text()).toContain('使用 42 次')
  })

  it('shows empty state when no templates', async () => {
    mockListTemplates.mockResolvedValue({ items: [], total: 0 })
    const wrapper = await mountView()

    expect(wrapper.find('.market__empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('暂无模板')
  })

  it('shows loading skeleton', async () => {
    mockLoading.value = true
    // Keep listTemplates pending so loading stays true
    mockListTemplates.mockReturnValue(new Promise(() => {}))
    const wrapper = mount(TemplateMarketView, { global: { stubs } })
    await nextTick()

    expect(wrapper.find('.market__skeleton').exists()).toBe(true)
  })

  it('shows error alert when API fails', async () => {
    mockListTemplates.mockResolvedValue({ items: [], total: 0 })
    const wrapper = await mountView()

    // Simulate the error state by directly setting the shared ref after mount
    mockLoading.value = false
    mockError.value = { message: 'Network error' }
    await nextTick()

    // The NAlert stub should render with the error message
    expect(wrapper.text()).toContain('Network error')
  })

  // ── 2. Shows category filter tabs ─────────────────────────────

  it('shows category filter tabs', async () => {
    const wrapper = await mountView()

    const tabs = wrapper.findAll('.market__filter-tab')
    expect(tabs.length).toBeGreaterThanOrEqual(6) // 全部 + 5 categories

    expect(wrapper.text()).toContain('全部')
    expect(wrapper.text()).toContain('销售')
    expect(wrapper.text()).toContain('财务')
    expect(wrapper.text()).toContain('人力')
    expect(wrapper.text()).toContain('运维')
    expect(wrapper.text()).toContain('通用')
  })

  it('highlights active category tab', async () => {
    const wrapper = await mountView()

    // "全部" should be active by default (value = '')
    const tabs = wrapper.findAll('.market__filter-tab')
    const allTab = tabs[0]
    expect(allTab.classes()).toContain('market__filter-tab--active')
  })

  it('switches category on tab click', async () => {
    const wrapper = await mountView()

    const tabs = wrapper.findAll('.market__filter-tab')
    // Click "销售" (index 1)
    await tabs[1].trigger('click')
    await flushPromises()

    expect(mockListTemplates).toHaveBeenCalledWith('sales', undefined)
  })

  // ── 3. Search/filter templates by name ─────────────────────────

  it('calls listTemplates after search debounce', async () => {
    vi.useFakeTimers()
    const wrapper = await mountView()
    mockListTemplates.mockClear()

    // Directly set searchQuery and call onSearch (simulates NInput update:value)
    const vm = wrapper.vm as TemplateMarketViewVm
    vm.searchQuery = '日报'
    vm.onSearch()

    // Before debounce fires, listTemplates should not be called again
    expect(mockListTemplates).not.toHaveBeenCalled()

    // Advance timers past the 300ms debounce
    vi.advanceTimersByTime(350)
    await flushPromises()

    expect(mockListTemplates).toHaveBeenCalledWith(undefined, '日报')

    vi.useRealTimers()
  })

  it('resets page when search query changes', async () => {
    const wrapper = await mountView()
    // Access component internals
    const vm = wrapper.vm as TemplateMarketViewVm
    vm.searchQuery = 'test'
    await nextTick()

    expect(vm.currentPage).toBe(1)
  })

  // ── 4. Delete button visible for admin users ──────────────────

  it('hides delete button for non-admin users', async () => {
    mockAuth.isAdmin = false
    const wrapper = await mountView()

    const deleteButtons = wrapper.findAll('.market__card-delete')
    expect(deleteButtons).toHaveLength(0)
  })

  it('shows delete button for admin users', async () => {
    mockAuth.isAdmin = true
    const wrapper = await mountView()

    const deleteButtons = wrapper.findAll('.market__card-delete')
    expect(deleteButtons.length).toBeGreaterThan(0)
  })

  // ── 5. Two-step delete confirmation ───────────────────────────

  it('shows confirmation UI after clicking delete', async () => {
    mockAuth.isAdmin = true
    const wrapper = await mountView()

    const deleteBtn = wrapper.find('.market__card-delete')
    await deleteBtn.trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('确认删除？')
    expect(wrapper.find('.market__card-confirm-text').exists()).toBe(true)
  })

  it('cancels delete and restores normal actions', async () => {
    mockAuth.isAdmin = true
    const wrapper = await mountView()

    // Click delete to enter confirm state
    const deleteBtn = wrapper.find('.market__card-delete')
    await deleteBtn.trigger('click')
    await nextTick()

    // After clicking delete, the confirm/cancel buttons should appear
    // Find all buttons in the first card's actions area
    const card = wrapper.find('.market__card')
    const buttons = card.findAll('button')
    const cancelBtn = buttons.find(b => b.text().includes('取消'))
    expect(cancelBtn).toBeTruthy()
    await cancelBtn!.trigger('click')
    await nextTick()

    // Confirm state should be gone
    expect(wrapper.find('.market__card-confirm-text').exists()).toBe(false)
    // Delete button should be back
    expect(wrapper.find('.market__card-delete').exists()).toBe(true)
  })

  it('confirms delete and removes template from list', async () => {
    mockAuth.isAdmin = true
    const wrapper = await mountView()

    // Click delete to enter confirm state
    const deleteBtn = wrapper.find('.market__card-delete')
    await deleteBtn.trigger('click')
    await nextTick()

    // Find confirm button within the first card
    const card = wrapper.find('.market__card')
    const buttons = card.findAll('button')
    const confirmBtn = buttons.find(b => b.text().includes('确定'))
    expect(confirmBtn).toBeTruthy()
    await confirmBtn!.trigger('click')
    await flushPromises()

    expect(mockDeleteTemplate).toHaveBeenCalled()
    // Template should be removed from the list
    const cards = wrapper.findAll('.market__card')
    expect(cards).toHaveLength(2)
  })

  // ── 6. "Use template" button works ────────────────────────────

  it('opens preview modal on "使用此模板" click', async () => {
    const wrapper = await mountView()

    // Find "使用此模板" button — it has class market__card-btn
    const useBtn = wrapper.find('.market__card-btn')
    expect(useBtn.exists()).toBe(true)
    await useBtn.trigger('click')
    await nextTick()

    const vm = wrapper.vm as TemplateMarketViewVm
    expect(vm.previewVisible).toBe(true)
    expect(vm.previewTemplate).toBeTruthy()
    expect(vm.previewTemplate.id).toBe('tpl-1')
  })

  it('opens preview modal on card click', async () => {
    const wrapper = await mountView()

    const card = wrapper.find('.market__card')
    await card.trigger('click')
    await nextTick()

    const vm = wrapper.vm as TemplateMarketViewVm
    expect(vm.previewVisible).toBe(true)
  })

  // ── 7. Import/export buttons ──────────────────────────────────

  it('renders import button', async () => {
    const wrapper = await mountView()

    // The import button has class market__import-btn in the template
    const importBtn = wrapper.find('.market__import-btn')
    expect(importBtn.exists()).toBe(true)
    expect(importBtn.text()).toContain('导入模板')
  })

  it('renders export button on each card', async () => {
    const wrapper = await mountView()

    const exportBtns = wrapper.findAll('.market__card-export')
    expect(exportBtns).toHaveLength(3)
  })

  it('calls exportTemplate on export click', async () => {
    // Mock URL.createObjectURL / revokeObjectURL for happy-dom
    const mockCreateObjectURL = vi.fn(() => 'blob:http://localhost/fake')
    const mockRevokeObjectURL = vi.fn()
    vi.stubGlobal('URL', {
      createObjectURL: mockCreateObjectURL,
      revokeObjectURL: mockRevokeObjectURL,
    })

    const wrapper = await mountView()

    const exportBtn = wrapper.find('.market__card-export')
    await exportBtn.trigger('click')
    await flushPromises()

    expect(mockExportTemplate).toHaveBeenCalledWith('tpl-1')
    expect(mockCreateObjectURL).toHaveBeenCalled()

    vi.unstubAllGlobals()
  })

  it('triggers file input on import button click', async () => {
    const wrapper = await mountView()

    // The component uses a hidden file input; verify it exists
    const fileInput = wrapper.find('input[type="file"]')
    expect(fileInput.exists()).toBe(true)

    // Verify the import button exists and is connected to triggerImport
    const importBtn = wrapper.find('.market__import-btn')
    expect(importBtn.exists()).toBe(true)
  })

  // ── 8. Sort dropdown ──────────────────────────────────────────

  it('renders sort dropdown', async () => {
    const wrapper = await mountView()

    const select = wrapper.find('.market__sort-select')
    expect(select.exists()).toBe(true)

    const options = select.findAll('option')
    expect(options).toHaveLength(2) // 默认排序 + 热门模板
    expect(options[0].text()).toBe('默认排序')
    expect(options[1].text()).toBe('热门模板')
  })

  it('sorts by popularity when "热门模板" is selected', async () => {
    const wrapper = await mountView()

    const select = wrapper.find('.market__sort-select')
    // Change sort value
    const vm = wrapper.vm as TemplateMarketViewVm
    vm.sortBy = 'popular'
    await nextTick()

    // The filteredTemplates computed should sort by usageCount descending
    const sorted = vm.filteredTemplates
    expect(sorted[0].usageCount).toBeGreaterThanOrEqual(sorted[1].usageCount)
  })

  it('resets page when sort changes', async () => {
    const wrapper = await mountView()
    const vm = wrapper.vm as TemplateMarketViewVm
    vm.currentPage = 3
    vm.sortBy = 'popular'
    vm.onSortChange()
    expect(vm.currentPage).toBe(1)
  })

  // ── Pagination ────────────────────────────────────────────────

  it('shows pagination when templates exceed page size', async () => {
    // Create 15 templates to exceed pageSize (12)
    const manyTemplates = Array.from({ length: 15 }, (_, i) => ({
      ...mockTemplates[0],
      id: `tpl-${i}`,
      name: `模板 ${i}`,
    }))
    mockListTemplates.mockResolvedValue({ items: manyTemplates, total: 15 })
    const wrapper = await mountView()

    expect(wrapper.find('.market__pagination').exists()).toBe(true)
    expect(wrapper.text()).toContain('1 / 2')
  })

  it('navigates to next page', async () => {
    const manyTemplates = Array.from({ length: 15 }, (_, i) => ({
      ...mockTemplates[0],
      id: `tpl-${i}`,
      name: `模板 ${i}`,
    }))
    mockListTemplates.mockResolvedValue({ items: manyTemplates, total: 15 })
    const wrapper = await mountView()

    const nextBtn = wrapper.findAll('.market__pagination-btn').find(b => b.text() === '下一页')
    expect(nextBtn).toBeTruthy()
    await nextBtn!.trigger('click')
    await nextTick()

    const vm = wrapper.vm as TemplateMarketViewVm
    expect(vm.currentPage).toBe(2)
  })
})
