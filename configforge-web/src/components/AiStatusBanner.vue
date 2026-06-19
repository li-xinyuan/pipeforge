<template>
  <div class="ai-banner">
    <!-- Not configured: prominent warning -->
    <div v-if="!aiConfigured" class="ai-banner__warning">
      <span class="ai-banner__warning-icon" aria-hidden="true">⚙️</span>
      <div class="ai-banner__warning-body">
        <p class="ai-banner__warning-title">AI 模型未配置</p>
        <p class="ai-banner__warning-desc">配置后可启用 AI 辅助 SQL 生成、列映射和场景描述等功能。</p>
      </div>
      <div class="ai-banner__warning-action">
        <NButton size="tiny" type="warning" @click="router.push('/settings')">前往设置</NButton>
      </div>
    </div>

    <!-- Configured: subtle status pill -->
    <div v-else class="ai-banner__status" @click="router.push('/settings')">
      <span class="ai-banner__status-dot" />
      <span class="ai-banner__status-label">AI 助手已就绪</span>
      <NButton text size="tiny" class="ai-banner__status-link" @click.stop="router.push('/settings')">管理 →</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import { useAiStatus } from '../composables/useAiStatus'

const router = useRouter()
const { aiConfigured, aiProvider, aiModel, checkStatus } = useAiStatus()

onMounted(checkStatus)
</script>

<style scoped>
.ai-banner {
  border-bottom: 1px solid var(--color-border-light);
}

/* Warning state */
.ai-banner__warning {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 24px;
  background: var(--color-warning-bg);
  border-bottom: 1px solid var(--color-warning-border);
}

.ai-banner__warning-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.ai-banner__warning-body {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-banner__warning-title {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-warning);
  margin: 0;
  white-space: nowrap;
}

.ai-banner__warning-desc {
  font-size: var(--font-size-xs);
  color: var(--color-warning);
  opacity: 0.75;
  margin: 0;
}

.ai-banner__warning-action {
  flex-shrink: 0;
}

/* Status bar (configured) */
.ai-banner__status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 24px;
  background: var(--color-success-bg);
  border-bottom: 1px solid var(--color-success-border);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.ai-banner__status:hover {
  background: var(--color-success-border);
}

.ai-banner__status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-success);
  flex-shrink: 0;
}

.ai-banner__status-label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-success);
}

.ai-banner__status-info {
  font-size: var(--font-size-xs);
  color: var(--color-success);
  opacity: 0.7;
}

.ai-banner__status-link {
  font-size: var(--font-size-xs) !important;
  color: var(--color-success) !important;
  opacity: 0.7;
  margin-left: auto;
}
</style>
