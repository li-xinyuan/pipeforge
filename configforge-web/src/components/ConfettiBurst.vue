<template>
  <div v-if="active" class="confetti-container" aria-hidden="true">
    <span v-for="i in 30" :key="i" class="confetti-piece" :style="getStyle(i)" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const active = ref(false)
const colors = ['#0d9488', '#f59e0b', '#6366f1', '#10b981', '#ef4444', '#ec4899', '#14b8a6', '#f97316']

function burst() {
  active.value = true
  setTimeout(() => { active.value = false }, 3000)
}

function getStyle(i: number) {
  const left = Math.random() * 100
  const delay = Math.random() * 0.5
  const size = 6 + Math.random() * 8
  const color = colors[i % colors.length]
  const rotation = Math.random() * 360
  return {
    left: `${left}%`,
    width: `${size}px`,
    height: `${size * 0.6}px`,
    backgroundColor: color,
    animationDelay: `${delay}s`,
    transform: `rotate(${rotation}deg)`,
  }
}

defineExpose({ burst })
</script>

<style scoped>
.confetti-container {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  pointer-events: none; z-index: 9999;
  overflow: hidden;
}
.confetti-piece {
  position: absolute;
  top: -20px;
  border-radius: 2px;
  animation: confetti-fall 2.5s ease-out forwards;
}
@keyframes confetti-fall {
  0%   { top: -20px; opacity: 1; transform: translateX(0) rotate(0deg); }
  100% { top: 100vh; opacity: 0; transform: translateX(40px) rotate(720deg); }
}
</style>
