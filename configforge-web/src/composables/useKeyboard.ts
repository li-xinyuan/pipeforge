import { onMounted, onUnmounted } from 'vue'

export function useKeyboard(handlers: Record<string, (e: KeyboardEvent) => void>) {
  function handleKeyDown(e: KeyboardEvent) {
    // 构建快捷键标识：Ctrl+S, Ctrl+Enter, Escape, Ctrl+1~5
    let key = ''
    if (e.ctrlKey || e.metaKey) key += 'Ctrl+'
    if (e.shiftKey) key += 'Shift+'
    key += e.key

    const handler = handlers[key]
    if (handler) {
      e.preventDefault()
      handler(e)
    }
  }

  onMounted(() => document.addEventListener('keydown', handleKeyDown))
  onUnmounted(() => document.removeEventListener('keydown', handleKeyDown))
}
