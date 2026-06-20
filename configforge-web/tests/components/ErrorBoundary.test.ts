import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ErrorBoundary from '../../src/components/common/ErrorBoundary.vue'

// A component that always throws during render
const ThrowingChild = {
  name: 'ThrowingChild',
  render() {
    throw new Error('Test error from child')
  },
}

// A normal child component
const NormalChild = {
  name: 'NormalChild',
  template: '<p class="normal-content">Hello from child</p>',
}

describe('ErrorBoundary', () => {
  it('renders child components normally when no error', () => {
    const wrapper = mount(ErrorBoundary, {
      slots: { default: NormalChild },
    })
    expect(wrapper.find('.normal-content').exists()).toBe(true)
    expect(wrapper.text()).toContain('Hello from child')
  })

  it('does not show error UI when child renders successfully', () => {
    const wrapper = mount(ErrorBoundary, {
      slots: { default: NormalChild },
    })
    expect(wrapper.find('.error-boundary').exists()).toBe(false)
  })

  it('displays error UI when error ref is set', async () => {
    const wrapper = mount(ErrorBoundary, {
      slots: { default: NormalChild },
    })
    // Manually set error to simulate onErrorCaptured behavior
    wrapper.vm.error = new Error('Test error from child')
    await nextTick()

    expect(wrapper.find('.error-boundary').exists()).toBe(true)
    expect(wrapper.text()).toContain('组件渲染出错')
    expect(wrapper.text()).toContain('Test error from child')
  })

  it('shows retry button when error occurs', async () => {
    const wrapper = mount(ErrorBoundary, {
      slots: { default: NormalChild },
    })
    wrapper.vm.error = new Error('Test error')
    await nextTick()

    expect(wrapper.find('button').exists()).toBe(true)
    expect(wrapper.find('button').text()).toContain('重试')
  })

  it('resets error state when retry button is clicked', async () => {
    const wrapper = mount(ErrorBoundary, {
      slots: { default: NormalChild },
    })
    wrapper.vm.error = new Error('Test error')
    await nextTick()

    // Error UI should be visible
    expect(wrapper.find('.error-boundary').exists()).toBe(true)

    // Click retry button
    await wrapper.find('button').trigger('click')

    // After retry, error ref should be cleared
    expect(wrapper.vm.error).toBeNull()
    // Error UI should be gone, slot should render again
    expect(wrapper.find('.error-boundary').exists()).toBe(false)
  })

  it('onErrorCaptured sets error and prevents propagation', async () => {
    const wrapper = mount(ErrorBoundary, {
      slots: { default: ThrowingChild },
      global: {
        config: { errorHandler: () => {} },
      },
    })
    await nextTick()
    // onErrorCaptured should have set the error
    expect(wrapper.vm.error).toBeTruthy()
    expect(wrapper.vm.error.message).toBe('Test error from child')
  })
})
