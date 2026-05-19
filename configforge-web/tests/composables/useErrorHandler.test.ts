import { describe, it, expect, beforeEach } from 'vitest'
import { useErrorHandler } from '../../src/composables/useErrorHandler'

describe('useErrorHandler', () => {
  const handler = useErrorHandler()

  beforeEach(() => {
    handler.clearAll()
  })

  it('starts with no errors', () => {
    expect(handler.warning.value).toBeNull()
    expect(handler.error.value).toBeNull()
    expect(handler.fatal.value).toBeNull()
  })

  it('sets error for non-fatal API error', () => {
    handler.handleApiError({ message: '请求超时', code: 'TIMEOUT' })
    expect(handler.error.value).toBe('请求超时')
    expect(handler.fatal.value).toBeNull()
  })

  it('sets fatal for INTERNAL_ERROR', () => {
    handler.handleApiError({ message: '服务器崩溃', code: 'INTERNAL_ERROR' })
    expect(handler.fatal.value).toBe('服务器崩溃')
    expect(handler.error.value).toBeNull()
  })

  it('clearAll resets all levels', () => {
    handler.handleApiError({ message: 'e1', code: 'TIMEOUT' })
    handler.handleApiError({ message: 'e2', code: 'INTERNAL_ERROR' })
    handler.clearAll()
    expect(handler.error.value).toBeNull()
    expect(handler.fatal.value).toBeNull()
    expect(handler.warning.value).toBeNull()
  })

  it('can manually set warning', () => {
    handler.warning.value = '低磁盘空间'
    expect(handler.warning.value).toBe('低磁盘空间')
  })
})
