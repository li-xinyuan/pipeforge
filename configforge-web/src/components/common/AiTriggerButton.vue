<template>
  <button
    :class="['ai-trigger-btn', { 'ai-trigger-btn--loading': loading, 'ai-trigger-btn--dark': isDark }]"
    :disabled="disabled || loading"
    @click="$emit('click')"
  >
    <span class="ai-trigger-btn__icon" :class="{ 'ai-trigger-btn__icon--spin': loading }">✨</span>
    <span class="ai-trigger-btn__text">{{ loading ? 'AI 思考中...' : label }}</span>
  </button>
</template>

<script setup lang="ts">
import { useTheme } from '../../composables/useTheme'

defineProps<{
  label: string
  loading?: boolean
  disabled?: boolean
}>()

defineEmits<{
  click: []
}>()

const { isDark } = useTheme()
</script>

<style scoped>
.ai-trigger-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1.5px dashed rgba(13, 148, 136, 0.35);
  background: linear-gradient(135deg, rgba(13, 148, 136, 0.06), rgba(13, 148, 136, 0.12));
  color: #0d9488;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  line-height: 1.4;
}

.ai-trigger-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(13, 148, 136, 0.10), rgba(13, 148, 136, 0.16));
  border-color: rgba(13, 148, 136, 0.50);
  transform: scale(1.02);
}

.ai-trigger-btn:active:not(:disabled) {
  transform: scale(0.97);
}

.ai-trigger-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Dark mode */
.ai-trigger-btn--dark {
  border-color: rgba(94, 234, 212, 0.35);
  background: linear-gradient(135deg, rgba(94, 234, 212, 0.06), rgba(94, 234, 212, 0.12));
  color: #5eead4;
}

.ai-trigger-btn--dark:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(94, 234, 212, 0.10), rgba(94, 234, 212, 0.16));
  border-color: rgba(94, 234, 212, 0.50);
}

/* Icon */
.ai-trigger-btn__icon {
  font-size: 13px;
  line-height: 1;
  flex-shrink: 0;
}

.ai-trigger-btn__icon--spin {
  animation: ai-spin 1s linear infinite;
  display: inline-block;
}

@keyframes ai-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.ai-trigger-btn__text {
  line-height: 1.4;
}
</style>
