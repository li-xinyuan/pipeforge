<template>
  <slot v-if="!error" />
  <div v-else class="error-boundary" style="padding: 24px; text-align: center;">
    <h3 style="color: #d03050;">组件渲染出错</h3>
    <p style="color: #666; font-size: 14px;">{{ error.message }}</p>
    <button @click="retry" style="padding: 8px 16px; cursor: pointer;">重试</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'

const error = ref<Error | null>(null)

onErrorCaptured((err) => {
  error.value = err
  return false // 阻止错误继续传播
})

function retry() {
  error.value = null
}
</script>
