import type { ChatMessage } from '../types/wizard'

const STORAGE_KEY_PREFIX = 'configforge-chat-history'
const MAX_MESSAGES = 50

function getStorageKey(configId?: string | null): string {
  return configId ? `${STORAGE_KEY_PREFIX}-${configId}` : `${STORAGE_KEY_PREFIX}-new`
}

function estimateSize(messages: ChatMessage[]): number {
  return new Blob([JSON.stringify(messages)]).size
}

export function useConversationHistory() {
  function saveMessages(messages: ChatMessage[], configId?: string | null) {
    try {
      let toSave = messages.slice(-MAX_MESSAGES)
      while (estimateSize(toSave) > 4 * 1024 * 1024 && toSave.length > 10) {
        toSave = toSave.slice(-Math.floor(toSave.length / 2))
      }
      localStorage.setItem(getStorageKey(configId), JSON.stringify(toSave))
    } catch { /* ignore */ }
  }

  function loadMessages(configId?: string | null): ChatMessage[] {
    try {
      const raw = localStorage.getItem(getStorageKey(configId))
      return raw ? JSON.parse(raw) : []
    } catch {
      return []
    }
  }

  function clearHistory(configId?: string | null) {
    try { localStorage.removeItem(getStorageKey(configId)) } catch { /* ignore */ }
  }

  return { saveMessages, loadMessages, clearHistory }
}
