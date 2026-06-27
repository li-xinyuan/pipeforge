import { ref } from 'vue'
import { registerSW } from 'virtual:pwa-register'

/**
 * PWA service worker registration and update management.
 *
 * - `needRefresh`: true when a new SW version is waiting to activate.
 *   The UI should show an update prompt when this is true.
 * - `offlineReady`: true when the app is cached and usable offline.
 * - `update()`: triggers SW activation + page reload.
 * - `close()`: dismisses the update prompt (user can update later).
 */
const needRefresh = ref(false)
const offlineReady = ref(false)

let swRegistration: ReturnType<typeof registerSW> | null = null

function initPwa(): void {
  if (swRegistration) return // already initialized
  swRegistration = registerSW({
    immediate: true,
    onNeedRefresh() {
      needRefresh.value = true
    },
    onOfflineReady() {
      offlineReady.value = true
    },
  })
}

async function update(): Promise<void> {
  if (swRegistration) {
    await swRegistration()
  }
}

function close(): void {
  needRefresh.value = false
}

export function usePwa() {
  return {
    needRefresh,
    offlineReady,
    initPwa,
    update,
    close,
  }
}
