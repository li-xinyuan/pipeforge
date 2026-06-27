<template>
  <div class="space-y-3">
    <!-- Step name + Input tables in one row -->
    <div class="cf-form-grid">
      <div>
        <label class="cf-label">处理步骤名称</label>
        <NInput
          :value="proc.name"
          placeholder="例如：数据清洗"
          size="small"
          :data-testid="`processor-name-${index}`"
          @update:value="(v: string) => emit('update', { name: v })"
        />
      </div>
      <div>
        <label class="cf-label">输入源表</label>
        <div class="flex flex-wrap gap-1">
          <NTag
            v-for="tbl in availableTables"
            :key="tbl.value"
            :type="currentFromTable === tbl.value ? 'info' : 'default'"
            size="tiny"
            :bordered="true"
            checkable
            :checked="currentFromTable === tbl.value"
            class="cursor-pointer"
            @click="switchTable(tbl.value)"
          >
            {{ tbl.label }}
          </NTag>
          <span v-if="availableTables.length === 0" class="text-xs text-slate-400 dark:text-slate-500">暂无可用表，请先在步骤 2 上传文件</span>
        </div>
      </div>

      <!-- Available columns -->
      <div v-if="displayTable">
        <label class="cf-label">{{ displayTable }} 的字段</label>
        <div class="flex flex-wrap gap-1">
          <NTag
            v-for="col in currentTableColumns"
            :key="col.name"
            size="tiny"
            :bordered="true"
            :class="colTypeBgClass(col.type)"
          >
            <span :class="colTypeTextClass(col.type)" class="text-[11px] font-medium">{{ col.name }}</span>
            <span :class="colTypeBadgeClass(col.type)" class="text-[9px] px-1 py-0.5 rounded ml-1">{{ col.type }}</span>
          </NTag>
          <span v-if="currentTableColumns.length === 0" class="text-xs text-slate-400 dark:text-slate-500">加载列信息中...</span>
        </div>
      </div>
    </div>

    <!-- SQL editor -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <label class="cf-label">
          <span class="cf-required">*</span> SQL
        </label>
        <NDropdown :options="sqlTemplates" trigger="click" @select="onSqlTemplateSelect">
          <NButton size="tiny" quaternary>📋 SQL 模板</NButton>
        </NDropdown>
      </div>
      <CodeEditor
        ref="sqlEditorRef"
        :model-value="proc.sql"
        language="sql"
        :placeholder="sqlPlaceholder"
        min-height="200px"
        :class="{ 'pulse-cta-input': pulseSql }"
        :data-testid="`processor-sql-${index}`"
        @update:model-value="(v: string) => emit('update', { sql: v })"
      />
    </div>

    <!-- AI generate inline -->
    <div v-if="showNlInput" class="p-3 bg-sky-50 border border-sky-200 rounded-lg">
      <NInput
        v-model:value="nlText"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 6 }"
        placeholder="用自然语言描述你想要的查询，例如：查询每个部门有多少员工，按人数降序"
        size="small"
      />
      <div class="flex gap-2 mt-2">
        <NButton size="tiny" type="primary" :loading="suggesting" @click="onAiGenerateSql">生成 SQL</NButton>
        <NButton size="tiny" @click="showNlInput = false">取消</NButton>
      </div>
      <p v-if="aiError" class="text-xs text-red-500 mt-1">{{ aiError }}</p>
    </div>

    <!-- Preview execution + AI generate SQL button -->
    <div class="flex gap-2 items-center flex-wrap">
      <NButton v-if="!dryRunVisible || !dryRunResult" size="tiny" type="info" :loading="dryRunRunning" :disabled="!proc.sql.trim()" @click="runDryRun">▶ 预览结果</NButton>
      <NButton v-else size="tiny" type="info" @click="dryRunVisible = false">收起结果</NButton>
      <AiTriggerButton label="AI 生成 SQL" :disabled="!aiConfigured" :loading="showNlInput && suggesting" @click="showNlInput = !showNlInput" />
    </div>

    <p v-if="dryRunError" class="text-xs text-red-500 mt-1">{{ dryRunError }}</p>

    <div v-if="dryRunResult && dryRunVisible" class="space-y-2 mt-2">
      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-400 dark:text-slate-500">共 {{ dryRunResult.length }} 个表</span>
        <span class="text-xs text-amber-500">⚠ 预览基于样本数据，结果可能与实际执行不同</span>
      </div>
      <div v-for="table in dryRunResult" :key="table.table_name" class="border border-slate-200 dark:border-slate-700 rounded p-2">
        <div class="flex items-center gap-2 mb-2">
          <NTag size="tiny" :bordered="false" type="info">{{ table.table_name }}</NTag>
          <span class="text-xs text-slate-400 dark:text-slate-500">{{ table.columns.length }} 列 / {{ table.total_rows }} 行</span>
        </div>
        <ColumnPreview :columns="table.columns" :rows="table.rows" />
      </div>
    </div>

    <!-- Output table (moved below preview/AI buttons to avoid splitting the AI generation area) -->
    <div>
      <label class="cf-label">
        <span class="cf-required">*</span> 输出表名
      </label>
      <NInput
        :value="proc.outputTables[0] || ''"
        placeholder="例如：月度报表"
        size="small"
        @update:value="(v: string) => emit('update', { outputTables: [v] })"
      />
      <p v-if="outputTableError" class="text-xs text-red-500 mt-1">{{ outputTableError }}</p>
      <p v-if="equivalenceSql" class="text-xs text-slate-400 dark:text-slate-500 mt-1.5 font-mono">{{ equivalenceSql }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, ref, type Ref } from 'vue'
import { NButton, NTag, NInput, NDropdown } from 'naive-ui'
import ColumnPreview from '../step2/ColumnPreview.vue'
import CodeEditor from '../common/CodeEditor.vue'
import AiTriggerButton from '../common/AiTriggerButton.vue'
import type { ProcessorStep } from '../../types/wizard'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi, useAiApi } from '../../composables/useWizardApi'

const props = defineProps<{
  proc: Extract<ProcessorStep, { plugin: 'sql' }>
  index: number
  availableTables: Array<{ label: string; value: string }>
  pulseSql?: boolean
}>()

const emit = defineEmits<{
  update: [partial: Partial<ProcessorStep>]
}>()

const store = useWizardStore()
const columnsCache = inject<Ref<Record<string, Array<{ name: string; type: string }>>>>('tableColumnsCache', ref({}))
const { dryRun: runDryRunApi, error: wizardApiError } = useWizardApi()
const { suggesting, aiError, askSuggestion, getAiSettings } = useAiApi()

const showNlInput = ref(false)
const nlText = ref('')
const aiConfigured = ref(false)

const dryRunRunning = ref(false)
const dryRunResult = ref<{ table_name: string; columns: string[]; rows: string[][]; total_rows: number }[] | null>(null)
const dryRunError = ref('')
const dryRunVisible = ref(false)
const sqlEditorRef = ref<InstanceType<typeof CodeEditor> | null>(null)

// SQL template library
const sqlTemplates = [
  { label: '统计', key: 'cat-stats', children: [
    { label: 'SELECT COUNT(*) AS total FROM {table}', key: 'stats-count' },
    { label: 'SELECT COUNT(*) AS total, {column} FROM {table} GROUP BY {column}', key: 'stats-group-count' },
  ]},
  { label: '过滤', key: 'cat-filter', children: [
    { label: 'SELECT * FROM {table} WHERE {condition}', key: 'filter-where' },
    { label: 'SELECT * FROM {table} WHERE {column} > {value}', key: 'filter-gt' },
  ]},
  { label: '关联', key: 'cat-join', children: [
    { label: 'SELECT a.*, b.* FROM {table1} a JOIN {table2} b ON a.{key} = b.{key}', key: 'join-basic' },
  ]},
  { label: '排序', key: 'cat-sort', children: [
    { label: 'SELECT * FROM {table} ORDER BY {column} DESC', key: 'sort-desc' },
    { label: 'SELECT * FROM {table} ORDER BY {column} ASC LIMIT {n}', key: 'sort-asc-limit' },
  ]},
  { label: '去重', key: 'cat-distinct', children: [
    { label: 'SELECT DISTINCT {column} FROM {table}', key: 'distinct-col' },
  ]},
  { label: '聚合', key: 'cat-agg', children: [
    { label: 'SELECT {column}, SUM({value}) AS total, AVG({value}) AS avg FROM {table} GROUP BY {column}', key: 'agg-sum-avg' },
  ]},
]

const sqlTemplateMap: Record<string, string> = {
  'stats-count': 'SELECT COUNT(*) AS total FROM {table}',
  'stats-group-count': 'SELECT COUNT(*) AS total, {column} FROM {table} GROUP BY {column}',
  'filter-where': 'SELECT * FROM {table} WHERE {condition}',
  'filter-gt': 'SELECT * FROM {table} WHERE {column} > {value}',
  'join-basic': 'SELECT a.*, b.* FROM {table1} a JOIN {table2} b ON a.{key} = b.{key}',
  'sort-desc': 'SELECT * FROM {table} ORDER BY {column} DESC',
  'sort-asc-limit': 'SELECT * FROM {table} ORDER BY {column} ASC LIMIT {n}',
  'distinct-col': 'SELECT DISTINCT {column} FROM {table}',
  'agg-sum-avg': 'SELECT {column}, SUM({value}) AS total, AVG({value}) AS avg FROM {table} GROUP BY {column}',
}

function onSqlTemplateSelect(key: string) {
  const template = sqlTemplateMap[key]
  if (!template) return
  // Replace {table} with actual input table name if available
  const tableName = props.availableTables[0]?.value || inputTableNames.value[0] || ''
  let sql = template
  if (tableName) {
    sql = sql.replace(/\{table\}/g, `"${tableName}"`)
  }
  // Insert at cursor position in editor
  const editor = sqlEditorRef.value
  if (editor) {
    editor.insertAtCursor(sql)
  } else {
    // Fallback: append to existing SQL
    const currentSql = props.proc.sql
    emit('update', { sql: currentSql ? currentSql + '\n' + sql : sql })
  }
}

onMounted(async () => {
  const settings = await getAiSettings()
  aiConfigured.value = !!(settings?.enabled && settings?.api_key)
})

const sqlPlaceholder = computed(() => {
  const tables = props.availableTables.map(o => o.value)
  return tables.length > 0
    ? `SELECT * FROM "${tables[0]}"\n-- 提示：也可以点击"AI 生成 SQL"，用自然语言描述需求`
    : '输入 SQL 查询语句，或点击"AI 生成 SQL"用自然语言描述需求...'
})

const inputTableNames = computed(() =>
  store.inputs.map(inp => inp.table.trim()).filter(Boolean)
)

const outputTableError = computed(() => {
  for (const name of props.proc.outputTables) {
    if (!name.trim()) continue
    if (inputTableNames.value.includes(name.trim())) {
      return `表名 "${name.trim()}" 已被输入源使用，请换一个名称`
    }
  }
  return ''
})

const isPlainSelect = computed(() => {
  const sql = props.proc.sql.trim()
  if (!sql) return false
  return !(
    /\bCREATE\s+(?:TEMP\s+|TEMPORARY\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\w+\s+AS\b/i.test(sql) ||
    /\bINSERT\s+INTO\s+\w+\b/i.test(sql) ||
    /\bWITH\s+\w+\s+AS\s*\(/i.test(sql)
  )
})

const currentFromTable = computed(() => {
  const m = props.proc.sql.trim().match(/FROM\s+"(\w+)"/i)
  return m ? m[1] : ''
})

const displayTable = computed(() => currentFromTable.value || props.availableTables[0]?.value || '')

const datePattern = /^\d{4}[-/]\d{1,2}[-/]\d{1,2}$|^\d{8}$|^\d{4}年\d{1,2}月\d{1,2}日$|^\d{1,2}[-/]\d{1,2}[-/]\d{4}$/

function inferColType(values: string[]): string {
  const v = values.filter(x => x != null && String(x).trim())
  if (v.length === 0) return 'TEXT'
  if (v.every(x => /^(true|false|yes|no|0|1)$/i.test(String(x)))) return 'BOOL'
  if (v.every(x => /^-?\d+$/.test(String(x)))) return 'INT'
  if (v.every(x => /^-?\d+\.?\d*$/.test(String(x)) && !isNaN(Number(x)))) return 'NUM'
  if (v.every(x => datePattern.test(String(x)))) return 'DATE'
  return 'TEXT'
}

const typeBgMap: Record<string, string> = { INT: 'bg-blue-50 dark:bg-blue-900/30', NUM: 'bg-purple-50 dark:bg-purple-900/30', BOOL: 'bg-amber-50 dark:bg-amber-900/30', DATE: 'bg-green-50 dark:bg-green-900/30', TEXT: '' }
const typeTextMap: Record<string, string> = { INT: 'text-blue-700 dark:text-blue-300', NUM: 'text-purple-700 dark:text-purple-300', BOOL: 'text-amber-700 dark:text-amber-300', DATE: 'text-green-700 dark:text-green-300', TEXT: 'text-slate-600 dark:text-slate-300' }
const typeBadgeMap: Record<string, string> = { INT: 'bg-blue-200/60 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200', NUM: 'bg-purple-200/60 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200', BOOL: 'bg-amber-200/60 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200', DATE: 'bg-green-200/60 text-green-800 dark:bg-green-900/40 dark:text-green-200', TEXT: 'bg-slate-200/60 text-slate-700 dark:bg-slate-600/40 dark:text-slate-200' }

const currentTableColumns = computed(() => {
  if (!displayTable.value) return []
  // Check input sources first
  for (const inp of store.inputs) {
    if (inp.table === displayTable.value && inp.fileId) {
      const meta = store.uploadedFiles[inp.fileId]
      if (meta?.columns) {
        return meta.columns.map((name, ci) => {
          const samples = (meta.sampleRows || []).slice(0, 10).map(r => r[ci]).filter(v => v != null)
          return { name, type: inferColType(samples.map(String)) }
        })
      }
    }
  }
  // Check if it's a previous processor's output table
  for (let i = 0; i < props.index; i++) {
    const proc = store.processors[i]
    if (proc.outputTables.includes(displayTable.value)) {
      // Try to get columns from cached dry-run result or previously known columns
      // For now, return existing column info if we can derive it from the source
      const sourceMeta = findSourceColumns(i)
      if (sourceMeta) return sourceMeta
    }
  }
  return []
})

function findSourceColumns(procIndex: number): { name: string; type: string }[] | null {
  const proc = store.processors[procIndex]
  if (!proc) return null
  // Check cache first (from dry-run results)
  const cached = columnsCache.value[proc.outputTables[0] || '']
  if (cached) return cached
  // Walk back to find the original input source columns
  for (const inp of store.inputs) {
    if (proc.inputTables?.includes(inp.table) || (!proc.inputTables?.length && inp.table)) {
      const meta = store.uploadedFiles[inp.fileId]
      if (meta?.columns) {
        return meta.columns.map((name, ci) => {
          const samples = (meta.sampleRows || []).slice(0, 10).map(r => r[ci]).filter(v => v != null)
          return { name, type: inferColType(samples.map(String)) }
        })
      }
    }
  }
  return null
}

function colTypeBgClass(t: string) { return typeBgMap[t] || '' }
function colTypeTextClass(t: string) { return typeTextMap[t] || '' }
function colTypeBadgeClass(t: string) { return typeBadgeMap[t] || '' }

function switchTable(table: string) {
  const sql = props.proc.sql.trim()
  if (!sql) return
  // If it's the default SELECT * pattern, replace the table name
  if (/^SELECT\s+\*\s+FROM\s+"\w+"/i.test(sql)) {
    emit('update', { sql: `SELECT * FROM "${table}"` })
  } else {
    // For custom SQL, replace all occurrences of the old table
    const oldTable = currentFromTable.value
    if (oldTable && oldTable !== table) {
      emit('update', { sql: sql.replace(new RegExp(`"${oldTable}"`, 'g'), `"${table}"`) })
    }
  }
}

const equivalenceSql = computed(() => {
  if (!isPlainSelect.value) return ''
  let sql = props.proc.sql.trim()
  if (sql.endsWith(';')) sql = sql.slice(0, -1).trim()
  const name = props.proc.outputTables[0] || 'result'
  return `等效语句: SELECT * FROM (${sql}) AS ${name}`
})

async function runDryRun() {
  dryRunError.value = ''
  dryRunResult.value = null
  if (!props.proc.sql.trim()) {
    dryRunError.value = '请先输入 SQL'
    return
  }
  dryRunRunning.value = true
  const result = await runDryRunApi(store.getWizardState())
  if (result?.tables?.length) {
    // Only show this step's output table(s)
    const myOutputs = new Set(props.proc.outputTables.filter(Boolean))
    dryRunResult.value = result.tables.filter(t => myOutputs.has(t.table_name))
    // Cache column info for downstream steps
    for (const t of result.tables) {
      columnsCache.value[t.table_name] = t.columns.map((name: string, ci: number) => {
        const samples = t.rows.slice(0, 10).map((r: unknown[]) => r[ci]).filter((v: unknown) => v != null)
        return { name, type: inferColType(samples.map(String)) }
      })
    }
    dryRunVisible.value = true
  } else {
    const apiMsg = wizardApiError.value?.message || ''
    dryRunError.value = apiMsg ? `预览执行失败: ${apiMsg}` : '预览执行失败，请检查输入配置'
  }
  dryRunRunning.value = false
}

async function onAiGenerateSql() {
  if (!nlText.value.trim()) return
  const content = await askSuggestion('sql', {
    inputs: store.inputs.map(inp => ({
      name: inp.table, table: inp.table, columns: [],
    })),
    naturalLanguage: nlText.value,
  })
  if (content) {
    try {
      const parsed = JSON.parse(content)
      let sql = (parsed.sql || '').trim()
      if (sql.endsWith(';')) sql = sql.slice(0, -1).trim()
      const update: Partial<ProcessorStep> = { sql }
      if (parsed.outputTables?.length) {
        const clean = parsed.outputTables.filter((t: string) => !inputTableNames.value.includes(t))
        if (clean.length) update.outputTables = clean
      }
      emit('update', update)
    } catch {
      let sql = content.trim()
      if (sql.endsWith(';')) sql = sql.slice(0, -1).trim()
      emit('update', { sql })
    }
    showNlInput.value = false
    nlText.value = ''
  }
}
</script>

