import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAiGuide } from '../../src/composables/useAiGuide'

describe('useAiGuide', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('parseGuideResponse extracts JSON from markdown code block', () => {
    const { parseGuideResponse } = useAiGuide()
    const aiText = '好的！```json\n{"message":"test","actions":[{"label":"OK","value":"ok"}]}\n```'
    const result = parseGuideResponse(aiText)
    expect(result.message).toBe('test')
    expect(result.actions).toHaveLength(1)
    expect(result.actions![0].label).toBe('OK')
  })

  it('parseGuideResponse falls back to whole text as message when no JSON', () => {
    const { parseGuideResponse } = useAiGuide()
    const result = parseGuideResponse('Hello, this is plain text')
    expect(result.message).toBe('Hello, this is plain text')
    expect(result.actions).toBeUndefined()
  })

  it('extractSceneName truncates to 30 chars', () => {
    const { extractSceneName } = useAiGuide()
    const long = '这是一段非常长的用户输入描述超过三十个字符的测试文本'
    expect(extractSceneName(long).length).toBeLessThanOrEqual(33) // 30 + "..."
    const short = '短文本'
    expect(extractSceneName(short)).toBe('短文本')
  })
})
