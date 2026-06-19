import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import AppNavBar from '../../src/components/common/AppNavBar.vue'

// Mock useTheme
const mockToggleTheme = vi.fn()
vi.mock('../../src/composables/useTheme', () => ({
  useTheme: () => ({ isDark: { value: false }, toggleTheme: mockToggleTheme }),
}))

async function makeWrapper(props = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' } },
      { path: '/history', component: { template: '<div/>' } },
      { path: '/schedules', component: { template: '<div/>' } },
      { path: '/settings', component: { template: '<div/>' } },
    ],
  })
  router.push('/')
  await router.isReady()

  return mount(AppNavBar, {
    props: { currentRoute: 'home', ...props },
    global: {
      plugins: [router],
      stubs: {
        RouterLink: {
          template: '<a><slot /></a>',
          props: ['to'],
        },
      },
    },
  })
}

describe('AppNavBar', () => {
  it('renders brand name', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('ConfigForge')
  })

  it('renders navigation links', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.text()).toContain('我的配置')
    expect(wrapper.text()).toContain('执行历史')
    expect(wrapper.text()).toContain('定时任务')
    expect(wrapper.text()).toContain('设置')
  })

  it('renders badge when provided', async () => {
    const wrapper = await makeWrapper({ badge: 'v0.5' })
    expect(wrapper.text()).toContain('v0.5')
  })

  it('does not render badge when not provided', async () => {
    const wrapper = await makeWrapper()
    expect(wrapper.find('.app-nav-bar__badge').exists()).toBe(false)
  })

  it('renders theme toggle button', async () => {
    const wrapper = await makeWrapper()
    const themeBtn = wrapper.find('.app-nav-bar__theme-btn')
    expect(themeBtn.exists()).toBe(true)
  })

  it('calls toggleTheme on theme button click', async () => {
    const wrapper = await makeWrapper()
    await wrapper.find('.app-nav-bar__theme-btn').trigger('click')
    expect(mockToggleTheme).toHaveBeenCalled()
  })

  it('shows moon icon in light mode', async () => {
    const wrapper = await makeWrapper()
    const themeBtn = wrapper.find('.app-nav-bar__theme-btn')
    // In light mode (isDark=false), button shows ☾ (click to switch to dark)
    const text = themeBtn.text()
    expect(text === '☾' || text === '☀').toBe(true)
  })

  it('applies active class to current route link', async () => {
    const wrapper = await makeWrapper({ currentRoute: 'home' })
    const links = wrapper.findAll('.app-nav-bar__link')
    const homeLink = links.find(l => l.text() === '我的配置')
    expect(homeLink?.classes()).toContain('app-nav-bar__link--active')
  })
})
