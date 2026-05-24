import { ref, watch, onUnmounted } from 'vue'

export function useTypewriter(text: () => string, speed = 20) {
  const displayText = ref('')
  const isTyping = ref(false)
  let timer: ReturnType<typeof setInterval> | null = null

  function startTyping(fullText: string) {
    stopTyping()
    if (!fullText) return
    displayText.value = ''
    isTyping.value = true
    let i = 0
    timer = setInterval(() => {
      i++
      displayText.value = fullText.slice(0, i)
      if (i >= fullText.length) {
        stopTyping()
      }
    }, speed)
  }

  function stopTyping() {
    if (timer) { clearInterval(timer); timer = null }
    isTyping.value = false
  }

  function finish() {
    stopTyping()
    displayText.value = text()
  }

  onUnmounted(stopTyping)

  return { displayText, isTyping, startTyping, finish }
}
