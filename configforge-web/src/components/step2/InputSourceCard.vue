<template>
  <div class="input-source-card bg-[var(--color-surface)] dark:bg-[var(--color-surface)] border border-[var(--color-border-light)] dark:border-[var(--color-border)] rounded-lg overflow-hidden relative">
    <!-- Header -->
    <InputSourceHeader :input="input" :analyzing="analyzing" @remove="confirmRemove" />

    <!-- Body: Configuration fields -->
    <div class="p-3 cf-form-grid mb-0 relative">
      <!-- File upload (shown for file-based types, not database or api) -->
      <FileUploadSection
        v-if="isFileBasedPlugin"
        :input="input"
        :pulse-upload="pulseUpload"
        @update="handleUpdate"
        @file-ready="(fileId: string) => emit('file-ready', fileId)"
      />

      <!-- API input form (shown for api type only) -->
      <template v-if="input.plugin === 'api'">
        <div class="col-span-2 cf-form-group--full pt-0">
          <ApiForm :input="input" :index="index" @update="handleUpdate" />
        </div>
      </template>

      <!-- AI Analysis inline prompt (full width) -->
      <div v-if="input.fileId && !input.confirmedAnalysis && !analyzing" class="col-span-2">
        <AiTriggerButton label="AI 分析此文件" :loading="analyzing" @click="triggerAiAnalysis" />
      </div>
      <div v-if="input.fileId && !input.confirmedAnalysis && aiError && !analyzing" class="col-span-2 flex items-center gap-2 px-3 py-2 bg-red-50 dark:bg-red-900/30 border border-red-200 rounded-md">
        <span class="text-xs text-red-600 dark:text-red-400 flex-1">{{ aiError }}</span>
        <AiTriggerButton label="重试" @click="triggerAiAnalysis" />
      </div>

      <!-- File input config (Excel/CSV/JSON/XML) -->
      <FileInputForm :input="input" :index="index" :sheet-names="sheetNames" :analyzing="analyzing" @update="handleUpdate" />

      <!-- Database-specific fields -->
      <div v-if="input.plugin === 'database'" class="cf-form-group--full pt-3 border-t border-dashed border-[var(--color-border-light)] dark:border-[var(--color-border)]">
        <DatabaseForm :input="input" :index="index" @update="handleUpdate" />
      </div>

      <!-- Column preview -->
      <ColumnPreviewPanel
        :input="input"
        :preview-data="previewData"
        :api-preview-data="apiPreviewData"
        :preview-visible="previewVisible"
        :preview-loading="previewLoading"
        :error="error"
        @load-preview="loadPreview"
        @load-api-preview="loadApiPreview"
        @toggle-visible="previewVisible = !previewVisible"
      />

      <!-- Table name -->
      <div>
        <label class="cf-label"><span class="cf-required">*</span> 表名</label>
        <NInput
          :id="`input-table-${index}`"
          :value="input.table"
          placeholder="例如：销售数据"
          size="small"
          :status="tableNameError ? 'error' : undefined"
          :disabled="analyzing"
          @update:value="$emit('update', { ...input, table: $event })"
        />
        <p v-if="tableNameError" class="text-xs text-red-500 mt-1">{{ tableNameError }}</p>
        <p v-else class="text-xs text-slate-400 dark:text-slate-500 mt-1">给这个数据源起个名字，方便后续引用</p>
      </div>

      <!-- Param key -->
      <div>
        <label class="cf-label">参数键</label>
        <NInput
          :id="`input-key-${index}`"
          :value="input.paramKey"
          placeholder="例如：date"
          size="small"
          :disabled="analyzing"
          @update:value="$emit('update', { ...input, paramKey: $event })"
        />
        <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">可选，用于定时执行时传入参数</p>
      </div>
    </div>

    <!-- Confirmed AI Analysis & overlay -->
    <ConfirmedAnalysisPanel :confirmed-analysis="input.confirmedAnalysis ?? null" :analyzing="analyzing" />

    <p v-if="!input.fileId && input.plugin !== 'database' && input.plugin !== 'api'" class="text-xs text-slate-400 dark:text-slate-500 mt-2">请先上传文件以加载列预览</p>

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
import type { InputSource, ExcelInputConfig, ApiInputConfig, ConfirmedAnalysis } from '../../types/wizard'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi, useAiApi } from '../../composables/useWizardApi'
import { useApi, ApiError } from '../../composables/useApi'
import { NInput, useDialog } from 'naive-ui'
import AiColumnConfirmModal from './AiColumnConfirmModal.vue'
import AiTriggerButton from '../common/AiTriggerButton.vue'
import DatabaseForm from './DatabaseForm.vue'
import ApiForm from './ApiForm.vue'
import FileInputForm from './FileInputForm.vue'
import InputSourceHeader from './InputSourceHeader.vue'
import ColumnPreviewPanel from './ColumnPreviewPanel.vue'
import FileUploadSection from './FileUploadSection.vue'
import ConfirmedAnalysisPanel from './ConfirmedAnalysisPanel.vue'

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
const { suggesting: analyzing, aiError, askSuggestion } = useAiApi()
const { apiPreview } = useApi()
const previewData = ref<{ columns: string[]; rows: string[][] } | null>(null)
const apiPreviewData = ref<{ columns: string[]; rows: string[][] } | null>(null)
const previewVisible = ref(false)
const previewLoading = ref(false)
const sheetNames = ref<string[]>([])
const modalVisible = ref(false)
const modalParsed = ref<{ columnTypes: Record<string, string>; tableName: string; paramKeys: string[] } | null>(null)
const modalRawText = ref<string | null>(null)
const modalColumns = ref<string[]>([])

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

// File-based plugins (show file upload)
const isFileBasedPlugin = computed(() =>
  ['excel', 'csv', 'json', 'xml', 'parquet'].includes(props.input.plugin)
)

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

onMounted(async () => {
  if (props.input.fileId) {
    const data = await fetchPreview(props.input.fileId)
    if (data) {
      sheetNames.value = data.sheets
      const existing = store.uploadedFiles[props.input.fileId]
      if (existing && (!existing.columns || !existing.sampleRows)) {
        store.addFileRef(props.input.fileId, { ...existing, columns: data.columns, sampleRows: data.rows })
      }
      previewData.value = data
      previewVisible.value = true
    }
  }
})

watch(() => (props.input.config as ExcelInputConfig).sheet, () => {
  if (previewVisible.value) loadPreview()
})

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

async function loadApiPreview() {
  previewLoading.value = true
  apiPreviewData.value = null
  try {
    const cfg = props.input.config as ApiInputConfig
    const result = await apiPreview({
      url: cfg.url,
      method: cfg.method,
      headers: cfg.headers,
      params: cfg.params,
      data_path: cfg.dataPath,
      pagination: cfg.pagination,
      page_size: cfg.pageSize,
      max_pages: cfg.maxPages,
    })
    if (!result) {
      error.value = new ApiError('API 请求失败', 'API_ERROR', 0)
      return
    }
    if (result.columns && result.rows) {
      apiPreviewData.value = { columns: result.columns, rows: result.rows }
      previewVisible.value = true
    }
  } catch (e) {
    error.value = new ApiError(e instanceof Error ? e.message : '网络错误', 'NETWORK_ERROR', 0)
  } finally {
    previewLoading.value = false
  }
}
</script>
