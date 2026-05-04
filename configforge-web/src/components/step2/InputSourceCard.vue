<template>
  <div class="bg-white border border-slate-200 rounded-lg p-4">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-4">
      <input
        :value="input.name"
        @input="$emit('update', { ...input, name: ($event.target as HTMLInputElement).value })"
        placeholder="输入源名称"
        class="flex-1 text-sm font-medium text-slate-900 bg-transparent border-0 border-b border-transparent hover:border-slate-200 focus:border-blue-500 focus:outline-none px-1 py-0.5"
      />
      <span class="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded">Excel</span>
      <button
        @click="$emit('remove')"
        class="text-slate-400 hover:text-red-500 transition-colors p-1"
        title="删除输入源"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    </div>

    <!-- Body: Configuration fields -->
    <div class="grid grid-cols-2 gap-3 mb-4">
      <!-- File selector -->
      <div>
        <label class="block text-xs font-medium text-slate-500 mb-1">文件</label>
        <select
          :value="input.fileId"
          @change="$emit('update', { ...input, fileId: ($event.target as HTMLSelectElement).value })"
          class="w-full text-sm border border-slate-200 rounded-md px-2 py-1.5 focus:outline-none focus:border-blue-500"
        >
          <option value="" disabled>选择文件...</option>
          <option v-for="(file, fid) in uploadedFiles" :key="fid" :value="fid">{{ file.originalName }}</option>
        </select>
      </div>

      <!-- Sheet name -->
      <div>
        <label class="block text-xs font-medium text-slate-500 mb-1">工作表</label>
        <input
          :value="input.config.sheet"
          @input="$emit('update', { ...input, config: { ...input.config, sheet: ($event.target as HTMLInputElement).value } })"
          placeholder="Sheet1"
          class="w-full text-sm border border-slate-200 rounded-md px-2 py-1.5 focus:outline-none focus:border-blue-500"
        />
      </div>

      <!-- Table name -->
      <div>
        <label class="block text-xs font-medium text-slate-500 mb-1">表名</label>
        <input
          :value="input.table"
          @input="$emit('update', { ...input, table: ($event.target as HTMLInputElement).value })"
          placeholder="table_name"
          class="w-full text-sm border border-slate-200 rounded-md px-2 py-1.5 focus:outline-none focus:border-blue-500"
        />
      </div>

      <!-- Param key -->
      <div>
        <label class="block text-xs font-medium text-slate-500 mb-1">参数键</label>
        <input
          :value="input.paramKey"
          @input="$emit('update', { ...input, paramKey: ($event.target as HTMLInputElement).value })"
          placeholder="param_key"
          class="w-full text-sm border border-slate-200 rounded-md px-2 py-1.5 focus:outline-none focus:border-blue-500"
        />
      </div>
    </div>

    <!-- Column preview -->
    <div v-if="input.fileId">
      <button
        @click="loadPreview"
        :disabled="previewLoading"
        class="text-xs text-blue-600 hover:text-blue-700 font-medium mb-2 disabled:opacity-50"
      >
        {{ previewLoading ? '加载中...' : previewData ? '刷新预览' : '加载列预览' }}
      </button>
      <ColumnPreview v-if="previewData" :columns="previewData.columns" :rows="previewData.rows" />
      <p v-else-if="!previewLoading" class="text-xs text-slate-400 mt-2">点击上方按钮加载文件列预览</p>
    </div>
    <p v-else class="text-xs text-slate-400 mt-2">请先选择文件以加载列预览</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { InputSource, UploadedFileMeta } from '../../types/wizard'
import { useWizardApi } from '../../composables/useWizardApi'
import ColumnPreview from './ColumnPreview.vue'

const props = defineProps<{
  input: InputSource
  index: number
  uploadedFiles: Record<string, UploadedFileMeta>
}>()

defineEmits<{
  remove: []
  update: [input: InputSource]
}>()

const { fetchPreview } = useWizardApi()
const previewData = ref<{ columns: string[]; rows: string[][] } | null>(null)
const previewLoading = ref(false)

async function loadPreview() {
  if (!props.input.fileId) return
  previewLoading.value = true
  const data = await fetchPreview(props.input.fileId, props.input.config.sheet)
  if (data) previewData.value = data
  previewLoading.value = false
}
</script>
