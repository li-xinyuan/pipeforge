import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useConversationHistory } from '../../src/composables/useConversationHistory'
import type { ChatMessage } from '../../src/types/wizard'

describe('useConversationHistory', () => {
  let store: Record<string, string> = {}
  beforeEach(() => {
    store = {}
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = value },
      removeItem: (key: string) => { delete store[key] },
    })
  })

  it('saves and loads messages', () => {
    const { saveMessages, loadMessages } = useConversationHistory()
    const configId = 'test-config-1'
    const msgs: ChatMessage[] = [
      { role: 'ai', content: 'Hello', timestamp: Date.now() },
      { role: 'user', content: 'Hi', timestamp: Date.now() },
    ]
    saveMessages(msgs, configId)
    const loaded = loadMessages(configId)
    expect(loaded).toHaveLength(2)
    expect(loaded[0].content).toBe('Hello')
  })

  it('isolates history per config', () => {
    const { saveMessages, loadMessages } = useConversationHistory()
    saveMessages([{ role: 'ai', content: 'Config A', timestamp: Date.now() }], 'config-a')
    saveMessages([{ role: 'ai', content: 'Config B', timestamp: Date.now() }], 'config-b')
    expect(loadMessages('config-a')[0].content).toBe('Config A')
    expect(loadMessages('config-b')[0].content).toBe('Config B')
  })

  it('truncates to 50 messages', () => {
    const { saveMessages, loadMessages } = useConversationHistory()
    const msgs: ChatMessage[] = Array.from({ length: 60 }, (_, i) => ({
      role: i % 2 === 0 ? 'ai' as const : 'user' as const,
      content: `msg ${i}`,
      timestamp: Date.now() + i,
    }))
    saveMessages(msgs, 'test')
    const loaded = loadMessages('test')
    expect(loaded).toHaveLength(50)
    expect(loaded[0].content).toBe('msg 10')
  })

  it('returns empty array when no history', () => {
    const { loadMessages } = useConversationHistory()
    expect(loadMessages('nonexistent')).toEqual([])
  })

  it('clears history', () => {
    const { saveMessages, loadMessages, clearHistory } = useConversationHistory()
    saveMessages([{ role: 'ai', content: 'test', timestamp: Date.now() }], 'test')
    clearHistory('test')
    expect(loadMessages('test')).toEqual([])
  })
})
