<template>
  <NDropdown trigger="click" :options="menuOptions" @select="(key: string) => $emit('select', key)">
    <NButton text size="tiny" class="home__menu-btn" style="min-width: 44px; min-height: 44px;" aria-label="更多操作">···</NButton>
  </NDropdown>
</template>

<script setup lang="ts">
import { NButton, NDropdown } from 'naive-ui'
import type { SavedConfig } from '../../types/wizard'

const props = defineProps<{
  config: SavedConfig
}>()

defineEmits<{
  select: [key: string]
}>()

const menuOptions = [
  { label: '编辑', key: 'edit' },
  { label: '版本历史', key: 'versions' },
  { label: '下载 YAML', key: 'download' },
  { label: '删除', key: 'delete' },
]
</script>
