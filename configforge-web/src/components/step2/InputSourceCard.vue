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
      <span v-if="input.plugin === 'csv'" class="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded">CSV</span>
      <span v-else class="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded">Excel</span>
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
      <!-- File upload -->
      <div>
        <label class="block text-xs font-medium text-slate-500 mb-1">文件</label>
        <template v-if="input.fileId && store.uploadedFiles[input.fileId]">
          <div class="flex items-center gap-1">
            <span class="text-xs text-green-700 bg-green-50 border border-green-200 rounded px-2 py-1 truncate flex-1">✓ {{ store.uploadedFiles[input.fileId].originalName }}</span>
            <button @click="removeFile" class="text-slate-400 hover:text-red-500 p-0.5 flex-shrink-0" title="移除文件">&times;</button>
          </div>
        </template>
        <div v-else @click="triggerUpload" class="border-2 border-dashed border-slate-200 rounded-md p-2 text-center cursor-pointer bg-slate-50 hover:border-blue-500 hover:bg-blue-50 transition-colors">
          <div v-if="uploading" class="text-xs text-slate-500">上传中...</div>
          <div v-else class="text-xs text-slate-400">{{ input.plugin === 'csv' ? '📎 点击上传 CSV' : '📎 点击上传 Excel' }}</div>
          <input type="file" ref="fileInput" class="hidden" :accept="input.plugin === 'csv' ? '.csv' : '.xlsx,.xls'" @change="onFileSelected" />
        </div>
        <p v-if="uploadError" class="text-xs text-red-500 mt-1">{{ uploadError }}</p>
      </div>

      <!-- Sheet name (Excel) -->
      <div v-if="input.plugin === 'excel'">
        <label class="block text-xs font-medium text-slate-500 mb-1">工作表</label>
        <select
          v-if="sheetNames.length > 0"
          :value="(input.config as ExcelInputConfig).sheet"
          @change="$emit('update', { ...input, config: { ...input.config, sheet: ($event.target as HTMLSelectElement).value } })"
          class="w-full text-sm border border-slate-200 rounded-md px-2 py-1.5 focus:outline-none focus:border-blue-500 bg-white"
        >
          <option v-for="s in sheetNames" :key="s" :value="s">{{ s }}</option>
        </select>
        <input
          v-else
          :value="(input.config as ExcelInputConfig).sheet"
          @input="$emit('update', { ...input, config: { ...input.config, sheet: ($event.target as HTMLInputElement).value } })"
          placeholder="Sheet1"
          class="w-full text-sm border border-slate-200 rounded-md px-2 py-1.5 focus:outline-none focus:border-blue-500"
        />
      </div>

      <!-- CSV config fields -->
      <template v-if="input.plugin === 'csv'">
        <!-- Delimiter -->
        <div>
          <label class="block text-xs font-medium text-slate-500 mb-1">分隔符</label>
          <input
            :value="(input.config as CsvInputConfig).delimiter"
            @input="$emit('update', { ...input, config: { ...input.config, delimiter: ($event.target as HTMLInputElement).value } })"
            placeholder=","
            class="w-full text-sm border border-slate-200 rounded-md px-2 py-1.5 focus:outline-none focus:border-blue-500"
          />
        </div>
        <!-- Encoding -->
        <div>
          <label class="block text-xs font-medium text-slate-500 mb-1">编码</label>
          <select
            :value="(input.config as CsvInputConfig).encoding"
            @change="$emit('update', { ...input, config: { ...input.config, encoding: ($event.target as HTMLSelectElement).value } })"
            class="w-full text-sm border border-slate-200 rounded-md px-2 py-1.5 focus:outline-none focus:border-blue-500 bg-white"
          >
            <option value="utf-8">UTF-8</option>
            <option value="gbk">GBK</option>
          </select>
        </div>
        <!-- Has header -->
        <div class="flex items-center gap-2 pt-5">
          <input
            type="checkbox"
            :checked="(input.config as CsvInputConfig).hasHeader"
            @change="$emit('update', { ...input, config: { ...input.config, hasHeader: ($event.target as HTMLInputElement).checked } })"
            class="rounded border-slate-300"
          />
          <label class="text-xs font-medium text-slate-500">包含表头</label>
        </div>
      </template>

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
      <div class="flex items-center gap-2 mb-2">
        <button
          v-if="!previewData"
          @click="loadPreview"
          :disabled="previewLoading"
          class="text-xs text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50"
        >{{ previewLoading ? '加载中...' : '加载列预览' }}</button>
        <template v-else>
          <button
            @click="previewVisible = !previewVisible"
            class="text-xs text-blue-600 hover:text-blue-700 font-medium"
          >{{ previewVisible ? '收起预览' : '展开预览' }}</button>
        </template>
      </div>
      <p v-if="error && !previewLoading" class="text-xs text-red-500 mb-2">{{ error.message }}</p>
      <ColumnPreview v-if="previewData && previewVisible" :columns="previewData.columns" :rows="previewData.rows" />
    </div>
    <p v-else class="text-xs text-slate-400 mt-2">请先上传文件以加载列预览</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import type { InputSource, CsvInputConfig, ExcelInputConfig } from '../../types/wizard'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi } from '../../composables/useWizardApi'
import { useFileUpload } from '../../composables/useFileUpload'
import ColumnPreview from './ColumnPreview.vue'

const props = defineProps<{
  input: InputSource
  index: number
}>()

const emit = defineEmits<{
  remove: []
  update: [input: InputSource]
}>()

const store = useWizardStore()
const { fetchPreview, error } = useWizardApi()
const { uploading, error: uploadError, upload } = useFileUpload()
const fileInput = ref<HTMLInputElement>()
const previewData = ref<{ columns: string[]; rows: string[][] } | null>(null)
const previewVisible = ref(false)
const previewLoading = ref(false)
const sheetNames = ref<string[]>([])
let tableSeq = 0

onMounted(async () => {
  if (props.input.fileId) {
    const data = await fetchPreview(props.input.fileId)
    if (data) sheetNames.value = data.sheets
  }
})

watch(() => props.input.config.sheet, () => {
  if (previewVisible.value) loadPreview()
})

function generateTableName(originalName: string): string {
  const base = originalName.replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9一-鿿_]/g, '_')
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  tableSeq++
  return `${base}_${date}_${tableSeq}`
}

function triggerUpload() { fileInput.value?.click() }

async function onFileSelected(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (!files || files.length === 0) return
  const meta = await upload(files[0])
  if (meta) {
    store.addFileRef(meta.fileId, meta)
    const data = await fetchPreview(meta.fileId)
    if (data) {
      sheetNames.value = data.sheets
      if (props.input.plugin === 'excel') {
        emit('update', {
          ...props.input,
          fileId: meta.fileId,
          config: { ...props.input.config, sheet: data.sheets[0] || 'Sheet1' },
          table: generateTableName(meta.originalName)
        })
      } else {
        emit('update', {
          ...props.input,
          fileId: meta.fileId,
          table: generateTableName(meta.originalName)
        })
      }
    } else {
      emit('update', { ...props.input, fileId: meta.fileId })
    }
  }
}

function removeFile() {
  sheetNames.value = []
  previewData.value = null
  previewVisible.value = false
  if (props.input.plugin === 'excel') {
    emit('update', { ...props.input, fileId: '', config: { ...props.input.config, sheet: '' }, table: '' })
  } else {
    emit('update', { ...props.input, fileId: '', table: '' })
  }
}

async function loadPreview() {
  if (!props.input.fileId) return
  previewLoading.value = true
  const sheet = props.input.plugin === 'excel' ? (props.input.config as ExcelInputConfig).sheet : undefined
  const data = await fetchPreview(props.input.fileId, sheet)
  if (data) {
    previewData.value = data
    previewVisible.value = true
  }
  previewLoading.value = false
}
</script>
