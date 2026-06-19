import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DiagnosisPanel from '../../src/components/common/DiagnosisPanel.vue'

const errorDiagnosis = {
  cause: '表名不存在',
  suggestions: ['检查表名拼写', '确认表已创建'],
  severity: 'error' as const,
  step: 3,
}

const warningDiagnosis = {
  cause: '列名可能不匹配',
  suggestions: ['检查列映射'],
  severity: 'warning' as const,
  step: 4,
}

const autofixFixableResult = {
  fixable: true,
  fixes: [
    { step: 3, field: 'sql', old: 'SELECT * FORM users', new: 'SELECT * FROM users', reason: 'SQL关键字拼写错误' },
  ],
}

const autofixNotFixableResult = {
  fixable: false,
  suggestions: ['需要手动修改JOIN关系', '建议重新设计查询逻辑'],
}

const makeWrapper = (props = {}) =>
  mount(DiagnosisPanel, {
    props: { diagnosis: null, ...props },
  })

describe('DiagnosisPanel', () => {
  it('does not render when diagnosis is null', () => {
    const wrapper = makeWrapper({ diagnosis: null })
    expect(wrapper.find('.diagnosis-panel').exists()).toBe(false)
  })

  it('renders when diagnosis is provided', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis })
    expect(wrapper.find('.diagnosis-panel').exists()).toBe(true)
  })

  it('displays AI diagnosis header', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis })
    expect(wrapper.text()).toContain('AI 诊断')
  })

  it('displays cause text', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis })
    expect(wrapper.text()).toContain('表名不存在')
  })

  it('displays suggestions list', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis })
    expect(wrapper.text()).toContain('检查表名拼写')
    expect(wrapper.text()).toContain('确认表已创建')
  })

  it('shows error severity label for error diagnosis', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis })
    expect(wrapper.text()).toContain('严重')
  })

  it('shows warning severity label for warning diagnosis', () => {
    const wrapper = makeWrapper({ diagnosis: warningDiagnosis })
    expect(wrapper.text()).toContain('警告')
  })

  it('applies error border class for error severity', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis })
    expect(wrapper.find('.diagnosis-panel--error').exists()).toBe(true)
  })

  it('applies warning border class for warning severity', () => {
    const wrapper = makeWrapper({ diagnosis: warningDiagnosis })
    expect(wrapper.find('.diagnosis-panel--warning').exists()).toBe(true)
  })

  it('shows goto step button when step is set', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis })
    const gotoButtons = wrapper.findAll('.diagnosis-panel__goto')
    expect(gotoButtons.length).toBeGreaterThan(0)
    expect(gotoButtons[0].text()).toContain('前往修复')
  })

  it('emits gotoStep when goto button is clicked', async () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis })
    const gotoBtn = wrapper.find('.diagnosis-panel__goto')
    await gotoBtn.trigger('click')
    expect(wrapper.emitted('gotoStep')).toBeTruthy()
    expect(wrapper.emitted('gotoStep')![0]).toEqual([3])
  })

  it('does not show goto button when step is 0 or undefined', () => {
    const wrapper = makeWrapper({
      diagnosis: { cause: 'test', suggestions: ['fix'], severity: 'warning' as const, step: 0 },
    })
    expect(wrapper.find('.diagnosis-panel__goto').exists()).toBe(false)
  })

  it('shows autofix button by default', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis })
    expect(wrapper.find('.diagnosis-panel__autofix-btn').exists()).toBe(true)
  })

  it('hides autofix button when hideAutofix is true', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis, hideAutofix: true })
    expect(wrapper.find('.diagnosis-panel__autofix-btn').exists()).toBe(false)
  })

  it('emits autofix when autofix button is clicked', async () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis })
    await wrapper.find('.diagnosis-panel__autofix-btn').trigger('click')
    expect(wrapper.emitted('autofix')).toHaveLength(1)
  })

  it('disables autofix button when loading', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis, autofixLoading: true })
    const btn = wrapper.find('.diagnosis-panel__autofix-btn')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
    expect(btn.text()).toContain('AI 修复中')
  })

  it('shows fixable autofix result with diff', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis, autofixResult: autofixFixableResult })
    expect(wrapper.text()).toContain('AI 建议的修复')
    expect(wrapper.text()).toContain('SQL关键字拼写错误')
    expect(wrapper.text()).toContain('SELECT * FORM users')
    expect(wrapper.text()).toContain('SELECT * FROM users')
  })

  it('shows apply button for fixable result', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis, autofixResult: autofixFixableResult })
    expect(wrapper.find('.diagnosis-panel__apply-btn').exists()).toBe(true)
  })

  it('emits applyFixes when apply button is clicked', async () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis, autofixResult: autofixFixableResult })
    await wrapper.find('.diagnosis-panel__apply-btn').trigger('click')
    expect(wrapper.emitted('applyFixes')).toBeTruthy()
    expect(wrapper.emitted('applyFixes')![0][0]).toEqual(autofixFixableResult.fixes)
  })

  it('shows suggestions for non-fixable result', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis, autofixResult: autofixNotFixableResult })
    expect(wrapper.text()).toContain('无法自动修复')
    expect(wrapper.text()).toContain('需要手动修改JOIN关系')
    expect(wrapper.text()).toContain('建议重新设计查询逻辑')
  })

  it('does not show autofix result when null', () => {
    const wrapper = makeWrapper({ diagnosis: errorDiagnosis, autofixResult: null })
    expect(wrapper.find('.diagnosis-panel__fixes').exists()).toBe(false)
  })
})
