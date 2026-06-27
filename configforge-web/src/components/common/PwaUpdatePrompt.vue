<template>
  <Transition name="pwa-slide">
    <div v-if="needRefresh" class="pwa-prompt">
      <div class="pwa-prompt__icon">↻</div>
      <div class="pwa-prompt__content">
        <p class="pwa-prompt__title">{{ t('pwa.updateTitle') }}</p>
        <p class="pwa-prompt__body">{{ t('pwa.updateBody') }}</p>
      </div>
      <div class="pwa-prompt__actions">
        <NButton size="small" @click="close">{{ t('pwa.laterBtn') }}</NButton>
        <NButton size="small" type="primary" :loading="updating" @click="onUpdate">{{ t('pwa.updateBtn') }}</NButton>
      </div>
    </div>
  </Transition>
  <Transition name="pwa-slide">
    <div v-if="showOfflineReady" class="pwa-prompt pwa-prompt--success">
      <div class="pwa-prompt__icon">✓</div>
      <div class="pwa-prompt__content">
        <p class="pwa-prompt__title">{{ t('pwa.offlineReady') }}</p>
      </div>
      <div class="pwa-prompt__actions">
        <NButton size="small" @click="dismissOfflineReady">{{ t('pwa.laterBtn') }}</NButton>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { NButton } from 'naive-ui'
import { usePwa } from '../../composables/usePwa'

const { t } = useI18n()
const { needRefresh, offlineReady, close, update } = usePwa()
const updating = ref(false)
const showOfflineReady = ref(false)

// Show offline ready notification once, auto-dismiss after 5s
watch(offlineReady, (ready) => {
  if (ready) {
    showOfflineReady.value = true
    setTimeout(() => { showOfflineReady.value = false }, 5000)
  }
})

function dismissOfflineReady() {
  showOfflineReady.value = false
}

async function onUpdate() {
  updating.value = true
  try {
    await update()
  } finally {
    updating.value = false
  }
}
</script>

<style scoped>
.pwa-prompt {
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 380px;
  padding: 14px 16px;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border-light, #e2e8f0);
  border-radius: var(--radius-lg, 12px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.pwa-prompt--success {
  border-color: var(--color-success, #10b981);
}

.pwa-prompt--success .pwa-prompt__icon {
  color: var(--color-success, #10b981);
}

.pwa-prompt__icon {
  flex-shrink: 0;
  font-size: 28px;
  color: var(--color-primary, #4f46e5);
  line-height: 1;
}

.pwa-prompt__content {
  flex: 1;
  min-width: 0;
}

.pwa-prompt__title {
  margin: 0 0 2px;
  font-size: var(--font-size-sm, 14px);
  font-weight: 600;
  color: var(--color-text, #1e293b);
}

.pwa-prompt__body {
  margin: 0;
  font-size: var(--font-size-xs, 12px);
  color: var(--color-text-muted, #64748b);
  line-height: 1.4;
}

.pwa-prompt__actions {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pwa-slide-enter-active,
.pwa-slide-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.pwa-slide-enter-from,
.pwa-slide-leave-to {
  transform: translateY(20px);
  opacity: 0;
}

@media (max-width: 480px) {
  .pwa-prompt {
    left: 12px;
    right: 12px;
    max-width: none;
  }
}
</style>
