<template>
  <div class="cf-form-group--full">
    <div class="flex items-center justify-between mb-2">
      <label class="cf-label" style="margin-bottom: 0;"><span class="cf-required">*</span> 列映射</label>
      <div class="flex gap-2">
        <NButton
          v-if="plugin === 'csv'"
          size="small"
          @click="onInferColumns"
        >
          {{ inferColumnLabel }}
        </NButton>
        <AiTriggerButton
          v-else
          label="AI 推断列映射"
          :loading="mappingLoading"
          @click="onAiMapping"
        />
        <NButton v-if="columns.length > 0" size="small" @click="onMapAll">全部映射</NButton>
        <NButton v-if="columns.length > 0" size="small" @click="onSmartMatch">智能匹配</NButton>
        <NButton v-if="plugin !== 'csv'" size="small" @click="addColumn">+ 添加列映射</NButton>
      </div>
    </div>
    <ColumnMapping v-if="columns.length > 0" :columns="columns" @remove="removeColumn" />
    <p v-else class="text-xs text-slate-400 mt-1">{{ plugin === 'csv' ? `点击"${inferColumnLabel}"自动填充列映射` : '点击"+ 添加列映射"添加源列到目标列的映射' }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi, useAiApi } from '../../composables/useWizardApi'
import type { ColumnMappingItem, ExcelOutputConfig, CsvOutputConfig, DatabaseOutputConfig } from '../../types/wizard'
import { NButton, useMessage } from 'naive-ui'
import { inferSelectColumns } from '../../utils/sql'
import ColumnMapping from './ColumnMapping.vue'
import AiTriggerButton from '../common/AiTriggerButton.vue'

const store = useWizardStore()
const message = useMessage()
const { executeSql } = useWizardApi()
const { suggesting: mappingLoading, askSuggestion } = useAiApi()

const outputConfig = computed(() => (store.output?.config ?? { columns: [], sourceTable: '' }) as ExcelOutputConfig | CsvOutputConfig | DatabaseOutputConfig)
const columns = computed(() => outputConfig.value.columns)
const plugin = computed(() => store.output?.plugin ?? '')

const inferColumnLabel = computed(() => {
  const lastProcessor = store.processors[0]
  return lastProcessor?.plugin === 'python' ? '推断列映射' : '推断列映射'
})

const prevFileIds = ref<string[]>([])
const prevSql = ref('')
let _lastAutoInferred = false
let inferTimer: ReturnType<typeof setTimeout> | null = null

watch(() => store.inputs, (inputs) => {
  const currentIds = inputs.map(inp => inp.fileId).filter(Boolean)
  const hasChange = prevFileIds.value.length !== currentIds.length
    || prevFileIds.value.some((id, i) => id !== currentIds[i])
  prevFileIds.value = currentIds
  if (hasChange && outputConfig.value.columns.length > 0) {
    outputConfig.value.columns = []
    _lastAutoInferred = false
  }
}, { deep: true })

watch(
  () => store.processors.map(p => p.plugin === 'sql' ? p.sql : p.script),
  (sqls) => {
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

onMounted(() => {
  const p0 = store.processors[0]
  const hasCode = p0 && (p0.plugin === 'sql' ? p0.sql.trim() : p0.script.trim())
  if (store.output?.plugin === 'csv' && outputConfig.value.columns.length === 0 && hasCode) {
    prevSql.value = p0.plugin === 'sql' ? p0.sql : p0.script
    onInferColumns()
  }
})

onUnmounted(() => {
  if (inferTimer) clearTimeout(inferTimer)
})

async function onInferColumns() {
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
      _lastAutoInferred = true
      return
    }
    message.warning('无法从当前 SQL 中提取列名（可能是 SELECT * 或复杂语句），请手动添加列映射。')
    return
  }
  outputConfig.value.columns = cols.map(col => ({ source: col, target: col }))
  _lastAutoInferred = true
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
  const cols = outputConfig.value.columns as ColumnMappingItem[]
  for (const col of cols) {
    if (!col.source && col.target) {
      const sourceCols = getSourceColumns()
      const match = sourceCols.find(s => s === col.target)
      if (match) col.source = match
    }
  }
}

function onSmartMatch() {
  const cols = outputConfig.value.columns as ColumnMappingItem[]
  const sourceCols = getSourceColumns()
  for (const col of cols) {
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
</script>
