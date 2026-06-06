import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useWizardStore } from '../../src/stores/wizard'
import SceneInfoForm from '../../src/components/step1/SceneInfoForm.vue'

const makeWrapper = () => mount(SceneInfoForm, {
  global: {
    stubs: {
      NCard: {
        template: '<div class="n-card"><slot /></div>',
      },
      NInput: {
        template: `
          <input
            :id="id"
            :value="value"
            :placeholder="placeholder"
            @input="$emit('update:value', ($event.target as HTMLInputElement).value)"
          />`,
        props: ['value', 'id', 'placeholder'],
        emits: ['update:value'],
      },
    },
  },
})

describe('SceneInfoForm', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders within an NCard wrapper', () => {
    const wrapper = makeWrapper()
    expect(wrapper.find('.n-card').exists()).toBe(true)
  })

  it('renders 3 labels (scene name, version, description)', () => {
    const wrapper = makeWrapper()
    const labels = wrapper.findAll('label')
    expect(labels).toHaveLength(3)
  })

  it('shows red asterisk on required scene name field', () => {
    const wrapper = makeWrapper()
    // The first label should contain "*" for required
    expect(wrapper.findAll('label')[0].text()).toContain('*')
    expect(wrapper.findAll('label')[0].text()).toContain('场景名称')
  })

  it('version and description labels have no asterisk', () => {
    const wrapper = makeWrapper()
    const labels = wrapper.findAll('label')
    expect(labels[1].text()).not.toContain('*')
    expect(labels[2].text()).not.toContain('*')
  })

  it('scene name defaults to empty from store', () => {
    const store = useWizardStore()
    expect(store.scene.name).toBe('')
  })

  it('scene version defaults to 1.0 from store', () => {
    const store = useWizardStore()
    expect(store.scene.version).toBe('1.0')
  })
})
