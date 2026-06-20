<template>
  <button
    class="ai-btn"
    :class="{ 'ai-btn-sm': size === 'small' }"
    :disabled="disabled || loading"
    :style="loading ? { animation: 'none', opacity: '0.6', pointerEvents: 'none' } : {}"
    @click="$emit('click')"
  >
    <span>✨</span>
    <span>{{ loading ? 'AI 思考中...' : label }}</span>
  </button>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  loading?: boolean
  disabled?: boolean
  size?: 'default' | 'small'
}>()

defineEmits<{
  click: []
}>()
</script>
