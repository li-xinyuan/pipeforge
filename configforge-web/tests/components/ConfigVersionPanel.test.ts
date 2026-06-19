import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfigVersionPanel from '../../src/components/config/ConfigVersionPanel.vue'

// Mock naive-ui
vi.mock('naive-ui', () => ({
  NButton: { template: '<button @click="$emit(\'click\')"><slot /></button>', emits: ['click'] },
  NTag: { template: '<span><slot /></span>' },
  NSelect: { template: '<select><slot /></select>' },
  useDialog: () => ({
    warning: ({ onPositiveClick }: { onPositiveClick: () => void }) => onPositiveClick(),
  }),
  useMessage: () => ({
    success: vi.fn(),
    error: vi.fn(),
  }),
}))

const mockVersions = [
  {
    version: 2,
    scene_version: '1.1',
    change_summary: '添加新输入源',
    created_at: '2026-06-18T10:00:00',
    input_count: 2,
    processor_count: 1,
    output_type: 'excel',
  },
  {
    version: 1,
    scene_version: '1.0',
    change_summary: '',
    created_at: '2026-06-17T08:00:00',
    input_count: 1,
    processor_count: 1,
    output_type: 'csv',
  },
]

describe('ConfigVersionPanel', () => {
  beforeEach(() => {
    // Default mock: return empty array to prevent real network requests
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 })
    )
  })

  it('renders version history header', () => {
    const wrapper = mount(ConfigVersionPanel, {
      props: { configId: 'test-config-1', currentVersion: 2 },
    })
    expect(wrapper.text()).toContain('版本历史')
  })

  it('shows current version number', () => {
    const wrapper = mount(ConfigVersionPanel, {
      props: { configId: 'test-config-1', currentVersion: 3 },
    })
    expect(wrapper.text()).toContain('v3')
  })

  it('shows loading state initially', () => {
    const wrapper = mount(ConfigVersionPanel, {
      props: { configId: 'test-config-1', currentVersion: 2 },
    })
    const text = wrapper.text()
    expect(text.includes('加载中') || text.includes('暂无历史版本')).toBe(true)
  })

  it('shows empty state when no versions', async () => {
    const wrapper = mount(ConfigVersionPanel, {
      props: { configId: 'test-config-1', currentVersion: 2 },
    })
    await new Promise(r => setTimeout(r, 50))
    expect(wrapper.text()).toContain('暂无历史版本')
  })

  it('renders version list after loading', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(mockVersions), { status: 200 })
    )
    const wrapper = mount(ConfigVersionPanel, {
      props: { configId: 'test-config-1', currentVersion: 2 },
    })
    await new Promise(r => setTimeout(r, 50))
    expect(wrapper.text()).toContain('v2')
    expect(wrapper.text()).toContain('v1')
  })

  it('renders version diff section when versions >= 2', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(mockVersions), { status: 200 })
    )
    const wrapper = mount(ConfigVersionPanel, {
      props: { configId: 'test-config-1', currentVersion: 2 },
    })
    await new Promise(r => setTimeout(r, 50))
    expect(wrapper.text()).toContain('版本对比')
  })
})
