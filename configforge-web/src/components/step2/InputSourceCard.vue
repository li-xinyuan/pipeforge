<template>
  <div class="input-source-card bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden relative">
    <!-- Header: name + plugin badge + delete -->
    <div class="flex items-center gap-2 px-3 py-2 bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700">
      <span class="text-lg">{{ input.plugin === 'csv' ? '🗄' : input.plugin === 'database' ? '🔌' : '📊' }}</span>
      <span class="text-sm font-medium truncate flex-1">{{ input.table || '新输入源' }}</span>
      <NTag :type="input.plugin === 'csv' ? 'info' : input.plugin === 'database' ? 'warning' : 'success'" size="small">
        {{ input.plugin === 'csv' ? 'CSV' : input.plugin === 'database' ? 'DB' : 'Excel' }}
      </NTag>
      <NTag v-if="analyzing" type="warning" size="small">AI 分析中...</NTag>
      <NButton text type="error" size="tiny" class="ml-auto" @click="confirmRemove">删除</NButton>
    </div>

    <!-- Body: Configuration fields -->
    <div class="p-3 cf-form-grid mb-0 relative">
      <!-- File upload -->
      <div v-if="input.plugin !== 'database'" class="col-span-2">
        <template v-if="input.fileId && store.uploadedFiles[input.fileId]">
          <div class="flex items-center gap-1">
            <NTag type="success" size="small" class="truncate">
              {{ store.uploadedFiles[input.fileId].originalName }}
            </NTag>
            <NButton text size="tiny" type="error" :disabled="analyzing" @click="removeFile">移除</NButton>
          </div>
        </template>
        <NUpload
          ref="uploadRef"
          v-else
          :custom-request="handleUpload"
          :show-file-list="false"
          :accept="input.plugin === 'csv' ? '.csv' : '.xlsx,.xls'"
          class="w-full"
        >
          <div :class="['border-2 border-dashed rounded-lg py-5 px-6 text-center cursor-pointer transition-colors',
               uploading ? 'border-slate-300 bg-slate-50' : 'border-slate-300 hover:border-teal-400 hover:bg-teal-50/30',
               { 'pulse-cta': pulseUpload }]"
          >
              <NSpin v-if="uploading" size="small" />
              <span v-else class="text-3xl block mb-1.5">📤</span>
              <span class="text-sm text-slate-500 dark:text-slate-400 block">
                <template v-if="uploading"><span style="font-size: var(--font-size-xs); color: var(--color-text-muted);">上传中...</span></template>
                <template v-else>将文件拖拽到此处，或点击选择文件</template>
              </span>
              <span class="text-xs text-slate-400 dark:text-slate-500 mt-1 block">
                支持 {{ input.plugin === 'csv' ? '.csv / .tsv' : '.xlsx / .xls' }} 格式
              </span>
          </div>
        </NUpload>
        <p v-if="uploadError" class="text-xs text-red-500 mt-1">{{ uploadError }}</p>
      </div>

      <!-- AI Analysis inline prompt (full width) -->
      <div v-if="input.fileId && !input.confirmedAnalysis && !analyzing" class="col-span-2">
        <AiTriggerButton label="AI 分析此文件" :loading="analyzing" @click="triggerAiAnalysis" />
      </div>
      <div v-if="input.fileId && !input.confirmedAnalysis && aiError && !analyzing" class="col-span-2 flex items-center gap-2 px-3 py-2 bg-red-50 dark:bg-red-900/30 border border-red-200 rounded-md">
        <span class="text-xs text-red-600 dark:text-red-400 flex-1">{{ aiError }}</span>
        <AiTriggerButton label="重试" @click="triggerAiAnalysis" />
      </div>

      <!-- Sheet name (Excel) -->
      <div v-if="input.plugin === 'excel'">
        <label class="cf-label">工作表</label>
        <NSelect
          v-if="sheetNames.length > 0"
          :value="(input.config as ExcelInputConfig).sheet"
          @update:value="$emit('update', { ...input, config: { ...input.config, sheet: $event } as ExcelInputConfig })"
          :options="sheetOptions"
          size="small"
          :disabled="analyzing"
        />
        <NInput
          v-else
          :id="`input-sheet-${index}`"
          :value="(input.config as ExcelInputConfig).sheet"
          @update:value="$emit('update', { ...input, config: { ...input.config, sheet: $event } as ExcelInputConfig })"
          placeholder="Sheet1"
          size="small"
          :disabled="analyzing"
        />
      </div>

      <!-- CSV config fields -->
      <template v-if="input.plugin === 'csv'">
        <!-- Delimiter -->
        <div>
          <label class="cf-label">分隔符</label>
          <NInput
            :value="(input.config as CsvInputConfig).delimiter"
            @update:value="$emit('update', { ...input, config: { ...input.config, delimiter: $event } as CsvInputConfig })"
            placeholder=","
            size="small"
            :disabled="analyzing"
          />
        </div>
        <!-- Encoding -->
        <div>
          <label class="cf-label">编码</label>
          <NSelect
            :value="(input.config as CsvInputConfig).encoding"
            @update:value="$emit('update', { ...input, config: { ...input.config, encoding: $event } as CsvInputConfig })"
            :options="encodingOptions"
            size="small"
            :disabled="analyzing"
          />
        </div>
        <!-- Has header -->
        <div class="flex items-center gap-2" style="padding-top: 22px;">
          <NCheckbox
            :checked="(input.config as CsvInputConfig).hasHeader"
            @update:checked="$emit('update', { ...input, config: { ...input.config, hasHeader: $event } as CsvInputConfig })"
            :disabled="analyzing"
          />
          <span class="cf-label" style="margin-bottom: 0;">包含表头</span>
        </div>
      </template>

      <!-- Database-specific fields -->
      <div v-if="input.plugin === 'database'" class="cf-form-group--full pt-3 border-t border-dashed border-slate-200 dark:border-slate-700">
        <DatabaseForm :input="input" :index="index" @update="handleUpdate" />
      </div>

      <!-- Column preview -->
      <div v-if="input.fileId" class="col-span-2">
        <div class="flex items-center gap-2 mb-2">
          <span class="cf-label" style="margin-bottom: 0;">列预览</span>
          <NButton
            v-if="!previewData"
            text
            size="tiny"
            :loading="previewLoading"
            @click="loadPreview"
          >{{ previewLoading ? '加载中...' : '加载' }}</NButton>
          <NButton
            v-else
            text
            size="tiny"
            @click="previewVisible = !previewVisible"
          >{{ previewVisible ? '收起' : '展开' }}</NButton>
        </div>
        <p v-if="error && !previewLoading" class="text-xs text-red-500 mb-2">{{ error.message }}</p>
        <ColumnPreview v-if="previewData && previewVisible" :columns="previewData.columns" :rows="previewData.rows" />
      </div>

      <!-- Table name -->
      <div>
        <label class="cf-label"><span class="cf-required">*</span> 表名</label>
        <NInput
          :id="`input-table-${index}`"
          :value="input.table"
          @update:value="$emit('update', { ...input, table: $event })"
          placeholder="table_name"
          size="small"
          :status="tableNameError ? 'error' : undefined"
          :disabled="analyzing"
        />
        <p v-if="tableNameError" class="text-xs text-red-500 mt-1">{{ tableNameError }}</p>
      </div>

      <!-- Param key -->
      <div>
        <label class="cf-label">参数键</label>
        <NInput
          :id="`input-key-${index}`"
          :value="input.paramKey"
          @update:value="$emit('update', { ...input, paramKey: $event })"
          placeholder="param_key"
          size="small"
          :disabled="analyzing"
        />
      </div>
    </div>

    <!-- Confirmed AI Analysis -->
    <div v-if="input.confirmedAnalysis" class="mb-4 border border-blue-200 bg-blue-50/40 dark:bg-blue-900/30 rounded-md px-3 py-2">
      <div class="flex items-center gap-2 mb-1.5">
        <span class="text-xs font-medium text-blue-700 dark:text-blue-300">AI 分析确认</span>
      </div>
      <div v-if="Object.keys(input.confirmedAnalysis.columnTypes).length" class="flex flex-wrap gap-1 mb-1.5">
        <NTag
          v-for="(type, col) in input.confirmedAnalysis.columnTypes"
          :key="col"
          size="tiny"
          :bordered="false"
          :type="columnTypeTagType(type)"
        >{{ col }}: {{ type }}</NTag>
      </div>
      <div v-if="input.confirmedAnalysis.paramKeys.length" class="flex flex-wrap gap-1">
        <span class="text-[10px] text-slate-400 dark:text-slate-500 mr-0.5">Keys:</span>
        <NTag
          v-for="key in input.confirmedAnalysis.paramKeys"
          :key="key"
          size="tiny"
          type="info"
        >{{ key }}</NTag>
      </div>
    </div>

    <!-- AI analysis overlay -->
    <div v-if="analyzing" class="absolute inset-0 bg-white/65 dark:bg-slate-800/65 backdrop-blur-sm flex flex-col items-center justify-center gap-3 z-10 rounded-md" style="pointer-events: auto; cursor: wait;">
      <NSpin size="medium" />
      <span class="text-sm text-teal-600 font-medium">AI 分析中...</span>
    </div>

    <p v-if="!input.fileId" class="text-xs text-slate-400 dark:text-slate-500 mt-2">请先上传文件以加载列预览</p>

    <!-- AI Column Confirm Modal -->
    <AiColumnConfirmModal
      :visible="modalVisible"
      :analyzing="analyzing"
      :parsed="modalParsed"
      :raw-text="modalRawText"
      :error-message="aiError"
      :input="input"
      :columns="modalColumns"
      :conflicting-table-names="otherTableNames"
      @confirm="handleModalConfirm"
      @regenerate="handleModalRegenerate"
      @close="handleModalClose"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import type { InputSource, CsvInputConfig, ExcelInputConfig, ConfirmedAnalysis } from '../../types/wizard'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi, useAiApi } from '../../composables/useWizardApi'
import { useFileUpload } from '../../composables/useFileUpload'
import { NInput, NButton, NTag, NUpload, NSelect, NCheckbox, NSpin, useDialog } from 'naive-ui'
import type { UploadCustomRequestOptions } from 'naive-ui'
import ColumnPreview from './ColumnPreview.vue'
import AiColumnConfirmModal from './AiColumnConfirmModal.vue'
import AiTriggerButton from '../common/AiTriggerButton.vue'
import DatabaseForm from './DatabaseForm.vue'

const props = defineProps<{
  input: InputSource
  index: number
  pulseUpload?: boolean
}>()

const emit = defineEmits<{
  remove: []
  update: [input: InputSource]
  'file-ready': [fileId: string]
}>()

const dialog = useDialog()

function confirmRemove() {
  dialog.warning({
    title: '确认删除',
    content: '确定要删除此输入源吗？所有相关配置将丢失。',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: () => emit('remove'),
  })
}

const store = useWizardStore()
const { fetchPreview, error } = useWizardApi()
const { uploading, error: uploadError, upload } = useFileUpload()
const { suggesting: analyzing, aiError, askSuggestion } = useAiApi()
const previewData = ref<{ columns: string[]; rows: string[][] } | null>(null)
const previewVisible = ref(false)
const previewLoading = ref(false)
const sheetNames = ref<string[]>([])
const modalVisible = ref(false)
const modalParsed = ref<{ columnTypes: Record<string, string>; tableName: string; paramKeys: string[] } | null>(null)
const modalRawText = ref<string | null>(null)
const modalColumns = ref<string[]>([])

const encodingOptions = [
  { label: 'UTF-8', value: 'utf-8' },
  { label: 'GBK', value: 'gbk' },
]

const sheetOptions = computed(() => sheetNames.value.map(s => ({ label: s, value: s })))

const otherTableNames = computed(() =>
  store.inputs
    .filter((_, i) => i !== props.index)
    .map(inp => inp.table.trim())
    .filter(Boolean)
)

const tableNameError = computed(() => {
  const name = props.input.table.trim()
  if (!name) return ''
  if (otherTableNames.value.includes(name)) return `表名 "${name}" 已被其他输入源使用`
  return ''
})

function handleUpdate(updated: InputSource) {
  emit('update', updated)
}

function parseColumnsResponse(raw: string): {
  columnTypes: Record<string, string>
  tableName: string
  paramKeys: string[]
} | null {
  try {
    let json = raw
    const jsonMatch = raw.match(/```(?:json)?\s*([\s\S]*?)\s*```/)
    if (jsonMatch) json = jsonMatch[1].trim()

    const parsed = JSON.parse(json)
    const result = Array.isArray(parsed) ? parsed[0] : parsed

    const columnTypes: Record<string, string> = {}
    if (result.columnTypes && typeof result.columnTypes === 'object') {
      for (const [col, type] of Object.entries(result.columnTypes)) {
        columnTypes[col] = String(type)
      }
    } else if (Array.isArray(result.columns)) {
      for (const col of result.columns) {
        if (typeof col === 'string') {
          columnTypes[col] = 'string'
        } else if (col && typeof col === 'object') {
          const cname = col.name || col.column || ''
          if (cname) columnTypes[cname] = col.type || 'string'
        }
      }
    }

    return {
      columnTypes,
      tableName: result.tableName || result.table_name || result.table || '',
      paramKeys: Array.isArray(result.paramKeys)
        ? result.paramKeys.map(String)
        : Array.isArray(result.param_keys)
          ? result.param_keys.map(String)
          : Array.isArray(result.keys)
            ? result.keys.map(String)
            : [],
    }
  } catch {
    return null
  }
}

async function triggerAiAnalysis() {
  const fileMeta = store.uploadedFiles[props.input.fileId]
  if (!fileMeta?.columns) {
    aiError.value = '请先上传文件并等待列信息加载完成'
    return
  }

  modalColumns.value = fileMeta.columns
  modalParsed.value = null
  modalRawText.value = null

  try {
    const result = await askSuggestion('columns', {
      inputs: [{
        name: props.input.table || fileMeta.originalName,
        table: props.input.table,
        columns: fileMeta.columns,
        sampleRows: fileMeta.sampleRows || [],
      }],
    })

    modalVisible.value = true

    if (!result) return

    const parsed = parseColumnsResponse(result)
    if (!parsed) {
      modalRawText.value = result
      return
    }

    modalParsed.value = parsed
  } catch (e) {
    aiError.value = e instanceof Error ? e.message : '分析过程出现异常'
    modalVisible.value = true
  }
}

function handleModalConfirm(confirmed: ConfirmedAnalysis) {
  emit('update', {
    ...props.input,
    table: confirmed.tableName,
    paramKey: confirmed.paramKeys.join(','),
    confirmedAnalysis: confirmed,
  })
  modalVisible.value = false
  modalParsed.value = null
  modalRawText.value = null
}

function handleModalRegenerate() {
  modalParsed.value = null
  modalRawText.value = null
  aiError.value = null
  triggerAiAnalysis()
}

function handleModalClose() {
  modalVisible.value = false
  modalParsed.value = null
  modalRawText.value = null
}

function columnTypeTagType(type: string) {
  switch (type) {
    case 'string': return 'success' as const
    case 'number': return 'info' as const
    case 'date': return 'warning' as const
    case 'boolean': return 'error' as const
    default: return 'default' as const
  }
}

onMounted(async () => {
  if (props.input.fileId) {
    const data = await fetchPreview(props.input.fileId)
    if (data) {
      sheetNames.value = data.sheets
      const existing = store.uploadedFiles[props.input.fileId]
      if (existing && (!existing.columns || !existing.sampleRows)) {
        store.addFileRef(props.input.fileId, { ...existing, columns: data.columns, sampleRows: data.rows })
      }
      // Auto-load and expand preview when file is uploaded
      previewData.value = data
      previewVisible.value = true
    }
  }
})

watch(() => (props.input.config as ExcelInputConfig).sheet, () => {
  if (previewVisible.value) loadPreview()
})

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
      sheetNames.value = data.sheets
      previewData.value = data
      previewVisible.value = true
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
  sheetNames.value = []
  previewData.value = null
  previewVisible.value = false
  if (props.input.plugin === 'excel') {
    emit('update', { ...props.input, fileId: '', config: { ...props.input.config, sheet: '' } as ExcelInputConfig, table: '', confirmedAnalysis: undefined })
  } else {
    emit('update', { ...props.input, fileId: '', table: '', confirmedAnalysis: undefined })
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
