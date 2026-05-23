import { ref } from 'vue'

const ERROR_MAP: Record<string, string> = {
  FILE_FORMAT_UNSUPPORTED: '文件格式不支持，请上传 .xlsx 或 .csv 格式的文件',
  FILE_TOO_LARGE: '文件过大，最大支持 50MB',
  VALIDATION_ERROR: '输入数据格式不正确，请检查后重试',
  SQL_EXECUTION_ERROR: 'SQL 执行失败，请检查 SQL 语法和列名拼写',
  PATH_TRAVERSAL: '非法的文件访问路径',
  PIPELINE_FAILED: '流水线执行失败，请检查配置',
}

export function useErrorHandler() {
  const warning = ref<string | null>(null)
  const error = ref<string | null>(null)
  const fatal = ref<string | null>(null)
  const errorCode = ref<string | null>(null)
  const errorDetail = ref<string | null>(null)
  const errorMessage = ref<string | null>(null)

  function handleApiError(err: { message: string; code: string }) {
    if (err.code === 'INTERNAL_ERROR') fatal.value = err.message
    else error.value = err.message
  }

  function setError(err: { error?: string; code?: string; detail?: string } | string | null) {
    if (!err) { clearAll(); return }
    if (typeof err === 'string') {
      errorMessage.value = err
      return
    }
    errorCode.value = err.code || null
    errorDetail.value = err.detail || null
    errorMessage.value = (err.code && ERROR_MAP[err.code]) || err.error || '操作失败，请稍后重试'
  }

  function clearAll() { warning.value = null; error.value = null; fatal.value = null; errorCode.value = null; errorDetail.value = null; errorMessage.value = null }

  return { warning, error, fatal, errorCode, errorDetail, errorMessage, handleApiError, setError, clearAll }
}
