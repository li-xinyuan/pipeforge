<template>
  <div class="space-y-3">
    <!-- Step name + Input tables in one row -->
    <div class="grid grid-cols-2 gap-3">
      <div>
        <label class="block text-xs font-medium text-slate-500 mb-1">步骤名称</label>
        <NInput
          :value="proc.name"
          @update:value="(v: string) => emit('update', { name: v })"
          placeholder="例如：数据清洗"
          :data-testid="`processor-name-${index}`"
        />
      </div>
      <div>
        <label class="block text-xs font-medium text-slate-500 mb-1">可用表</label>
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
          >{{ tbl.label }}</NTag>
          <span v-if="availableTables.length === 0" class="text-xs text-slate-400">暂无可用表，请先在步骤 2 上传文件</span>
        </div>
      </div>

      <!-- Available columns -->
      <div v-if="displayTable">
        <label class="block text-xs font-medium text-slate-500 mb-1">{{ displayTable }} 的字段</label>
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
          <span v-if="currentTableColumns.length === 0" class="text-xs text-slate-400">加载列信息中...</span>
        </div>
      </div>
    </div>

    <!-- SQL textarea -->
    <div>
      <label class="block text-sm font-medium text-slate-900 mb-1">
        <span class="text-red-500">*</span> SQL
      </label>
      <NInput
        :value="proc.sql"
        @update:value="(v: string) => emit('update', { sql: v })"
        type="textarea"
        :autosize="{ minRows: 6, maxRows: 16 }"
        :placeholder="sqlPlaceholder"
        :class="['font-mono text-sm', { 'pulse-cta-input': pulseSql }]"
        :data-testid="`processor-sql-${index}`"
      />
    </div>

    <!-- AI generate inline -->
    <div v-if="showNlInput" class="p-3 bg-sky-50 border border-sky-200 rounded-lg">
      <NInput
        v-model:value="nlText"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 6 }"
        placeholder="用自然语言描述你想要的查询，例如：查询每个部门有多少员工，按人数降序"
      />
      <div class="flex gap-2 mt-2">
        <NButton size="tiny" type="primary" :loading="suggesting" @click="onAiGenerateSql">生成 SQL</NButton>
        <NButton size="tiny" @click="showNlInput = false">取消</NButton>
      </div>
      <p v-if="aiError" class="text-xs text-red-500 mt-1">{{ aiError }}</p>
    </div>

    <!-- Output table -->
    <div>
      <label class="block text-sm font-medium text-slate-900 mb-1">
        <span class="text-red-500">*</span> 输出表名
      </label>
      <NInput
        :value="proc.outputTables[0] || ''"
        @update:value="(v: string) => emit('update', { outputTables: [v] })"
        placeholder="例如：monthly_report"
      />
      <p v-if="outputTableError" class="text-xs text-red-500 mt-1">{{ outputTableError }}</p>
      <p v-if="equivalenceSql" class="text-xs text-slate-400 mt-1.5 font-mono">{{ equivalenceSql }}</p>
    </div>

    <!-- Preview execution -->
    <div class="flex gap-2 items-center flex-wrap">
      <NButton v-if="!dryRunVisible || !dryRunResult" size="tiny" type="info" :loading="dryRunRunning" :disabled="!proc.sql.trim()" @click="runDryRun">▶ 预览结果</NButton>
      <NButton v-else size="tiny" type="info" @click="dryRunVisible = false">收起结果</NButton>
      <NButton size="tiny" :disabled="!aiConfigured" @click="showNlInput = !showNlInput">✨ AI 生成 SQL</NButton>
    </div>

    <p v-if="dryRunError" class="text-xs text-red-500">{{ dryRunError }}</p>

    <div v-if="dryRunResult && dryRunVisible" class="space-y-2 mt-2">
      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-400">共 {{ dryRunResult.length }} 个表</span>
      </div>
      <div v-for="table in dryRunResult" :key="table.table_name" class="border border-slate-200 rounded p-2">
        <div class="flex items-center gap-2 mb-2">
          <NTag size="tiny" :bordered="false" type="info">{{ table.table_name }}</NTag>
          <span class="text-xs text-slate-400">{{ table.columns.length }} 列 / {{ table.total_rows }} 行</span>
        </div>
        <ColumnPreview :columns="table.columns" :rows="table.rows" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NTag, NInput, NSelect } from 'naive-ui'
import ColumnPreview from '../step2/ColumnPreview.vue'
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
const { dryRun: runDryRunApi, error: wizardApiError } = useWizardApi()
const { suggesting, aiError, askSuggestion, getAiSettings } = useAiApi()

const showNlInput = ref(false)
const nlText = ref('')
const aiConfigured = ref(false)

const dryRunRunning = ref(false)
const dryRunResult = ref<{ table_name: string; columns: string[]; rows: string[][]; total_rows: number }[] | null>(null)
const dryRunError = ref('')
const dryRunVisible = ref(false)

onMounted(async () => {
  const settings = await getAiSettings()
  aiConfigured.value = !!(settings?.enabled && settings?.api_key)
})

const sqlPlaceholder = computed(() => {
  const tables = props.availableTables.map(o => o.value)
  return tables.length > 0 ? `SELECT * FROM "${tables[0]}"` : '输入 SQL 查询语句...'
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

const datePattern = /^\d{4}[-\/]\d{1,2}[-\/]\d{1,2}$|^\d{8}$|^\d{4}年\d{1,2}月\d{1,2}日$|^\d{1,2}[-\/]\d{1,2}[-\/]\d{4}$/

function inferColType(values: string[]): string {
  const v = values.filter(x => x != null && String(x).trim())
  if (v.length === 0) return 'TEXT'
  if (v.every(x => /^(true|false|yes|no|0|1)$/i.test(String(x)))) return 'BOOL'
  if (v.every(x => /^-?\d+$/.test(String(x)))) return 'INT'
  if (v.every(x => /^-?\d+\.?\d*$/.test(String(x)) && !isNaN(Number(x)))) return 'NUM'
  if (v.every(x => datePattern.test(String(x)))) return 'DATE'
  return 'TEXT'
}

const typeBgMap: Record<string, string> = { INT: 'bg-blue-50', NUM: 'bg-purple-50', BOOL: 'bg-amber-50', DATE: 'bg-green-50', TEXT: '' }
const typeTextMap: Record<string, string> = { INT: 'text-blue-700', NUM: 'text-purple-700', BOOL: 'text-amber-700', DATE: 'text-green-700', TEXT: 'text-slate-600' }
const typeBadgeMap: Record<string, string> = { INT: 'bg-blue-200/60 text-blue-800', NUM: 'bg-purple-200/60 text-purple-800', BOOL: 'bg-amber-200/60 text-amber-800', DATE: 'bg-green-200/60 text-green-800', TEXT: 'bg-slate-200/60 text-slate-700' }

const currentTableColumns = computed(() => {
  if (!displayTable.value) return []
  // Find matching input source
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
  return []
})

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
  const result = await runDryRunApi(store.$state)
  if (result?.tables?.length) {
    const inputTables = new Set(store.inputs.map(inp => inp.table).filter(Boolean))
    const outputTables = result.tables.filter(t => !inputTables.has(t.table_name))
    dryRunResult.value = outputTables.length ? outputTables : result.tables
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
