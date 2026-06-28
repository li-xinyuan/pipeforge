<template>
  <div class="col-span-2">
    <template v-if="input.fileId && store.uploadedFiles[input.fileId]">
      <div class="flex items-center gap-1">
        <NTag type="success" size="small" class="truncate">
          {{ store.uploadedFiles[input.fileId].originalName }}
        </NTag>
        <NButton text size="tiny" type="error" :disabled="analyzing" @click="removeFile">移除</NButton>
      </div>
    </template>
    <NUpload
      v-else
      ref="uploadRef"
      :custom-request="handleUpload"
      :show-file-list="false"
      :accept="fileAcceptAttr"
      class="w-full"
    >
      <div
        :class="['border-2 border-dashed rounded-lg py-5 px-6 text-center cursor-pointer transition-all',
                 uploading ? 'border-slate-300 bg-slate-50'
                 : isDragging ? 'border-teal-500 bg-teal-50/60 scale-[1.01]'
                   : 'border-slate-300 hover:border-teal-400 hover:bg-teal-50/30',
                 { 'pulse-cta': pulseUpload }]"
        @dragenter.prevent="isDragging = true"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="isDragging = false"
      >
        <NSpin v-if="uploading" size="small" />
        <span v-else class="text-3xl block mb-1.5">📤</span>
        <span class="text-sm text-slate-500 dark:text-slate-400 block">
          <template v-if="uploading"><span style="font-size: var(--font-size-xs); color: var(--color-text-muted);">上传中...</span></template>
          <template v-else-if="isDragging"><span class="text-teal-600 dark:text-teal-400 font-medium">松开以上传文件</span></template>
          <template v-else>将文件拖拽到此处，或点击选择文件</template>
        </span>
        <span class="text-xs text-slate-400 dark:text-slate-500 mt-1 block">
          支持 {{ fileAcceptHint }} 格式
        </span>
      </div>
    </NUpload>
    <p v-if="uploadError" class="text-xs text-red-500 mt-1">{{ uploadError }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { InputSource, ExcelInputConfig } from '../../types/wizard'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi } from '../../composables/useWizardApi'
import { useFileUpload } from '../../composables/useFileUpload'
import { NButton, NTag, NUpload, NSpin } from 'naive-ui'
import type { UploadCustomRequestOptions } from 'naive-ui'

const props = defineProps<{
  input: InputSource
  pulseUpload?: boolean
}>()

const emit = defineEmits<{
  update: [input: InputSource]
  'file-ready': [fileId: string]
}>()

const store = useWizardStore()
const { fetchPreview } = useWizardApi()
const { uploading, error: uploadError, upload } = useFileUpload()
const uploadRef = ref()
const isDragging = ref(false)

const fileAcceptMap: Record<string, string> = {
  csv: '.csv',
  excel: '.xlsx,.xls',
  json: '.json',
  xml: '.xml',
  parquet: '.parquet',
}

const fileAcceptHintMap: Record<string, string> = {
  csv: '.csv / .tsv',
  excel: '.xlsx / .xls',
  json: '.json',
  xml: '.xml',
  parquet: '.parquet',
}

const fileAcceptAttr = computed(() => fileAcceptMap[props.input.plugin] || '')
const fileAcceptHint = computed(() => fileAcceptHintMap[props.input.plugin] || '')

// 自动弹出文件选择框（与输出配置 Excel 模板自动弹出行为一致）
onMounted(() => {
  if (props.input.fileId) return
  setTimeout(() => {
    const el = (uploadRef.value as { $el?: HTMLElement } | undefined)?.$el
    if (!el) return
    const fileInput = el.querySelector('input[type="file"]') as HTMLInputElement | null
    fileInput?.click()
  }, 200)
})

const analyzing = computed(() => false) // placeholder; parent controls analyzing state

function generateTableName(originalName: string): string {
  const base = originalName.replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9一-鿿_]/g, '_')
  const existing = store.inputs.map(inp => inp.table.trim()).filter(Boolean)
  let name = base
  let seq = 0
  while (existing.includes(name)) {
    seq++
    name = `${base}_${seq}`
  }
  return name
}

async function handleUpload({ file, onFinish, onError }: UploadCustomRequestOptions) {
  if (!file.file) return
  const meta = await upload(file.file)
  if (meta) {
    const data = await fetchPreview(meta.fileId)
    store.addFileRef(meta.fileId, {
      ...meta,
      columns: data?.columns,
      sampleRows: data?.rows,
    })
    if (data) {
      if (props.input.plugin === 'excel') {
        emit('update', {
          ...props.input,
          fileId: meta.fileId,
          config: { ...props.input.config, sheet: data.sheets[0] || 'Sheet1' } as ExcelInputConfig,
          table: generateTableName(meta.originalName),
          confirmedAnalysis: undefined,
        })
      } else {
        emit('update', {
          ...props.input,
          fileId: meta.fileId,
          table: generateTableName(meta.originalName),
          confirmedAnalysis: undefined,
        })
      }
    } else {
      emit('update', { ...props.input, fileId: meta.fileId, confirmedAnalysis: undefined })
    }
    emit('file-ready', meta.fileId)
    onFinish()
  } else {
    onError()
  }
}

function removeFile() {
  if (props.input.plugin === 'excel') {
    emit('update', { ...props.input, fileId: '', config: { ...props.input.config, sheet: '' } as ExcelInputConfig, table: '', confirmedAnalysis: undefined })
  } else {
    emit('update', { ...props.input, fileId: '', table: '', confirmedAnalysis: undefined })
  }
}
</script>
