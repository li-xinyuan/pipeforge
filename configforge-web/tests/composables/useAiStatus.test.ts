import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAiStatus } from '../../src/composables/useAiStatus'

const getAiSettings = vi.fn()

vi.mock('../../src/composables/useApi', () => ({
  useApi: () => ({ getAiSettings }),
}))

describe('useAiStatus', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('returns reactive refs with default values', () => {
    const { aiConfigured, aiProvider, aiModel } = useAiStatus()
    expect(aiConfigured.value).toBe(false)
    expect(aiProvider.value).toBe('')
    expect(aiModel.value).toBe('')
  })

  it('sets aiConfigured to true when enabled with api_key', async () => {
    getAiSettings.mockResolvedValueOnce({
      enabled: true,
      api_key: 'sk-123',
      provider: 'openai',
      model: 'gpt-4',
    })
    const { aiConfigured, aiProvider, aiModel, checkStatus } = useAiStatus()
    await checkStatus()
    expect(aiConfigured.value).toBe(true)
    expect(aiProvider.value).toBe('openai')
    expect(aiModel.value).toBe('gpt-4')
  })

  it('sets aiConfigured to false when enabled but no api_key', async () => {
    getAiSettings.mockResolvedValueOnce({
      enabled: true,
      api_key: '',
      provider: 'openai',
      model: 'gpt-4',
    })
    const { aiConfigured, checkStatus } = useAiStatus()
    await checkStatus()
    expect(aiConfigured.value).toBe(false)
  })

  it('sets aiConfigured to false when not enabled', async () => {
    getAiSettings.mockResolvedValueOnce({
      enabled: false,
      api_key: 'sk-123',
      provider: 'openai',
      model: 'gpt-4',
    })
    const { aiConfigured, checkStatus } = useAiStatus()
    await checkStatus()
    expect(aiConfigured.value).toBe(false)
  })

  it('sets aiConfigured to false when api_key is missing', async () => {
    getAiSettings.mockResolvedValueOnce({
      enabled: true,
      provider: 'openai',
      model: 'gpt-4',
    })
    const { aiConfigured, checkStatus } = useAiStatus()
    await checkStatus()
    expect(aiConfigured.value).toBe(false)
  })

  it('sets aiConfigured to false on error', async () => {
    getAiSettings.mockRejectedValueOnce(new Error('Network error'))
    const { aiConfigured, checkStatus } = useAiStatus()
    await checkStatus()
    expect(aiConfigured.value).toBe(false)
  })

  it('does not clear provider/model when not configured', async () => {
    // aiProvider/aiModel are module-level refs; they only get updated when aiConfigured is true
    getAiSettings.mockResolvedValueOnce({
      enabled: false,
      api_key: '',
      provider: 'some-provider',
      model: 'some-model',
    })
    const { aiConfigured, aiProvider, aiModel, checkStatus } = useAiStatus()
    await checkStatus()
    expect(aiConfigured.value).toBe(false)
    // Source code only updates provider/model inside the `if (aiConfigured.value)` block,
    // so they retain whatever value they had before
    expect(aiProvider.value).not.toBe('some-provider')
    expect(aiModel.value).not.toBe('some-model')
  })

  it('markConfigured sets aiConfigured to true', () => {
    const { aiConfigured, markConfigured } = useAiStatus()
    expect(aiConfigured.value).toBe(false)
    markConfigured()
    expect(aiConfigured.value).toBe(true)
  })
})
