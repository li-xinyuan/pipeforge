import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ConfigWizardView from '../../src/views/ConfigWizardView.vue'

// ── Mock factories ──────────────────────────────────────────────

function createMockStore(overrides: Record<string, unknown> = {}) {
  return {
    scene: { name: '', description: '', version: '' },
    inputs: [],
    processors: [],
    output: null,
    uploadedFiles: {},
    currentStep: 1,
    configId: null,
    aiSuggestions: {},
    dryRunResults: null,
    pendingAutofixes: [],
    canProceed: vi.fn((n: number) => {
      if (n === 1) return false
      return false
    }),
    stepValidation: vi.fn((n: number) => {
      if (n === 1) return ['请输入场景名称']
      return []
    }),
    goBackToStep: vi.fn(),
    resetAll: vi.fn(),
    setConfigId: vi.fn(),
    loadFromConfigState: vi.fn(),
    getWizardState: vi.fn(() => ({
      currentStep: 1,
      scene: { name: '', description: '', version: '' },
      inputs: [],
      processors: [],
      output: null,
      uploadedFiles: {},
      aiSuggestions: {},
    })),
    applyAutofixes: vi.fn(),
    setDryRunResults: vi.fn(),
    ...overrides,
  }
}

// ── Mocks ───────────────────────────────────────────────────────

const mockLoadConfigState = vi.fn()

vi.mock('../../src/composables/useConfigApi', () => ({
  useConfigApi: () => ({
    loading: { value: false },
    error: { value: null },
    loadConfigState: mockLoadConfigState,
  }),
}))

const mockDryRun = vi.fn()
const mockAskSuggestion = vi.fn()

vi.mock('../../src/composables/useWizardApi', async () => ({
  useWizardApi: () => ({
    loading: { value: false },
    error: { value: null },
    dryRun: mockDryRun,
    initScene: vi.fn(),
    fetchPreview: vi.fn(),
    generateYaml: vi.fn(),
    executeSql: vi.fn(),
    executePipeline: vi.fn(),
  }),
  useAiApi: () => ({
    loading: { value: false },
    suggesting: { value: false },
    error: { value: null },
    aiError: { value: null },
    askSuggestion: mockAskSuggestion,
  }),
}))

vi.mock('../../src/composables/useKeyboard', () => ({
  useKeyboard: vi.fn(),
}))

vi.mock('../../src/composables/useBreakpoint', () => ({
  useBreakpoint: () => ({
    breakpoint: { value: 'desktop' },
  }),
}))

const mockStore = createMockStore()

vi.mock('../../src/stores/wizard', () => ({
  useWizardStore: () => mockStore,
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

vi.mock('vue-router', () => ({
  useRoute: () => ({
    query: {},
    path: '/config/new',
  }),
  useRouter: () => ({
    push: vi.fn(),
  }),
  onBeforeRouteLeave: vi.fn((cb) => {
    // Store the callback so we can invoke it in tests if needed
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

const StubWizardStepCard = {
  name: 'WizardStepCard',
  template: `
    <div class="stub-wizard-step-card" :data-step="step">
      <div class="stub-step-header" @click="$emit('header-click')">
        <span class="stub-step-title">{{ title }}</span>
        <span v-if="badge" class="stub-step-badge">{{ badge }}</span>
        <span v-if="summary" class="stub-step-summary">{{ summary }}</span>
      </div>
      <div v-if="!collapsed" class="stub-step-body"><slot /></div>
      <div v-if="!collapsed" class="stub-step-footer"><slot name="footer" /></div>
    </div>
  `,
  props: ['title', 'description', 'icon', 'iconBg', 'status', 'badge', 'step', 'collapsed', 'summary'],
  emits: ['header-click'],
}

const StubWizardProgress = {
  name: 'WizardProgress',
  template: '<div class="stub-wizard-progress" />',
  props: ['steps'],
  emits: ['stepClick'],
}

const StubGuidePanel = {
  name: 'GuidePanel',
  template: '<div class="stub-guide-panel" />',
  props: ['currentStep'],
}

const StubInputSourceList = {
  name: 'InputSourceList',
  template: '<div class="stub-input-source-list" />',
  props: ['pulseCta'],
}

const StubSqlEditorTab = {
  name: 'SqlEditorTab',
  template: '<div class="stub-sql-editor-tab" />',
  props: ['pulseCta'],
  methods: { checkTableRenames: vi.fn() },
}

const StubOutputConfigTab = {
  name: 'OutputConfigTab',
  template: '<div class="stub-output-config-tab" />',
  props: ['pulseCta'],
}

const StubYamlPreview = {
  name: 'YamlPreview',
  template: '<div class="stub-yaml-preview" />',
  methods: { loadYaml: vi.fn() },
}

const StubExportActions = {
  name: 'ExportActions',
  template: '<div class="stub-export-actions" />',
  props: ['yaml'],
  emits: ['gotoStep'],
  methods: { saveConfigHandler: vi.fn(), downloadResult: vi.fn() },
}

const StubDataPreviewTable = {
  name: 'DataPreviewTable',
  template: '<div class="stub-data-preview-table" />',
  props: ['columns', 'rows'],
}

const StubAiTriggerButton = {
  name: 'AiTriggerButton',
  template: '<button class="stub-ai-trigger-btn" :disabled="disabled" :loading="loading" @click="$emit(\'click\')"><slot /></button>',
  props: ['label', 'loading', 'disabled'],
  emits: ['click'],
}

const StubNotificationSettings = {
  name: 'NotificationSettings',
  template: '<div class="stub-notification-settings" />',
}

const StubSaveAsTemplateModal = {
  name: 'SaveAsTemplateModal',
  template: '<div class="stub-save-as-template-modal" />',
  props: ['show'],
  emits: ['update:show'],
}

const StubErrorBoundary = {
  name: 'ErrorBoundary',
  template: '<div class="stub-error-boundary"><slot /></div>',
}

// ── Mount helper ────────────────────────────────────────────────

function mountWizard(storeOverrides: Record<string, unknown> = {}) {
  Object.assign(mockStore, createMockStore(storeOverrides))

  return mount(ConfigWizardView, {
    global: {
      stubs: {
        AppNavBar: { template: '<div class="stub-navbar" />' },
        WizardStepCard: StubWizardStepCard,
        WizardProgress: StubWizardProgress,
        GuidePanel: StubGuidePanel,
        InputSourceList: StubInputSourceList,
        SqlEditorTab: StubSqlEditorTab,
        OutputConfigTab: StubOutputConfigTab,
        YamlPreview: StubYamlPreview,
        ExportActions: StubExportActions,
        DataPreviewTable: StubDataPreviewTable,
        AiTriggerButton: StubAiTriggerButton,
        NotificationSettings: StubNotificationSettings,
        SaveAsTemplateModal: StubSaveAsTemplateModal,
        ErrorBoundary: StubErrorBoundary,
        NButton: {
          template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
          props: ['type', 'size', 'disabled', 'loading'],
          emits: ['click'],
        },
        NInput: {
          template: '<div class="stub-n-input"><input :value="modelValue" @input="$emit(\'update:value\', $event.target.value)" /></div>',
          props: ['modelValue', 'placeholder', 'size', 'type', 'rows'],
          emits: ['update:modelValue', 'update:value'],
        },
      },
    },
  })
}

// ── Tests ───────────────────────────────────────────────────────

describe('ConfigWizardView', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    mockLoadConfigState.mockResolvedValue(null)
    mockDryRun.mockResolvedValue(null)
    mockAskSuggestion.mockResolvedValue(null)
  })

  // ── 1. Renders the wizard with 5 step cards ─────────────────

  it('renders the wizard with 5 step cards', async () => {
    const wrapper = mountWizard()
    await flushPromises()

    const stepCards = wrapper.findAllComponents(StubWizardStepCard)
    expect(stepCards).toHaveLength(5)

    // Verify step titles
    const titles = stepCards.map(c => c.props('title'))
    expect(titles).toEqual(['场景信息', '输入源', '处理步骤', '输出配置', '预览与导出'])
  })

  // ── 2. Shows step 1 as active by default ────────────────────

  it('shows step 1 as active by default', async () => {
    const wrapper = mountWizard()
    await flushPromises()

    const stepCards = wrapper.findAllComponents(StubWizardStepCard)

    // Step 1 should be active
    expect(stepCards[0].props('status')).toBe('active')
    expect(stepCards[0].props('badge')).toBe('⟳ 当前步骤')

    // Steps 2-5 should be locked
    for (let i = 1; i < 5; i++) {
      expect(stepCards[i].props('status')).toBe('locked')
      expect(stepCards[i].props('badge')).toBe('待解锁')
    }
  })

  // ── 3. Can navigate between steps ───────────────────────────

  it('can navigate between steps via completeStep', async () => {
    // Start at step 1, canProceed(1) returns true
    const wrapper = mountWizard({
      canProceed: vi.fn((n: number) => n <= 2),
      stepValidation: vi.fn(() => []),
    })
    await flushPromises()

    // Click "下一步" on step 1
    const stepCards = wrapper.findAllComponents(StubWizardStepCard)
    const step1Footer = stepCards[0].find('.stub-step-footer')
    const nextBtn = step1Footer.find('button')
    expect(nextBtn.exists()).toBe(true)
    expect(nextBtn.attributes('disabled')).toBeUndefined()
    await nextBtn.trigger('click')
    await flushPromises()

    // Now step 1 should be completed, step 2 should be active
    const updatedCards = wrapper.findAllComponents(StubWizardStepCard)
    expect(updatedCards[0].props('status')).toBe('completed')
    expect(updatedCards[1].props('status')).toBe('active')
  })

  // ── 4. Step validation - cannot proceed without required fields ──

  it('cannot proceed without required fields (step 1)', async () => {
    // canProceed(1) returns false by default (empty scene name)
    const wrapper = mountWizard()
    await flushPromises()

    const stepCards = wrapper.findAllComponents(StubWizardStepCard)
    const step1Footer = stepCards[0].find('.stub-step-footer')
    const nextBtn = step1Footer.find('button')

    // Button should be disabled
    expect(nextBtn.attributes('disabled')).toBeDefined()

    // Validation message should be shown
    expect(stepCards[0].find('.wizard__validation-msg').exists()).toBe(true)
  })

  // ── 5. Step completion flow - completing step 1 enables step 2 ──

  it('completing step 1 enables step 2', async () => {
    const wrapper = mountWizard({
      canProceed: vi.fn((n: number) => {
        if (n === 1) return true
        return false
      }),
      stepValidation: vi.fn(() => []),
    })
    await flushPromises()

    // Complete step 1
    const stepCards = wrapper.findAllComponents(StubWizardStepCard)
    const step1Footer = stepCards[0].find('.stub-step-footer')
    const nextBtn = step1Footer.find('button')
    await nextBtn.trigger('click')
    await flushPromises()

    // Step 2 should now be active (not locked)
    const updatedCards = wrapper.findAllComponents(StubWizardStepCard)
    expect(updatedCards[1].props('status')).toBe('active')
    expect(updatedCards[1].props('collapsed')).toBe(false)
  })

  // ── 6. Renders mobile bottom navigation ─────────────────────

  it('renders mobile bottom navigation with 5 step buttons', async () => {
    const wrapper = mountWizard()
    await flushPromises()

    const mobileNav = wrapper.find('.wizard__mobile-nav')
    expect(mobileNav.exists()).toBe(true)

    const navSteps = mobileNav.findAll('.wizard__mobile-nav__step')
    expect(navSteps).toHaveLength(5)

    // Step 1 should be active
    expect(navSteps[0].classes()).toContain('wizard__mobile-nav__step--active')

    // Step labels
    const labels = navSteps.map(s => s.find('.wizard__mobile-nav__label').text())
    expect(labels).toEqual(['场景', '输入', '处理', '输出', '导出'])
  })

  it('marks completed steps as done in mobile navigation', async () => {
    const wrapper = mountWizard({
      canProceed: vi.fn((n: number) => n <= 1),
      stepValidation: vi.fn(() => []),
    })
    await flushPromises()

    // Complete step 1 to move to step 2
    const stepCards = wrapper.findAllComponents(StubWizardStepCard)
    const step1Footer = stepCards[0].find('.stub-step-footer')
    const nextBtn = step1Footer.find('button')
    await nextBtn.trigger('click')
    await flushPromises()

    const mobileNav = wrapper.find('.wizard__mobile-nav')
    const navSteps = mobileNav.findAll('.wizard__mobile-nav__step')

    // Step 1 should be done
    expect(navSteps[0].classes()).toContain('wizard__mobile-nav__step--done')
    // Step 2 should be active
    expect(navSteps[1].classes()).toContain('wizard__mobile-nav__step--active')
  })

  // ── 7. Accordion behavior - collapsed steps show summary ────

  it('collapsed steps show summary text', async () => {
    const wrapper = mountWizard({
      canProceed: vi.fn((n: number) => n <= 1),
      stepValidation: vi.fn(() => []),
      scene: { name: '测试场景', description: '', version: '' },
    })
    await flushPromises()

    // Complete step 1 to move to step 2
    const stepCards = wrapper.findAllComponents(StubWizardStepCard)
    const step1Footer = stepCards[0].find('.stub-step-footer')
    const nextBtn = step1Footer.find('button')
    await nextBtn.trigger('click')
    await flushPromises()

    // Step 1 should now be collapsed and show summary
    const updatedCards = wrapper.findAllComponents(StubWizardStepCard)
    expect(updatedCards[0].props('collapsed')).toBe(true)
    expect(updatedCards[0].props('summary')).toContain('测试场景')
  })

  it('current step is never collapsed', async () => {
    const wrapper = mountWizard()
    await flushPromises()

    const stepCards = wrapper.findAllComponents(StubWizardStepCard)
    // Step 1 is the current step, should not be collapsed
    expect(stepCards[0].props('collapsed')).toBe(false)
  })

  it('clicking header on completed step toggles expanded state', async () => {
    const wrapper = mountWizard({
      canProceed: vi.fn((n: number) => n <= 1),
      stepValidation: vi.fn(() => []),
      scene: { name: '测试场景', description: '', version: '' },
    })
    await flushPromises()

    // Complete step 1
    const stepCards = wrapper.findAllComponents(StubWizardStepCard)
    const step1Footer = stepCards[0].find('.stub-step-footer')
    const nextBtn = step1Footer.find('button')
    await nextBtn.trigger('click')
    await flushPromises()

    // Step 1 is now collapsed (completed, current step is 2)
    let updatedCards = wrapper.findAllComponents(StubWizardStepCard)
    expect(updatedCards[0].props('collapsed')).toBe(true)

    // Click header on step 1 to expand it
    const step1Header = updatedCards[0].find('.stub-step-header')
    await step1Header.trigger('click')
    await flushPromises()

    // Step 1 should now be expanded
    updatedCards = wrapper.findAllComponents(StubWizardStepCard)
    expect(updatedCards[0].props('collapsed')).toBe(false)
  })
})
