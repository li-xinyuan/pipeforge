<template>
  <div class="flex items-center gap-2 px-3 py-2 bg-[var(--color-bg-secondary)] dark:bg-[var(--color-surface-hover)] border-b border-[var(--color-border-light)] dark:border-[var(--color-border)]">
    <span class="text-lg">{{ pluginIcon }}</span>
    <span class="text-sm font-medium truncate flex-1">{{ input.table || '新输入源' }}</span>
    <NTag :type="pluginTagType" size="small">{{ pluginLabel }}</NTag>
    <NTag v-if="isPreviewOnly" type="warning" size="small">仅预览</NTag>
    <NTag v-if="analyzing" type="warning" size="small">AI 分析中...</NTag>
    <NButton text type="error" size="tiny" class="ml-auto" @click="$emit('remove')">删除</NButton>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { InputSource } from '../../types/wizard'
import { NTag, NButton } from 'naive-ui'

const props = defineProps<{
  input: InputSource
  analyzing?: boolean
}>()

defineEmits<{
  remove: []
}>()

const pluginIconMap: Record<string, string> = {
  csv: '🗄', database: '🔌', excel: '📊', json: '📋', xml: '📰', parquet: '📦', api: '🌐',
}

const pluginLabelMap: Record<string, string> = {
  csv: 'CSV', database: 'DB', excel: 'Excel', json: 'JSON', xml: 'XML', parquet: 'Parquet', api: 'API',
}

const pluginTagTypeMap: Record<string, 'info' | 'warning' | 'success' | 'default'> = {
  csv: 'info', database: 'warning', excel: 'success', json: 'default', xml: 'default', parquet: 'default', api: 'info',
}

const pluginIcon = computed(() => pluginIconMap[props.input.plugin] || '📄')
const pluginLabel = computed(() => pluginLabelMap[props.input.plugin] || props.input.plugin)
const pluginTagType = computed(() => pluginTagTypeMap[props.input.plugin] || 'default')

// REST API 输入源仅支持预览，不可执行
const PREVIEW_ONLY_PLUGINS = ['api']
const isPreviewOnly = computed(() => PREVIEW_ONLY_PLUGINS.includes(props.input.plugin))
</script>
