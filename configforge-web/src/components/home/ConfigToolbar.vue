<template>
  <div class="home__configs-header-right">
    <NInput
      :value="searchQuery"
      placeholder="搜索配置名称..."
      aria-label="搜索配置名称"
      size="small"
      clearable
      class="home__search-input"
      @update:value="onSearchInput"
    >
      <template #prefix>
        <span style="color: var(--color-text-muted);">🔍</span>
      </template>
    </NInput>
    <NButton v-if="!batchMode" size="small" @click="emit('enterBatchMode')">批量管理</NButton>
    <NButton v-else size="small" @click="emit('exitBatchMode')">取消</NButton>
  </div>
</template>

<script setup lang="ts">
import { NButton, NInput } from 'naive-ui'

defineProps<{
  searchQuery: string
  batchMode: boolean
}>()

const emit = defineEmits<{
  'update:searchQuery': [value: string]
  search: []
  enterBatchMode: []
  exitBatchMode: []
}>()

function onSearchInput(val: string) {
  emit('update:searchQuery', val)
  emit('search')
}
</script>

<style scoped>
.home__configs-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  justify-content: flex-end;
}

.home__search-input {
  max-width: 200px;
}

@media (max-width: 767px) {
  .home__search-input {
    max-width: 140px;
  }
}
</style>
