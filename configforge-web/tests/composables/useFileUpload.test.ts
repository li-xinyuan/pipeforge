import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useFileUpload } from '../../src/composables/useFileUpload'

describe('useFileUpload', () => {
  let uploader: ReturnType<typeof useFileUpload>

  beforeEach(() => {
    vi.restoreAllMocks()
    uploader = useFileUpload()
  })

  it('starts idle', () => {
    expect(uploader.uploading.value).toBe(false)
    expect(uploader.error.value).toBeNull()
  })

  it('upload success returns file meta', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ file_id: 'abc123', original_name: 'test.xlsx' }), { status: 200 })
    )
    const file = new File(['fake'], 'test.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const result = await uploader.upload(file)
    expect(result).toEqual({ fileId: 'abc123', originalName: 'test.xlsx' })
    expect(uploader.uploading.value).toBe(false)
    expect(uploader.error.value).toBeNull()
  })

  it('upload failure sets error', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ error: 'File too large' }), { status: 413 })
    )
    const file = new File(['big'], 'huge.xlsx')
    const result = await uploader.upload(file)
    expect(result).toBeNull()
    expect(uploader.error.value).toBe('File too large')
    expect(uploader.uploading.value).toBe(false)
  })

  it('network error sets generic message', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Connection refused'))
    const file = new File(['data'], 'test.xlsx')
    const result = await uploader.upload(file)
    expect(result).toBeNull()
    expect(uploader.error.value).toBe('Network error')
    expect(uploader.uploading.value).toBe(false)
  })
})
