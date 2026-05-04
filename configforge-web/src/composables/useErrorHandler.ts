import { ref } from 'vue'

export function useErrorHandler() {
  const warning = ref<string | null>(null)
  const error = ref<string | null>(null)
  const fatal = ref<string | null>(null)

  function handleApiError(err: { message: string; code: string }) {
    if (err.code === 'INTERNAL_ERROR') fatal.value = err.message
    else error.value = err.message
  }

  function clearAll() { warning.value = null; error.value = null; fatal.value = null }

  return { warning, error, fatal, handleApiError, clearAll }
}
