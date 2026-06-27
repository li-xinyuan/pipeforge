<template>
  <div v-if="input.fileId || (input.plugin === 'api' && apiPreviewData)" class="col-span-2">
    <div class="flex items-center gap-2 mb-2">
      <span class="cf-label" style="margin-bottom: 0;">列预览</span>
      <NButton
        v-if="!previewData && !apiPreviewData"
        text
        size="tiny"
        :loading="previewLoading"
        @click="input.plugin === 'api' ? $emit('load-api-preview') : $emit('load-preview')"
      >
        {{ previewLoading ? '加载中...' : '加载' }}
      </NButton>
      <NButton
        v-else
        text
        size="tiny"
        @click="$emit('toggle-visible')"
      >
        {{ previewVisible ? '收起' : '展开' }}
      </NButton>
    </div>
    <p v-if="error && !previewLoading" class="text-xs text-red-500 mb-2">{{ error.message }}</p>
    <ColumnPreview v-if="(previewData || apiPreviewData) && previewVisible" :columns="(previewData || apiPreviewData)!.columns" :rows="(previewData || apiPreviewData)!.rows" />
  </div>
</template>

<script setup lang="ts">
import type { InputSource } from '../../types/wizard'
import { NButton } from 'naive-ui'
import ColumnPreview from './ColumnPreview.vue'

defineProps<{
  input: InputSource
  previewData: { columns: string[]; rows: string[][] } | null
  apiPreviewData: { columns: string[]; rows: string[][] } | null
  previewVisible: boolean
  previewLoading: boolean
  error: Error | null
}>()

defineEmits<{
  'load-preview': []
  'load-api-preview': []
  'toggle-visible': []
}>()
</script>
