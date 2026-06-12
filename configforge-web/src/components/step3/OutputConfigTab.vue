<template>
  <div>
    <!-- Output type selector -->
    <p v-if="showOutputTypeChoices" style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 12px;">选择输出格式，配置数据的导出方式</p>
    <div v-if="showOutputTypeChoices" class="grid grid-cols-3 gap-3 mb-5">
      <div
        :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors',
          props.pulseCta ? 'pulse-cta' : '',
          store.output?.plugin === 'excel' ? 'border-green-600 bg-green-50' : 'border-dashed border-slate-200 hover:border-teal-400 hover:bg-teal-50/30']"
        @click="switchOutputType('excel'); showOutputTypeChoices = false"
      >
        <span class="text-2xl block mb-2">📊</span>
        <span class="text-sm font-semibold">Excel</span>
      </div>
      <div
        :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors',
          props.pulseCta ? 'pulse-cta' : '',
          store.output?.plugin === 'csv' ? 'border-blue-600 bg-blue-50' : 'border-dashed border-slate-200 hover:border-teal-400 hover:bg-teal-50/30']"
        @click="switchOutputType('csv'); showOutputTypeChoices = false"
      >
        <span class="text-2xl block mb-2">🗄</span>
        <span class="text-sm font-semibold">CSV</span>
      </div>
      <div
        :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors',
          props.pulseCta ? 'pulse-cta' : '',
          store.output?.plugin === 'database' ? 'border-amber-600 bg-amber-50' : 'border-dashed border-slate-200 hover:border-teal-400 hover:bg-teal-50/30']"
        @click="switchOutputType('database'); showOutputTypeChoices = false"
      >
        <span class="text-2xl block mb-2">🔌</span>
        <span class="text-sm font-semibold">Database</span>
      </div>
      <div class="text-center opacity-55 bg-slate-50 border-2 border-dashed border-slate-200 rounded-lg p-3 relative">
        <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.3</NTag>
        <span class="text-2xl block mb-2">📄</span>
        <span class="text-sm font-semibold">PDF</span>
      </div>
      <div class="text-center opacity-55 bg-slate-50 border-2 border-dashed border-slate-200 rounded-lg p-3 relative">
        <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.4</NTag>
        <span class="text-2xl block mb-2">🖥</span>
        <span class="text-sm font-semibold">PPT</span>
      </div>
      <div class="text-center opacity-55 bg-slate-50 border-2 border-dashed border-slate-200 rounded-lg p-3 relative">
        <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.5</NTag>
        <span class="text-2xl block mb-2">🌐</span>
        <span class="text-sm font-semibold">API</span>
      </div>
    </div>
    <div v-else class="bg-white border border-slate-200 rounded-lg overflow-hidden">
      <div class="flex items-center gap-2 px-3 py-2 bg-slate-50 border-b border-slate-200">
        <span class="text-lg">{{ outputTypeInfo.icon }}</span>
        <span class="text-sm font-medium truncate flex-1">{{ outputTypeInfo.desc }}</span>
        <NTag size="small" :type="store.output?.plugin === 'csv' ? 'info' : store.output?.plugin === 'database' ? 'warning' : 'success'">{{ outputTypeInfo.label }}</NTag>
        <NButton text size="tiny" type="error" class="ml-auto" @click="clearOutputType">更换类型</NButton>
      </div>

      <!-- Output form -->
      <div class="p-3 space-y-3">
      <!-- Source table (first field, required) -->
      <div>
        <label class="block text-xs font-medium text-slate-500 mb-1"><span class="text-red-500">*</span> 输入源表</label>
        <NSelect
          v-model:value="outputConfig.sourceTable"
          :options="sourceTableOptions"
          placeholder="-- 选择表 --"
          size="small"
        />
      </div>

      <!-- Template file upload (Excel only, drag-and-drop style) -->
      <div v-if="store.output?.plugin === 'excel'">
        <label class="block text-xs font-medium text-slate-500 mb-1">模板文件</label>
        <template v-if="excelConfig.template && store.uploadedFiles[excelConfig.template]">
          <div class="flex items-center gap-1">
            <NTag type="success" size="small" class="truncate">
              {{ store.uploadedFiles[excelConfig.template].originalName }}
            </NTag>
            <NButton text size="tiny" type="error" @click="removeTemplate">移除</NButton>
          </div>
        </template>
        <NUpload
          v-else
          ref="templateUploadRef"
          :custom-request="handleTemplateUpload"
          :show-file-list="false"
          accept=".xlsx,.xls"
          class="w-full"
        >
          <div class="border-2 border-dashed rounded-lg py-4 px-6 text-center cursor-pointer transition-colors border-slate-300 hover:border-teal-400 hover:bg-teal-50/30">
            <span class="text-2xl block mb-1.5">{{ templateUploading ? '⏳' : '📤' }}</span>
            <span class="text-sm text-slate-500 block">{{ templateUploading ? '上传中...' : '将模板文件拖拽到此处，或点击选择文件' }}</span>
            <span class="text-xs text-slate-400 mt-1 block">支持 .xlsx / .xls 格式</span>
          </div>
        </NUpload>
        <p v-if="templateUploadError" class="text-xs text-red-500 mt-1">{{ templateUploadError }}</p>
      </div>

      <!-- Sheet name (Excel only, disabled until template uploaded) -->
      <div v-if="store.output?.plugin === 'excel'">
        <label class="block text-xs font-medium text-slate-500 mb-1">Sheet 名称</label>
        <NSelect
          v-if="templateSheets.length > 0"
          :value="excelConfig.sheet"
          @update:value="(v: string) => { updateExcelConfig({ sheet: v }); onSheetChange(v) }"
          :options="templateSheets.map(s => ({ label: s, value: s }))"
          placeholder="选择 Sheet"
          size="small"
        />
        <NInput
          v-else
          :value="excelConfig.sheet"
          :disabled="!excelConfig.template"
          @update:value="v => updateExcelConfig({ sheet: v })"
          placeholder="Sheet1"
          size="small"
        />
      </div>

      <!-- Filename template -->
      <div v-if="store.output?.plugin !== 'database'">
        <div class="flex items-center gap-1 mb-1">
          <label class="block text-xs font-medium text-slate-500">输出文件名</label>
          <NTag size="tiny" class="cursor-pointer" @click="insertTag('{{date:%Y%m%d}}')">年月日</NTag>
          <NTag size="tiny" class="cursor-pointer" @click="insertTag('{{time:%H%M%S}}')">时分秒</NTag>
        </div>
        <div class="flex items-center flex-wrap gap-1 border border-slate-200 rounded px-2 py-1.5 min-h-[32px] bg-white">
          <template v-for="(part, i) in filenameParts" :key="i">
            <NTag size="tiny" :type="part.tag ? 'info' : 'default'" :bordered="true" closable @close="removeTagPart(i)">{{ part.text }}</NTag>
          </template>
          <input
            ref="plainInputRef"
            v-model="plainText"
            class="flex-1 min-w-[40px] outline-none text-sm bg-transparent"
            :placeholder="filenameParts.length === 0 ? '输入文件名' : ''"
            @keyup.enter="commitPlainText"
            @blur="commitPlainText"
          />
          <NButton v-if="baseFilename" text size="tiny" type="error" class="ml-auto" @click="clearFilename">✕</NButton>
        </div>
        <span class="text-sm text-slate-400 font-medium">{{ fileExtension }}</span>
      </div>

      <!-- Delimiter (CSV only) -->
      <div v-if="store.output?.plugin === 'csv'">
        <label class="block text-xs font-medium text-slate-500 mb-1">分隔符</label>
        <NInput
          :value="csvConfig.delimiter"
          @update:value="updateCsvConfig({ delimiter: $event })"
          size="small"
        />
      </div>

      <!-- Encoding (CSV only) -->
      <div v-if="store.output?.plugin === 'csv'">
        <label class="block text-xs font-medium text-slate-500 mb-1">编码</label>
        <NSelect
          :value="csvConfig.encoding"
          @update:value="updateCsvConfig({ encoding: $event })"
          :options="encodingOptions"
          size="small"
        />
      </div>

      <!-- Database output fields -->
      <template v-if="store.output?.plugin === 'database'">
        <!-- Connection selector -->
        <div>
          <label class="block text-xs font-medium text-slate-500 mb-1"><span class="text-red-500">*</span> 数据库连接</label>
          <NSelect
            v-model:value="dbConfig.connectionId"
            :options="connectionOptions"
            placeholder="-- 选择连接 --"
            size="small"
            @update:value="onConnectionSelected"
          />
        </div>
        <!-- Target table name -->
        <div>
          <label class="block text-xs font-medium text-slate-500 mb-1"><span class="text-red-500">*</span> 目标表名</label>
          <NInput v-model:value="dbConfig.targetTable" placeholder="例如：report_data" size="small" />
        </div>
        <!-- Write mode -->
        <div>
          <label class="block text-xs font-medium text-slate-500 mb-1">写入模式</label>
          <NSelect
            v-model:value="dbConfig.writeMode"
            :options="writeModeOptions"
            size="small"
          />
        </div>
        <!-- Create table if not exists -->
        <div>
          <NCheckbox v-model:checked="dbConfig.createTableIfNotExists" size="small">自动建表</NCheckbox>
        </div>
        <!-- Primary key columns -->
        <div v-if="dbConfig.writeMode === 'upsert'">
          <label class="block text-xs font-medium text-slate-500 mb-1">主键列</label>
          <NSelect
            v-model:value="dbConfig.primaryKeyColumns"
            :options="primaryKeyOptions"
            multiple
            placeholder="选择主键列"
            size="small"
          />
        </div>
        <!-- Batch size -->
        <div>
          <label class="block text-xs font-medium text-slate-500 mb-1">批量大小</label>
          <NInputNumber v-model:value="dbConfig.batchSize" :min="1" :max="10000" size="small" />
        </div>
      </template>

      <!-- Output directory -->
      <div v-if="store.output?.plugin !== 'database'">
        <label class="block text-xs font-medium text-slate-500 mb-1">输出目录</label>
        <NInput v-model:value="fileOutputConfig!.outputDir" size="small" />
      </div>

      <!-- Column mapping -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <label class="text-xs font-medium text-slate-500"><span class="text-red-500">*</span> 列映射</label>
          <div class="flex gap-2">
            <NButton
              v-if="store.output?.plugin === 'csv'"
              size="small"
              @click="onInferColumns"
            >{{ inferColumnLabel }}</NButton>
            <NButton
              v-else
              size="small"
              :loading="mappingLoading"
              @click="onAiMapping"
            >AI 推断列映射</NButton>
            <NButton v-if="outputConfig.columns.length > 0" size="small" @click="onMapAll">全部映射</NButton>
            <NButton v-if="outputConfig.columns.length > 0" size="small" @click="onSmartMatch">智能匹配</NButton>
            <NButton v-if="store.output?.plugin !== 'csv'" size="small" @click="addColumn">+ 添加列映射</NButton>
          </div>
        </div>
        <ColumnMapping v-if="outputConfig.columns.length > 0" :columns="outputConfig.columns" @remove="removeColumn" />
        <p v-else class="text-xs text-slate-400 mt-1">{{ store.output?.plugin === 'csv' ? `点击"${inferColumnLabel}"自动填充列映射` : '点击"+ 添加列映射"添加源列到目标列的映射' }}</p>
      </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { useFileUpload } from '../../composables/useFileUpload'
import { useWizardApi, useAiApi } from '../../composables/useWizardApi'
import type { ExcelOutputConfig, CsvOutputConfig, DatabaseOutputConfig, ColumnMappingItem } from '../../types/wizard'
import type { UploadCustomRequestOptions } from 'naive-ui'
import { NInput, NButton, NTag, NUpload, NSelect, NCheckbox, NInputNumber, useMessage, useDialog } from 'naive-ui'
import { inferSelectColumns } from '../../utils/sql'
import ColumnMapping from './ColumnMapping.vue'

const props = defineProps<{ pulseCta?: boolean }>()
const store = useWizardStore()
const templateUploadRef = ref<InstanceType<typeof NUpload>>()

const inferColumnLabel = computed(() => {
  const lastProcessor = store.processors[0]
  return lastProcessor?.plugin === 'python' ? '推断列映射' : '推断列映射'
})
const message = useMessage()
const dialog = useDialog()
const { fetchPreview, executeSql } = useWizardApi()
const { uploading: templateUploading, error: templateUploadError, upload: uploadTemplate } = useFileUpload()
const { suggesting: mappingLoading, askSuggestion } = useAiApi()
// Show type selector when no output plugin is selected
const showOutputTypeChoices = ref(true)
watch(() => store.output?.plugin, (plugin) => {
  if (plugin) showOutputTypeChoices.value = false
}, { immediate: true })
const lastAutoFilename = ref('')
const templateSheets = ref<string[]>([])

function getDateStr(): string {
  const d = new Date()
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
}

function safeSceneName(): string {
  return store.scene.name.replace(/[\/\\:*?"<>|]/g, '-').trim() || 'output'
}

function buildFilename(ext: string): string {
  return `${safeSceneName()}-${getDateStr()}.${ext}`
}

function applyAutoFilename(ext: string) {
  if (!fileOutputConfig.value) return
  const name = buildFilename(ext)
  // Strip extension — setBaseFilename will append the correct one
  fileOutputConfig.value.filename = name.endsWith('.' + ext) ? name.slice(0, -ext.length - 1) + fileExtension.value : name + fileExtension.value
  lastAutoFilename.value = fileOutputConfig.value.filename
}

const encodingOptions = [
  { label: 'UTF-8', value: 'utf-8' },
  { label: 'GBK', value: 'gbk' },
]

const outputConfig = computed(() => store.output!.config as ExcelOutputConfig | CsvOutputConfig | DatabaseOutputConfig)
const fileOutputConfig = computed(() => store.output?.plugin !== 'database' ? store.output!.config as ExcelOutputConfig | CsvOutputConfig : null)
const fileExtension = computed(() => {
  if (store.output?.plugin === 'csv') return '.csv'
  if (store.output?.plugin === 'database') return ''
  return '.xlsx'
})
const baseFilename = computed(() => {
  const fn = fileOutputConfig.value?.filename || ''
  const ext = fileExtension.value
  return fn.endsWith(ext) ? fn.slice(0, -ext.length) : fn
})
function setBaseFilename(v: string) {
  if (fileOutputConfig.value) fileOutputConfig.value.filename = v + fileExtension.value
}
const excelConfig = computed(() => store.output!.config as ExcelOutputConfig)
const csvConfig = computed(() => store.output!.config as CsvOutputConfig)
const dbConfig = computed(() => store.output!.config as DatabaseOutputConfig)

// Database connection options
const connectionOptions = ref<Array<{label: string; value: string}>>([])

const writeModeOptions = [
  { label: '追加 (INSERT)', value: 'insert' },
  { label: '替换 (DROP+CREATE+INSERT)', value: 'replace' },
  { label: '更新插入 (UPSERT)', value: 'upsert' },
]

const primaryKeyOptions = computed(() => {
  return outputConfig.value.columns
    .filter((c: ColumnMappingItem) => c.source)
    .map((c: ColumnMappingItem) => ({ label: c.target || c.source, value: c.target || c.source }))
})

async function loadConnections() {
  try {
    const resp = await fetch('/api/connections')
    if (resp.ok) {
      const data = await resp.json()
      connectionOptions.value = (Array.isArray(data) ? data : data.items || []).map(
        (c: any) => ({ label: `${c.name} (${c.db_type})`, value: c.id })
      )
    }
  } catch { /* ignore */ }
}

function onConnectionSelected(connId: string) {
  dbConfig.value.connectionId = connId
}

const sourceTableOptions = computed(() => {
  const tables: Array<{ label: string; value: string }> = []
  const seen = new Set<string>()
  for (const proc of store.processors) {
    for (const t of proc.outputTables) {
      if (t && !seen.has(t)) { seen.add(t); tables.push({ label: t + ' (处理输出)', value: t }) }
    }
  }
  for (const inp of store.inputs) {
    if (inp.table && !seen.has(inp.table)) { seen.add(inp.table); tables.push({ label: inp.table + ' (输入源)', value: inp.table }) }
  }
  return tables
})

const outputTypeInfo = computed(() => {
  if (store.output?.plugin === 'csv') return { icon: '🗄', label: 'CSV', desc: '纯文本逗号分隔' }
  if (store.output?.plugin === 'database') return { icon: '🔌', label: 'Database', desc: '写入数据库表' }
  return { icon: '📊', label: 'Excel', desc: '模板样式输出' }
})

const prevFileIds = ref<string[]>([])
const prevSql = ref('')
const plainInputRef = ref<HTMLInputElement>()
const plainText = ref('')

const filenameParts = computed(() => {
  const fn = baseFilename.value
  const parts: Array<{ text: string; tag: boolean }> = []
  const re = /\{\{.+?\}\}/g
  let last = 0; let m
  while ((m = re.exec(fn)) !== null) {
    if (m.index > last) parts.push({ text: fn.slice(last, m.index), tag: false })
    parts.push({ text: m[0], tag: true })
    last = m.index + m[0].length
  }
  if (last < fn.length) parts.push({ text: fn.slice(last), tag: false })
  return parts
})

function insertTag(tag: string) {
  if (fileOutputConfig.value) fileOutputConfig.value.filename = baseFilename.value + tag + fileExtension.value
}

function commitPlainText() {
  const v = plainText.value.trim()
  if (!v) return
  if (fileOutputConfig.value) fileOutputConfig.value.filename = baseFilename.value + v + fileExtension.value
  plainText.value = ''
}

function removeTagPart(idx: number) {
  const parts = filenameParts.value
  const removed = parts[idx].text
  if (fileOutputConfig.value) fileOutputConfig.value.filename = baseFilename.value.replace(removed, '') + fileExtension.value
}

function clearFilename() {
  if (fileOutputConfig.value) fileOutputConfig.value.filename = fileExtension.value
  plainText.value = ''
}
let lastAutoInferred = false
let inferTimer: ReturnType<typeof setTimeout> | null = null

watch(() => store.inputs, (inputs) => {
  const currentIds = inputs.map(inp => inp.fileId).filter(Boolean)
  const hasChange = prevFileIds.value.length !== currentIds.length
    || prevFileIds.value.some((id, i) => id !== currentIds[i])
  prevFileIds.value = currentIds
  if (hasChange && outputConfig.value.columns.length > 0) {
    outputConfig.value.columns = []
    lastAutoInferred = false
  }
}, { deep: true })

watch(
  () => store.processors.map(p => p.plugin === 'sql' ? p.sql : p.script),
  (sqls) => {
    // Use the first processor's SQL for column inference
    const sql = sqls[0] || ''
    if (prevSql.value === sql) return
    prevSql.value = sql
    if (store.output?.plugin !== 'csv') return
    if (inferTimer) clearTimeout(inferTimer)
    inferTimer = setTimeout(() => {
      if (store.output?.plugin === 'csv') {
        onInferColumns()
      }
    }, 800)
  },
  { deep: true }
)

function syncSourceTable() {
  // Use the first available output table from any processor
  for (const proc of store.processors) {
    for (const ot of proc.outputTables) {
      if (ot && !outputConfig.value.sourceTable) {
        outputConfig.value.sourceTable = ot
        return
      }
    }
  }
}

watch(
  () => store.processors.map(p => [...p.outputTables]),
  () => syncSourceTable(),
  { deep: true }
)

// Auto-open template file picker when switching to Excel output.
// Uses watch + setTimeout because NUpload is dynamically mounted and needs
// extra time for Naive UI's internal <input type="file"> to initialize.
watch(showOutputTypeChoices, (showing) => {
  if (!showing && store.output?.plugin === 'excel' && !excelConfig.value.template) {
    setTimeout(() => {
      const el = (templateUploadRef.value as any)?.$el
      if (el) {
        const input = el.querySelector('input[type="file"]') as HTMLInputElement | null
        input?.click()
      }
    }, 200)
  }
})

onMounted(() => {
  syncSourceTable()
  loadConnections()
  const p0 = store.processors[0]; const hasCode = p0 && (p0.plugin === 'sql' ? p0.sql.trim() : p0.script.trim())
  if (store.output?.plugin === 'csv' && outputConfig.value.columns.length === 0 && hasCode) {
    prevSql.value = p0.plugin === 'sql' ? p0.sql : p0.script
    onInferColumns()
  }
})

onUnmounted(() => {
  if (inferTimer) clearTimeout(inferTimer)
})

async function handleTemplateUpload({ file, onFinish, onError }: UploadCustomRequestOptions) {
  if (!file.file) return
  const meta = await uploadTemplate(file.file)
  if (meta) {
    store.addFileRef(meta.fileId, meta)
    const excelCfg = store.output!.config as ExcelOutputConfig
    excelCfg.template = meta.fileId

    const preview = await fetchPreview(meta.fileId)
    if (preview) {
      templateSheets.value = preview.sheets || []
      if (preview.sheets?.length) excelCfg.sheet = preview.sheets[0]
      // Auto-fill columns
      const sourceCols: string[] = []
      for (const input of store.inputs) {
        if (input.fileId) {
          const src = await fetchPreview(input.fileId)
          if (src) sourceCols.push(...src.columns)
        }
      }
      if (preview.columns?.length) {
        excelCfg.columns = preview.columns.map(col => ({
          source: sourceCols.includes(col) ? col : '',
          target: col
        }))
      } else if (sourceCols.length) {
        excelCfg.columns = sourceCols.map(col => ({ source: col, target: col }))
        message.info('这个sheet页没有找到表头信息，将直接用数据源字段作为表头，你可以修改或删除列')
      }
    }
    onFinish()
  } else {
    onError()
  }
}

function updateExcelConfig(partial: Partial<ExcelOutputConfig>) {
  const cfg = store.output!.config as ExcelOutputConfig
  Object.assign(cfg, partial)
}

async function onSheetChange(sheet: string) {
  const cfg = store.output!.config as ExcelOutputConfig
  if (!cfg.template) return
  const preview = await fetchPreview(cfg.template, sheet)
  if (!preview) return
  if (preview.columns?.length) {
    const sourceCols: string[] = []
    for (const input of store.inputs) {
      if (input.fileId) {
        const src = await fetchPreview(input.fileId)
        if (src) sourceCols.push(...src.columns)
      }
    }
    cfg.columns = preview.columns.map(col => ({
      source: sourceCols.includes(col) ? col : '',
      target: col
    }))
  } else {
    // Empty sheet — fall back to all source columns
    const allCols: string[] = []
    for (const input of store.inputs) {
      if (input.fileId) {
        const src = await fetchPreview(input.fileId)
        if (src) allCols.push(...src.columns)
      }
    }
    cfg.columns = allCols.map(col => ({ source: col, target: col }))
    message.info('这个sheet页没有找到表头信息，将直接用数据源字段作为表头，你可以修改或删除列')
  }
}

function removeTemplate() {
  const excelCfg = store.output!.config as ExcelOutputConfig
  excelCfg.template = ''
  excelCfg.columns = []
  lastAutoInferred = false
}

async function onInferColumns() {
  // Use the first processor's code for column inference
  const p0 = store.processors[0]
  if (!p0) return
  if (p0.plugin === 'python') {
    message.info('Python 步骤请在下方手动添加列映射，或点击预览结果后自动填充')
    return
  }
  const sql = p0.sql
  const cols = inferSelectColumns(sql)
  if (cols.length === 0) {
    const tableMapping: Record<string, string> = {}
    for (const inp of store.inputs) {
      if (inp.table && inp.fileId) tableMapping[inp.table] = inp.fileId
    }
    if (Object.keys(tableMapping).length === 0) {
      message.warning('无法从当前 SQL 中提取列名，且没有可用的输入文件来执行查询。请手动添加列映射。')
      return
    }
    const result = await executeSql(sql, tableMapping)
    if (result && result.columns.length > 0) {
      outputConfig.value.columns = result.columns.map(col => ({ source: col, target: col }))
      lastAutoInferred = true
      return
    }
    message.warning('无法从当前 SQL 中提取列名（可能是 SELECT * 或复杂语句），请手动添加列映射。')
    return
  }
  outputConfig.value.columns = cols.map(col => ({ source: col, target: col }))
  lastAutoInferred = true
}

async function onAiMapping() {
  const sourceCols: string[] = []
  for (const inp of store.inputs) {
    const fileMeta = store.uploadedFiles[inp.fileId]
    if (fileMeta?.columns) {
      sourceCols.push(...fileMeta.columns)
    }
  }
  const targetCols = outputConfig.value.columns.map((c: ColumnMappingItem) => c.target)
  const content = await askSuggestion('mapping', {
    sourceColumns: sourceCols,
    targetColumns: targetCols,
  })
  if (content) {
    try {
      const parsed = JSON.parse(content)
      if (parsed.mappings) {
        outputConfig.value.columns = parsed.mappings
      }
      store.setSuggestion('mapping', { category: 'mapping', status: 'pending', content, timestamp: Date.now() })
    } catch { /* ignore */ }
  }
}

function addColumn() {
  outputConfig.value.columns.push({ source: '', target: '' })
}

function removeColumn(index: number) {
  outputConfig.value.columns.splice(index, 1)
}

function normalizeColumnName(name: string): string {
  return name.toLowerCase().replace(/[_\s]/g, '')
}

function onMapAll() {
  const columns = outputConfig.value.columns as ColumnMappingItem[]
  for (const col of columns) {
    if (!col.source && col.target) {
      // Find source column matching the target name exactly
      const sourceCols = getSourceColumns()
      const match = sourceCols.find(s => s === col.target)
      if (match) col.source = match
    }
  }
}

function onSmartMatch() {
  const columns = outputConfig.value.columns as ColumnMappingItem[]
  const sourceCols = getSourceColumns()
  for (const col of columns) {
    if (col.source) continue
    const normalizedTarget = normalizeColumnName(col.target)
    const match = sourceCols.find(s => normalizeColumnName(s) === normalizedTarget)
    if (match) col.source = match
  }
}

function getSourceColumns(): string[] {
  const cols: string[] = []
  for (const inp of store.inputs) {
    const meta = store.uploadedFiles[inp.fileId]
    if (meta?.columns) cols.push(...meta.columns)
  }
  return cols
}

function clearOutputType() {
  dialog.warning({
    title: '确认删除',
    content: '确定要删除输出配置吗？所有列映射和相关配置将丢失。',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: () => {
      outputConfig.value.columns = []
      lastAutoInferred = false
      showOutputTypeChoices.value = true
    },
  })
}

function switchOutputType(plugin: 'excel' | 'csv' | 'database') {
  if (plugin === store.output?.plugin) return
  // Safely get sourceTable from current output config (may be null)
  const currentSourceTable = store.output?.config?.sourceTable || ''
  const currentOutputDir = (store.output?.config as ExcelOutputConfig | CsvOutputConfig)?.outputDir || ''
  if (plugin === 'database') {
    store.setOutput({
      plugin: 'database',
      config: {
        type: 'database',
        sourceTable: currentSourceTable,
        columns: [] as ColumnMappingItem[],
        connectionId: '',
        targetTable: '',
        writeMode: 'insert',
        createTableIfNotExists: true,
        primaryKeyColumns: [],
        batchSize: 1000,
      },
    })
    lastAutoFilename.value = ''
    return
  }
  const ext = plugin === 'csv' ? 'csv' : 'xlsx'
  const common = {
    sourceTable: currentSourceTable,
    outputDir: currentOutputDir,
    filename: buildFilename(ext),
    columns: [] as ColumnMappingItem[],
  }
  lastAutoInferred = false
  if (plugin === 'csv') {
    store.setOutput({
      plugin: 'csv',
      config: {
        type: 'csv' as const,
        ...common,
        delimiter: ',',
        encoding: 'utf-8',
      },
    })
    onInferColumns()
  } else {
    store.setOutput({
      plugin: 'excel',
      config: {
        type: 'excel' as const,
        ...common,
        template: '',
        sheet: 'Sheet1',
      },
    })
  }
  lastAutoFilename.value = common.filename
}

watch(() => store.scene.name, () => {
  if (!fileOutputConfig.value || fileOutputConfig.value.filename !== lastAutoFilename.value) return
  const ext = store.output?.plugin === 'csv' ? 'csv' : 'xlsx'
  applyAutoFilename(ext)
})

function updateCsvConfig(patch: Partial<CsvOutputConfig>) {
  if (store.output) {
    store.setOutput({
      ...store.output,
      config: { ...store.output.config, ...patch } as CsvOutputConfig,
    })
  }
}
</script>
