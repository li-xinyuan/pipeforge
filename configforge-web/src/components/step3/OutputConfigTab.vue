<template>
  <div>
    <!-- Output type selector -->
    <p v-if="showOutputTypeChoices" style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 12px;">选择输出格式，配置数据的导出方式</p>
    <div v-if="showOutputTypeChoices" class="grid grid-cols-3 gap-3 mb-5">
      <div
        :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30 dark:bg-green-900/30',
          props.pulseCta ? 'pulse-cta' : '',
          store.output?.plugin === 'excel' ? 'border-green-600 bg-green-50' : 'border-green-600 bg-green-50']"
        @click="switchOutputType('excel'); showOutputTypeChoices = false"
      >
        <span class="text-2xl block mb-2">📊</span>
        <span class="text-sm font-semibold">Excel</span>
        <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">.xlsx 模板输出</span>
      </div>
      <div
        :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30 dark:bg-blue-900/30',
          props.pulseCta ? 'pulse-cta' : '',
          store.output?.plugin === 'csv' ? 'border-blue-600 bg-blue-50' : 'border-blue-600 bg-blue-50']"
        @click="switchOutputType('csv'); showOutputTypeChoices = false"
      >
        <span class="text-2xl block mb-2">🗄</span>
        <span class="text-sm font-semibold">CSV</span>
        <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">.csv / .tsv 导出</span>
      </div>
      <div
        :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30 dark:bg-purple-900/30',
          props.pulseCta ? 'pulse-cta' : '',
          store.output?.plugin === 'database' ? 'border-purple-600 bg-purple-50' : 'border-purple-600 bg-purple-50']"
        @click="switchOutputType('database'); showOutputTypeChoices = false"
      >
        <span class="text-2xl block mb-2">🔌</span>
        <span class="text-sm font-semibold">Database</span>
        <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">MySQL / PostgreSQL</span>
      </div>
      <div class="text-center opacity-55 bg-slate-50 dark:bg-slate-800 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-lg p-3 relative">
        <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.3</NTag>
        <span class="text-2xl block mb-2">📄</span>
        <span class="text-sm font-semibold">PDF</span>
      </div>
      <div class="text-center opacity-55 bg-slate-50 dark:bg-slate-800 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-lg p-3 relative">
        <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.4</NTag>
        <span class="text-2xl block mb-2">🖥</span>
        <span class="text-sm font-semibold">PPT</span>
      </div>
      <div class="text-center opacity-55 bg-slate-50 dark:bg-slate-800 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-lg p-3 relative">
        <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.5</NTag>
        <span class="text-2xl block mb-2">🌐</span>
        <span class="text-sm font-semibold">API</span>
      </div>
    </div>
    <div v-else-if="outputConfig" class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
      <div class="flex items-center gap-2 px-3 py-2 bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700">
        <span class="text-lg">{{ outputTypeInfo.icon }}</span>
        <span class="text-sm font-medium truncate flex-1">{{ outputTypeInfo.desc }}</span>
        <NTag size="small" :type="store.output?.plugin === 'csv' ? 'info' : store.output?.plugin === 'database' ? 'warning' : 'success'">{{ outputTypeInfo.label }}</NTag>
        <NButton text size="tiny" type="error" class="ml-auto" @click="clearOutputType">更换类型</NButton>
      </div>

      <!-- Output form -->
      <div class="p-3 cf-form-grid">
      <!-- Source table (first field, required) -->
      <div>
        <label class="cf-label"><span class="cf-required">*</span> 输入源表</label>
        <NSelect
          v-model:value="outputConfig.sourceTable"
          :options="sourceTableOptions"
          placeholder="-- 选择表 --"
          size="small"
        />
      </div>

      <!-- File output form (Excel / CSV) -->
      <FileOutputForm
        ref="fileOutputFormRef"
        @remove-template="removeTemplate"
        @sheet-change="onSheetChange"
        @template-uploaded="onTemplateUploaded"
      />

      <!-- Database output form -->
      <DatabaseOutputForm @open-conn-manager="showConnManager = true" />

      <!-- Column mapping -->
      <div class="cf-form-group--full">
        <div class="flex items-center justify-between mb-2">
          <label class="cf-label" style="margin-bottom: 0;"><span class="cf-required">*</span> 列映射</label>
          <div class="flex gap-2">
            <NButton
              v-if="store.output?.plugin === 'csv'"
              size="small"
              @click="onInferColumns"
            >{{ inferColumnLabel }}</NButton>
            <AiTriggerButton
              v-else
              label="AI 推断列映射"
              :loading="mappingLoading"
              @click="onAiMapping"
            />
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

  <!-- Inline connection manager modal -->
  <div v-if="showConnManager" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showConnManager = false">
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto p-5">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-base font-semibold">管理数据库连接</h3>
        <button class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300" @click="closeConnManager">✕</button>
      </div>
      <ConnectionManager />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi, useAiApi } from '../../composables/useWizardApi'
import type { ExcelOutputConfig, CsvOutputConfig, DatabaseOutputConfig, ColumnMappingItem } from '../../types/wizard'
import { NInput, NButton, NTag, NSelect, useMessage, useDialog } from 'naive-ui'
import { inferSelectColumns } from '../../utils/sql'
import ColumnMapping from './ColumnMapping.vue'
import AiTriggerButton from '../common/AiTriggerButton.vue'
import ConnectionManager from '../common/ConnectionManager.vue'
import DatabaseOutputForm from './DatabaseOutputForm.vue'
import FileOutputForm from './FileOutputForm.vue'
import { useConnections } from '../../composables/useConnections'

const props = defineProps<{ pulseCta?: boolean }>()
const store = useWizardStore()
const fileOutputFormRef = ref<InstanceType<typeof FileOutputForm>>()

const inferColumnLabel = computed(() => {
  const lastProcessor = store.processors[0]
  return lastProcessor?.plugin === 'python' ? '推断列映射' : '推断列映射'
})
const message = useMessage()
const dialog = useDialog()
const { fetchPreview, executeSql } = useWizardApi()
const { suggesting: mappingLoading, askSuggestion } = useAiApi()
// Show type selector when no output plugin is selected
const showOutputTypeChoices = ref(true)
const showConnManager = ref(false)

async function closeConnManager() {
  showConnManager.value = false
  await loadConnections()
}
watch(() => store.output?.plugin, (plugin) => {
  if (plugin) showOutputTypeChoices.value = false
}, { immediate: true })
const lastAutoFilename = ref('')

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
  const fileOutputConfig = store.output?.plugin !== 'database' ? store.output?.config as ExcelOutputConfig | CsvOutputConfig : null
  if (!fileOutputConfig) return
  const fileExtension = store.output?.plugin === 'csv' ? '.csv' : '.xlsx'
  const name = buildFilename(ext)
  fileOutputConfig.filename = name.endsWith('.' + ext) ? name.slice(0, -ext.length - 1) + fileExtension : name + fileExtension
  lastAutoFilename.value = fileOutputConfig.filename
}

const outputConfig = computed(() => (store.output?.config ?? { columns: [], sourceTable: '' }) as ExcelOutputConfig | CsvOutputConfig | DatabaseOutputConfig)
const excelConfig = computed(() => store.output?.config as ExcelOutputConfig | undefined)

const { connectionOptions, loadConnectionOptions: loadConnections } = useConnections()

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
watch(showOutputTypeChoices, (showing) => {
  if (!showing && store.output?.plugin === 'excel' && !excelConfig.value?.template) {
    setTimeout(() => {
      const formRef = fileOutputFormRef.value
      if (formRef) {
        const el = (formRef.templateUploadRef as { $el?: HTMLElement } | undefined)?.$el
        if (el) {
          const input = el.querySelector('input[type="file"]') as HTMLInputElement | null
          input?.click()
        }
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

function onTemplateUploaded() {
  // No-op: template upload is handled inside FileOutputForm
}

async function onSheetChange(sheet: string) {
  const cfg = store.output?.config as ExcelOutputConfig
  if (!cfg?.template) return
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
  const excelCfg = store.output?.config as ExcelOutputConfig
  if (!excelCfg) return
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
        writeMode: 'append',
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
  const fileOutputConfig = store.output?.plugin !== 'database' ? store.output?.config as ExcelOutputConfig | CsvOutputConfig : null
  if (!fileOutputConfig || fileOutputConfig.filename !== lastAutoFilename.value) return
  const ext = store.output?.plugin === 'csv' ? 'csv' : 'xlsx'
  applyAutoFilename(ext)
})
</script>
