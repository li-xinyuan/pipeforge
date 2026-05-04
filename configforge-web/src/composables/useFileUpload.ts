import { ref } from 'vue'
import type { UploadedFileMeta } from '../types/wizard'

export function useFileUpload() {
  const uploading = ref(false)
  const error = ref<string | null>(null)

  async function upload(file: File): Promise<UploadedFileMeta | null> {
    uploading.value = true
    error.value = null
    try {
      const form = new FormData()
      form.append('file', file)
      const resp = await fetch('/api/files/upload', { method: 'POST', body: form })
      if (!resp.ok) {
        const data = await resp.json()
        error.value = data.error || 'Upload failed'
        return null
      }
      const data = await resp.json()
      return { fileId: data.file_id, originalName: data.original_name }
    } catch (e) {
      error.value = 'Network error'
      return null
    } finally {
      uploading.value = false
    }
  }

  return { uploading, error, upload }
}
