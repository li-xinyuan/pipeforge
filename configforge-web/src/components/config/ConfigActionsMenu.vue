<template>
  <NDropdown trigger="click" :options="menuOptions" @select="(key: string) => $emit('select', key)">
    <NButton text size="tiny" class="home__menu-btn" style="min-width: 44px; min-height: 44px;" aria-label="更多操作">···</NButton>
  </NDropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NDropdown } from 'naive-ui'
import type { SavedConfig } from '../../types/wizard'

const props = defineProps<{
  config: SavedConfig
  canEdit?: boolean
}>()

defineEmits<{
  select: [key: string]
}>()

const menuOptions = computed(() => [
  { label: '编辑', key: 'edit' },
  { label: '版本历史', key: 'versions' },
  { label: '下载 YAML', key: 'download' },
  { label: '导出配置', key: 'export_yaml' },
  { label: '导出为 JSON', key: 'export_json' },
  ...(props.canEdit !== false ? [{ label: '删除', key: 'delete' }] : []),
])
</script>
