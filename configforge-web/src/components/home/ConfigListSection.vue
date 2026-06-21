<template>
  <div v-if="loading" class="home__skeleton">
    <div v-for="n in 3" :key="n" class="home__skeleton-card" />
  </div>

  <NAlert v-else-if="error" type="error" :title="error" />

  <div v-else-if="configs.length > 0" class="home__config-list">
    <!-- Batch action bar -->
    <div v-if="batchMode" class="home__batch-bar">
      <NCheckbox :checked="isAllSelected" :indeterminate="isSomeSelected && !isAllSelected" @update:checked="emit('toggleSelectAll')">全选</NCheckbox>
      <span class="home__batch-count">已选 {{ selectedIds.size }} 项</span>
      <NButton size="small" type="error" :disabled="selectedIds.size === 0" :loading="batchDeleting" @click="emit('batchDelete')">删除选中</NButton>
    </div>

    <ErrorBoundary>
      <ConfigListCard
        :configs="configs"
        :batch-mode="batchMode"
        :selected-ids="selectedIds"
        :can-edit="canEdit"
        @toggle-select="(id: string) => emit('toggleSelect', id)"
        @execute="(cfg: SavedConfig) => emit('execute', cfg)"
        @menu-select="(key: string, cfg: SavedConfig) => emit('menuSelect', key, cfg)"
      />
    </ErrorBoundary>

    <!-- Pagination -->
    <ConfigPagination
      :current-page="currentPage"
      :total-pages="totalPages"
      :page-size="pageSize"
      :page-size-options="pageSizeOptions"
      @page-change="(page: number) => emit('pageChange', page)"
      @page-size-change="(size: number) => emit('pageSizeChange', size)"
      @jump-page="(page: number) => emit('jumpPage', page)"
    />
  </div>

  <div v-else style="text-align: center; padding: 40px 20px; color: var(--color-text-muted);">
    <p style="font-size: 48px; margin-bottom: 12px;">📋</p>
    <p v-if="searchQuery" style="font-size: var(--font-size-base); font-weight: 500; margin-bottom: 8px;">没有找到匹配的配置</p>
    <template v-else>
      <p style="font-size: var(--font-size-base); font-weight: 500; margin-bottom: 8px;">还没有配置</p>
      <p style="font-size: var(--font-size-sm);">点击上方按钮开始创建你的第一个数据管道配置</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { NAlert, NButton, NCheckbox } from 'naive-ui'
import type { SavedConfig } from '../../types/wizard'
import ConfigListCard from '../config/ConfigListCard.vue'
import ErrorBoundary from '../common/ErrorBoundary.vue'
import ConfigPagination from './ConfigPagination.vue'

defineProps<{
  loading: boolean
  error: string
  configs: SavedConfig[]
  batchMode: boolean
  selectedIds: Set<string>
  isAllSelected: boolean
  isSomeSelected: boolean
  canEdit: boolean
  searchQuery: string
  batchDeleting: boolean
  currentPage: number
  totalPages: number
  pageSize: number
  pageSizeOptions: Array<{ label: string; value: number }>
}>()

const emit = defineEmits<{
  toggleSelect: [id: string]
  toggleSelectAll: []
  execute: [config: SavedConfig]
  menuSelect: [key: string, config: SavedConfig]
  batchDelete: []
  pageChange: [page: number]
  pageSizeChange: [size: number]
  jumpPage: [page: number]
}>()
</script>

<style scoped>
.home__skeleton {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.home__skeleton-card {
  height: 64px;
  border-radius: 12px;
  background: linear-gradient(
    90deg,
    var(--color-surface-hover) 25%,
    var(--color-border-light) 50%,
    var(--color-surface-hover) 75%
  );
  background-size: 200% 100%;
  animation: cf-shimmer 1.5s infinite ease-in-out;
}

@keyframes cf-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.home__config-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.home__batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--color-primary-bg);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
  margin-bottom: 4px;
}

.home__batch-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  flex: 1;
}

@media (max-width: 767px) {
  .home__batch-bar {
    flex-wrap: wrap;
    gap: 6px;
  }
}
</style>
