<template>
  <div class="space-y-3">
    <!-- Step name + Input tables in one row -->
    <div class="grid grid-cols-2 gap-3">
      <div>
        <label class="block text-xs font-medium text-slate-500 mb-1">步骤名称</label>
        <NInput
          :value="proc.name"
          @update:value="(v: string) => $emit('update', { name: v })"
          size="small"
          placeholder="例如：数据清洗"
          :data-testid="`processor-name-${index}`"
        />
      </div>
      <div>
        <label class="block text-xs font-medium text-slate-500 mb-1">输入表</label>
        <NSelect
          :value="proc.inputTables"
          :options="availableTables"
          multiple
          size="tiny"
          placeholder="选择输入表（可选）"
          @update:value="(v: string[]) => $emit('update', { inputTables: v })"
        />
      </div>
    </div>

    <!-- SQL textarea -->
    <div>
      <label class="block text-sm font-medium text-slate-900 mb-1">
        <span class="text-red-500">*</span> SQL
      </label>
      <NInput
        :value="proc.sql"
        @update:value="(v: string) => $emit('update', { sql: v })"
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
        <NButton size="small" type="primary" :loading="suggesting" @click="onAiGenerateSql">生成 SQL</NButton>
        <NButton size="small" @click="showNlInput = false">取消</NButton>
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
        @update:value="(v: string) => $emit('update', { outputTables: [v] })"
        size="small"
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
