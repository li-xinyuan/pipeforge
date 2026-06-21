import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'
import { useBreakpoint } from '../../src/composables/useBreakpoint'

function createMatchMedia(matches: boolean) {
  const mql = {
    matches,
    media: '',
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
  }
  return mql
}

function mountWithBreakpoint() {
  const Wrapper = defineComponent({
    setup() {
      const { breakpoint } = useBreakpoint()
      return () => h('div', { 'data-breakpoint': breakpoint.value })
    },
  })
  return mount(Wrapper)
}

describe('useBreakpoint', () => {
  let originalMatchMedia: typeof window.matchMedia
  let tabletMql: ReturnType<typeof createMatchMedia>
  let mobileMql: ReturnType<typeof createMatchMedia>

  beforeEach(() => {
    originalMatchMedia = window.matchMedia
  })

  afterEach(() => {
    window.matchMedia = originalMatchMedia
    vi.restoreAllMocks()
  })

  function setupMatchMedia(tabletMatches: boolean, mobileMatches: boolean) {
    tabletMql = createMatchMedia(tabletMatches)
    mobileMql = createMatchMedia(mobileMatches)
    window.matchMedia = vi.fn((query: string) => {
      if (query.includes('767')) return mobileMql
      return tabletMql
    })
  }

  it('defaults to desktop when no media query matches', () => {
    setupMatchMedia(false, false)
    const wrapper = mountWithBreakpoint()
    expect(wrapper.vm.$el.dataset.breakpoint).toBe('desktop')
    wrapper.unmount()
  })

  it('detects tablet breakpoint', async () => {
    setupMatchMedia(true, false)
    const wrapper = mountWithBreakpoint()
    // The composable's onMounted calls update() which reads mql.matches
    // We need to get the update callback that was registered
    const updateFn = tabletMql.addEventListener.mock.calls[0]?.[1] as (() => void) | undefined
    if (updateFn) {
      await nextTick()
    }
    expect(wrapper.vm.$el.dataset.breakpoint).toBe('tablet')
    wrapper.unmount()
  })

  it('detects mobile breakpoint (takes priority over tablet)', async () => {
    setupMatchMedia(true, true)
    const wrapper = mountWithBreakpoint()
    await nextTick()
    expect(wrapper.vm.$el.dataset.breakpoint).toBe('mobile')
    wrapper.unmount()
  })

  it('registers change listeners on both media queries', () => {
    setupMatchMedia(false, false)
    const wrapper = mountWithBreakpoint()
    expect(tabletMql.addEventListener).toHaveBeenCalledWith('change', expect.any(Function))
    expect(mobileMql.addEventListener).toHaveBeenCalledWith('change', expect.any(Function))
    wrapper.unmount()
  })

  it('removes change listeners on unmount', () => {
    setupMatchMedia(false, false)
    const wrapper = mountWithBreakpoint()
    wrapper.unmount()
    expect(tabletMql.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function))
    expect(mobileMql.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function))
  })

  it('updates breakpoint when media query change event fires', async () => {
    setupMatchMedia(false, false)
    const wrapper = mountWithBreakpoint()
    expect(wrapper.vm.$el.dataset.breakpoint).toBe('desktop')

    // Get the update callback registered on the tablet media query
    const updateFn = tabletMql.addEventListener.mock.calls[0][1] as () => void

    // Simulate switching to tablet
    tabletMql.matches = true
    updateFn()
    await nextTick()
    expect(wrapper.vm.$el.dataset.breakpoint).toBe('tablet')

    // Simulate switching to mobile
    mobileMql.matches = true
    const mobileUpdateFn = mobileMql.addEventListener.mock.calls[0][1] as () => void
    mobileUpdateFn()
    await nextTick()
    expect(wrapper.vm.$el.dataset.breakpoint).toBe('mobile')

    wrapper.unmount()
  })
})
