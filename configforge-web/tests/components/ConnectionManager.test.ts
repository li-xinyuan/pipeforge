import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ConnectionManager from '../../src/components/common/ConnectionManager.vue'

const mockFetchConnections = vi.fn()
const mockCreateConnection = vi.fn()
const mockTestConnection = vi.fn()
const mockDeleteConnection = vi.fn()
const mockMessage = { success: vi.fn(), error: vi.fn(), warning: vi.fn() }

vi.mock('../../src/composables/useWizardApi', () => ({
  useConnectionApi: () => ({
    fetchConnections: mockFetchConnections,
    createConnection: mockCreateConnection,
    testConnection: mockTestConnection,
    deleteConnection: mockDeleteConnection,
    updateConnection: vi.fn(),
    fetchTables: vi.fn(),
    fetchColumns: vi.fn(),
    connecting: { value: false },
    connectionError: { value: null },
  }),
}))

vi.mock('naive-ui', async () => {
  const actual = await vi.importActual('naive-ui')
  return {
    ...actual,
    useMessage: () => mockMessage,
  }
})

const NButtonStub = {
  template: '<button :disabled="disabled || loading" @click="$emit(\'click\')"><slot /></button>',
  props: ['disabled', 'loading', 'size', 'type', 'text'],
  emits: ['click'],
}

const NInputStub = {
  template: '<input :value="modelValue" @input="$emit(\'update:value\', $event.target.value)" />',
  props: ['modelValue', 'type', 'placeholder', 'size', 'showPasswordToggle'],
  emits: ['update:value'],
}

const NSelectStub = {
  template: '<select :value="value" @change="$emit(\'update:value\', $event.target.value)"><option v-for="opt in options" :key="opt.value" :value="opt.value">{{ opt.label }}</option></select>',
  props: ['value', 'options', 'placeholder', 'disabled', 'size'],
  emits: ['update:value'],
}

const NInputNumberStub = {
  template: '<input type="number" :value="value" @input="$emit(\'update:value\', Number($event.target.value))" />',
  props: ['value', 'min', 'max', 'placeholder', 'size'],
  emits: ['update:value'],
}

describe('ConnectionManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchConnections.mockResolvedValue([])
  })

  function mountComponent() {
    return mount(ConnectionManager, {
      global: {
        stubs: {
          NButton: NButtonStub,
          NInput: NInputStub,
          NSelect: NSelectStub,
          NInputNumber: NInputNumberStub,
        },
      },
    })
  }

  it('renders without crashing', () => {
    const wrapper = mountComponent()
    expect(wrapper.exists()).toBe(true)
  })

  it('shows empty state when no connections', async () => {
    const wrapper = mountComponent()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('暂无连接配置')
  })

  it('shows connection list when connections exist', async () => {
    mockFetchConnections.mockResolvedValue([
      { id: 'c1', name: 'TestDB', dbType: 'sqlite', host: '/tmp/test.db', passwordSet: false, verified: true, createdAt: '', updatedAt: '' },
      { id: 'c2', name: 'MySQL Prod', dbType: 'mysql', host: '10.0.0.1', port: 3306, database: 'prod', username: 'admin', passwordSet: true, verified: false, createdAt: '', updatedAt: '' },
    ])
    const wrapper = mountComponent()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('TestDB')
    expect(wrapper.text()).toContain('MySQL Prod')
  })

  it('shows unverified badge for unverified connections', async () => {
    mockFetchConnections.mockResolvedValue([
      { id: 'c1', name: 'Unverified', dbType: 'sqlite', host: '/tmp/test.db', passwordSet: false, verified: false, createdAt: '', updatedAt: '' },
    ])
    const wrapper = mountComponent()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('⚠')
  })

  it('shows new connection form when button clicked', async () => {
    const wrapper = mountComponent()
    await wrapper.vm.$nextTick()
    // Click the "+ 新建连接" button to show the form
    const addBtn = wrapper.find('button')
    expect(addBtn.exists()).toBe(true)
    await addBtn.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('保存')
  })

  it('shows delete button for each connection', async () => {
    mockFetchConnections.mockResolvedValue([
      { id: 'c1', name: 'TestDB', dbType: 'sqlite', host: '/tmp/test.db', passwordSet: false, verified: true, createdAt: '', updatedAt: '' },
    ])
    const wrapper = mountComponent()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('删除')
  })

  it('has new connection button visible', () => {
    const wrapper = mountComponent()
    expect(wrapper.text()).toContain('新建连接')
  })
})
