import { ref } from 'vue'
import type { UploadedFileMeta } from '../types/wizard'
import { useApi } from './useApi'

export function useFileUpload() {
  const uploading = ref(false)
  const error = ref<string | null>(null)
  const api = useApi()

  async function upload(file: File): Promise<UploadedFileMeta | null> {
    uploading.value = true
    error.value = null
    try {
      const form = new FormData()
      form.append('file', file)
      const data = await api.uploadFile(form)
      if (!data) {
        error.value = api.error.value?.code === 'NETWORK_ERROR' ? 'Network error' : (api.error.value?.message || 'Upload failed')
        return null
      }
      return { fileId: data.file_id, originalName: data.original_name }
    } catch {
      error.value = 'Network error'
      return null
    } finally {
      uploading.value = false
    }
  }

  return { uploading, error, upload }
}
