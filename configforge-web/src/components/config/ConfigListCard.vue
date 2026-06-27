<template>
  <div v-for="cfg in configs" :key="cfg.id" class="config-card card-lift" :class="{ 'config-card--selected': batchMode && selectedIds.has(cfg.id) }">
    <NCheckbox v-if="batchMode" :checked="selectedIds.has(cfg.id)" class="config-card-check" @update:checked="$emit('toggle-select', cfg.id)" />
    <div class="config-card-left">
      <span class="config-card-icon">📋</span>
      <div class="config-card-info">
        <router-link :to="batchMode ? '' : '/config/new?load=' + cfg.id" class="config-name-link" :class="{ 'config-name-link--disabled': batchMode }">{{ cfg.sceneName }}</router-link>
        <div class="config-card-meta">
          <span class="meta-item">v{{ cfg.currentVersion }}</span>
          <span class="meta-sep">·</span>
          <span class="meta-item">{{ cfg.inputCount }} 个数据源</span>
          <span class="meta-sep">·</span>
          <span class="meta-item">{{ cfg.outputType }}</span>
          <span class="meta-sep">·</span>
          <span class="meta-item">{{ formatTime(cfg.updatedAt) }}</span>
        </div>
      </div>
    </div>
    <div v-if="!batchMode" class="config-card-right">
      <NButton v-if="cfg.inputCount > 0 && canEdit" size="small" secondary type="primary" @click.stop="$emit('execute', cfg)">执行</NButton>
      <ConfigActionsMenu :config="cfg" :can-edit="canEdit" @select="(key: string) => $emit('menu-select', key, cfg)" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { NButton, NCheckbox } from 'naive-ui'
import type { SavedConfig } from '../../types/wizard'
import { formatTime } from '../../utils/format'
import ConfigActionsMenu from './ConfigActionsMenu.vue'

defineProps<{
  configs: SavedConfig[]
  batchMode: boolean
  selectedIds: Set<string>
  canEdit?: boolean
}>()

defineEmits<{
  'toggle-select': [id: string]
  'execute': [cfg: SavedConfig]
  'menu-select': [key: string, cfg: SavedConfig]
}>()
</script>

<style scoped>
.config-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.config-card:hover {
  border-color: var(--color-primary-border);
  box-shadow: var(--shadow-md);
}

.config-card--selected {
  border-color: var(--color-primary) !important;
  background: var(--color-primary-bg) !important;
}

.config-card-check {
  flex-shrink: 0;
  margin-right: 12px;
}

.config-card-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  flex: 1;
}

.config-card-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.config-card-info {
  min-width: 0;
}

.config-card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
  flex-wrap: wrap;
}

.meta-item {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.meta-sep {
  font-size: var(--font-size-xs);
  color: var(--color-border);
}

.config-card-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.config-name-link {
  font-weight: 600;
  font-size: 15px;
  color: var(--color-primary);
  text-decoration: none;
}

.config-name-link:hover {
  text-decoration: underline;
}

.config-name-link--disabled {
  pointer-events: none;
  color: var(--color-text);
}

/* Mobile */
@media (max-width: 767px) {
  .config-card {
    padding: 12px 14px;
    border-radius: var(--radius-md);
  }
  .config-card-icon {
    font-size: 20px;
  }
  .config-card-meta {
    gap: 4px;
  }
  .meta-item {
    font-size: 10px;
  }
  .config-name-link {
    font-size: 14px;
  }
  .config-card-right {
    flex-wrap: wrap;
    gap: 4px;
  }
}
</style>
