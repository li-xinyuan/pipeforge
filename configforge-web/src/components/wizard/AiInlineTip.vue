<template>
  <div class="ai-inline-tip">
    <span class="ai-inline-tip__icon">⚡</span>
    <span class="ai-inline-tip__message">{{ message }}</span>
    <button
      v-if="showAction && actionLabel"
      type="button"
      class="ai-inline-tip__action"
      @click="$emit('action')"
    >{{ actionLabel }} →</button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  message: string
  showAction?: boolean
  actionLabel?: string
}>()

defineEmits<{ action: [] }>()
</script>

<style scoped>
.ai-inline-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: linear-gradient(135deg, var(--color-primary-bg), var(--color-primary-bg-light));
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
  margin-top: 12px;
}
.ai-inline-tip__icon {
  font-size: 16px;
  flex-shrink: 0;
}
.ai-inline-tip__message {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  flex: 1;
  line-height: 1.5;
}
.ai-inline-tip__action {
  flex-shrink: 0;
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}
.ai-inline-tip__action:hover {
  text-decoration: underline;
}
</style>
