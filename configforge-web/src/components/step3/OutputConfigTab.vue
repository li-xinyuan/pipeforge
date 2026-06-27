<template>
  <div>
    <!-- Output type selector -->
    <OutputTypeSelector v-if="showOutputTypeChoices" :pulse-cta="props.pulseCta" @select="onOutputTypeSelect" />
    <div v-else-if="outputConfig" class="bg-[var(--color-surface)] border border-[var(--color-border-light)] dark:border-[var(--color-border)] rounded-lg overflow-hidden">
      <div class="flex items-center gap-2 px-3 py-2 bg-[var(--color-bg-secondary)] dark:bg-[var(--color-surface-hover)] border-b border-[var(--color-border-light)] dark:border-[var(--color-border)]">
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

        <!-- Database output form (ConnectionSelector 自包含连接管理 modal) -->
        <DatabaseOutputForm />

        <!-- Column mapping — 命名 widget 协议（modelValue + update:modelValue） -->
        <ColumnMappingEditor
          :model-value="outputConfig.columns"
          @update:model-value="(cols: ColumnMappingItem[]) => outputConfig.columns = cols"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi } from '../../composables/useWizardApi'
import type { ExcelOutputConfig, CsvOutputConfig, DatabaseOutputConfig, ColumnMappingItem } from '../../types/wizard'
import { NButton, NTag, NSelect, useMessage, useDialog } from 'naive-ui'
import ColumnMappingEditor from './ColumnMappingEditor.vue'
import OutputTypeSelector from './OutputTypeSelector.vue'
import DatabaseOutputForm from './DatabaseOutputForm.vue'
import FileOutputForm from './FileOutputForm.vue'
import { registerWidget } from '../../composables/widgetRegistry'

// 注册 column-mapping 命名 widget（output 的 columns 字段引用）
registerWidget('column-mapping', ColumnMappingEditor)

const props = defineProps<{ pulseCta?: boolean }>()
const store = useWizardStore()
const fileOutputFormRef = ref<InstanceType<typeof FileOutputForm>>()

const message = useMessage()
const dialog = useDialog()
const { fetchPreview } = useWizardApi()
// Show type selector when no output plugin is selected
const showOutputTypeChoices = ref(true)

function onOutputTypeSelect(plugin: 'excel' | 'csv' | 'database') {
  switchOutputType(plugin)
  showOutputTypeChoices.value = false
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
  return store.scene.name.replace(/[/\\:*?"<>|]/g, '-').trim() || 'output'
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
}

function clearOutputType() {
  dialog.warning({
    title: '确认删除',
    content: '确定要删除输出配置吗？所有列映射和相关配置将丢失。',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: () => {
      outputConfig.value.columns = []
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
