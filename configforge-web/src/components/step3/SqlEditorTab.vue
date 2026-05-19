<template>
  <div>
    <!-- Processor type selector -->
    <div v-if="showProcessorChoices" class="grid grid-cols-3 gap-3 mb-5">
      <NCard hoverable class="cursor-pointer text-center border-2 border-blue-600 bg-blue-50" @click="showProcessorChoices = false">
        <span class="text-2xl block mb-2">🧪</span>
        <span class="text-sm font-semibold">SQL</span>
        <span class="text-xs text-slate-500 mt-1 block">SQLite 执行</span>
      </NCard>
      <NCard class="text-center opacity-55 bg-slate-50 relative" size="small">
        <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.3</NTag>
        <span class="text-2xl block mb-2">🔗</span>
        <span class="text-sm font-semibold">Jinja2</span>
      </NCard>
      <NCard class="text-center opacity-55 bg-slate-50 relative" size="small">
        <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.4</NTag>
        <span class="text-2xl block mb-2">🖥</span>
        <span class="text-sm font-semibold">Python</span>
      </NCard>
    </div>
    <div v-else class="mb-5 flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg">
      <span class="text-lg">🧪</span>
      <span class="text-sm font-semibold text-slate-700">SQL</span>
      <span class="text-xs text-slate-400">· SQLite 执行</span>
      <NButton text size="tiny" class="ml-auto" @click="showProcessorChoices = true">重选处理方式</NButton>
    </div>

    <!-- Table rename prompt -->
    <div v-if="renamePrompt" class="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-3">
      <span class="text-sm text-amber-700 leading-relaxed">
        表名已从 <strong>"{{ renamePrompt.oldName }}"</strong> 改为 <strong>"{{ renamePrompt.newName }}"</strong>，SQL 中引用了旧表名，是否替换？
      </span>
      <NButton size="tiny" type="warning" @click="onReplaceTableName">替换</NButton>
      <NButton size="tiny" @click="renamePrompt = null">忽略</NButton>
    </div>

    <!-- AI generate button -->
    <div class="flex gap-2 items-center mb-3">
      <NTooltip>
        <template #trigger>
          <NButton size="small" :disabled="!aiConfigured" @click="showNlInput = true">AI 生成 SQL</NButton>
        </template>
        {{ aiTooltip }}
      </NTooltip>
    </div>

    <div v-if="showNlInput" class="mb-4 p-3 bg-sky-50 border border-sky-200 rounded-lg">
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

    <!-- SQL textarea -->
    <div class="mb-4">
      <label class="block text-sm font-medium text-slate-900 mb-1"><span class="text-red-500">*</span> SQL</label>
      <NInput
        v-model:value="store.processor.sql"
        type="textarea"
        :autosize="{ minRows: 6, maxRows: 16 }"
        :placeholder="sqlPlaceholder"
        class="font-mono text-sm"
      />
    </div>

    <!-- output_table -->
    <div class="mb-4">
      <label class="block text-sm font-medium text-slate-900 mb-1"><span class="text-red-500">*</span> 输出表名</label>
      <div class="flex items-center gap-2">
        <NInput
          v-model:value="store.processor.outputTable"
          :status="outputTableError ? 'error' : undefined"
          placeholder="输入输出表名"
          size="small"
          class="w-48"
        />
        <span v-if="store.processor.outputTable && !outputTableError" class="text-[10px] text-slate-400">供后续输出步骤引用</span>
      </div>
      <p v-if="outputTableError" class="text-xs text-red-500 mt-1">{{ outputTableError }}</p>
      <p v-if="equivalenceSql" class="text-xs text-slate-400 mt-1.5 font-mono">{{ equivalenceSql }}</p>
    </div>

    <!-- Query preview -->
    <div class="sql-preview">
      <div class="sql-preview__actions">
        <NButton
          v-if="!queryResult"
          text
          size="tiny"
          :loading="queryRunning"
          :disabled="!store.processor.sql.trim()"
          @click="runQuery"
        >{{ queryRunning ? '执行中...' : '▶ 运行查询' }}</NButton>
        <NButton
          v-else
          text
          size="tiny"
          @click="queryVisible = !queryVisible"
        >{{ queryVisible ? '收起结果' : '展开结果' }}</NButton>
        <span v-if="queryResult" class="sql-preview__row-count">
          返回 {{ queryResult.rows.length }} 行 / {{ queryResult.columns.length }} 列
        </span>
      </div>
      <p v-if="queryError" class="sql-preview__error">{{ queryError }}</p>
      <ColumnPreview
        v-if="queryResult && queryVisible"
        :columns="queryResult.columns"
        :rows="queryResult.rows"
      />
    </div>

    <AiSuggestPanel
      :visible="!!store.aiSuggestions['sql'] && store.aiSuggestions['sql'].status !== 'auto'"
      :content="store.aiSuggestions['sql']?.content || ''"
      @accept="onAcceptSuggestion"
      @regenerate="onRegenerateSuggestion"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { NCard, NInput, NButton, NTag, NTooltip } from 'naive-ui'
import AiSuggestPanel from '../common/AiSuggestPanel.vue'
import ColumnPreview from '../step2/ColumnPreview.vue'
import { inferOutputTable } from '../../utils/sql'
import { useWizardApi, useAiApi } from '../../composables/useWizardApi'

const store = useWizardStore()
const { suggesting, aiError, askSuggestion, getAiSettings } = useAiApi()
const showProcessorChoices = ref(false)
const showNlInput = ref(false)
const nlText = ref('')
const isPlainSelect = ref(false)
const lastInferredName = ref('')
const aiConfigured = ref(false)
let fromAi = false

const { executeSql: runSql } = useWizardApi()
const queryRunning = ref(false)
const queryResult = ref<{ columns: string[]; rows: string[][] } | null>(null)
const queryError = ref('')
const queryVisible = ref(false)

function buildTableMapping(): Record<string, string> {
  const map: Record<string, string> = {}
  for (const inp of store.inputs) {
    if (inp.table && inp.fileId) map[inp.table] = inp.fileId
  }
  return map
}

async function runQuery() {
  queryError.value = ''
  queryResult.value = null
  const sql = store.processor.sql.trim()
  if (!sql) return

  const tableMapping = buildTableMapping()
  if (Object.keys(tableMapping).length === 0) {
    queryError.value = '请先在步骤 2 上传数据文件并设置表名'
    return
  }

  queryRunning.value = true
  const result = await runSql(sql, tableMapping)
  if (result) {
    queryResult.value = result
    queryVisible.value = true
  } else {
    queryError.value = '查询执行失败，请检查 SQL 语法'
  }
  queryRunning.value = false
}

const aiTooltip = computed(() => {
  if (!aiConfigured.value) return '请先在 AI 设置中配置 API Key'
  return '用自然语言描述查询需求，AI 将自动生成 SQL'
})

onMounted(async () => {
  lastKnownTables.value = store.inputs.map(inp => inp.table.trim()).filter(Boolean)
  const settings = await getAiSettings()
  aiConfigured.value = !!(settings?.enabled && settings?.api_key)
})

const inputTableNames = computed(() =>
  store.inputs.map(inp => inp.table.trim()).filter(Boolean)
)

const sqlPlaceholder = computed(() => {
  const tables = inputTableNames.value
  return tables.length > 0 ? `SELECT * FROM "${tables[0]}"` : '输入 SQL 查询语句...'
})

watch(inputTableNames, (tables) => {
  if (tables.length > 0 && !store.processor.sql.trim()) {
    store.processor.sql = `SELECT * FROM "${tables[0]}"`
  }
})

const renamePrompt = ref<{ oldName: string; newName: string } | null>(null)
const lastKnownTables = ref<string[]>([])

function checkTableRenames() {
  const currentTables = store.inputs.map(inp => inp.table.trim()).filter(Boolean)
  const prev = lastKnownTables.value

  for (let i = 0; i < Math.min(currentTables.length, prev.length); i++) {
    const oldName = prev[i]
    const newName = currentTables[i]
    if (!oldName || !newName || oldName === newName) continue

    const sql = store.processor.sql.trim()
    if (!sql) break

    if (i === 0 && sql === `SELECT * FROM "${oldName}"`) {
      store.processor.sql = `SELECT * FROM "${newName}"`
      break
    }

    if (sql.includes(`"${oldName}"`)) {
      renamePrompt.value = { oldName, newName }
      return
    }
  }

  lastKnownTables.value = [...currentTables]
}

function onReplaceTableName() {
  if (!renamePrompt.value) return
  const { oldName, newName } = renamePrompt.value
  const escaped = oldName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  store.processor.sql = store.processor.sql.replace(new RegExp(`"${escaped}"`, 'g'), `"${newName}"`)
  renamePrompt.value = null
  lastKnownTables.value = store.inputs.map(inp => inp.table.trim()).filter(Boolean)
}

defineExpose({ checkTableRenames })

const outputTableError = computed(() => {
  const name = store.processor.outputTable.trim()
  if (!name) return ''
  if (inputTableNames.value.includes(name)) return `表名 "${name}" 已被输入源使用，请换一个名称`
  return ''
})

const equivalenceSql = computed(() => {
  if (!isPlainSelect.value) return ''
  let sql = store.processor.sql.trim()
  if (sql.endsWith(';')) sql = sql.slice(0, -1).trim()
  const name = store.processor.outputTable || 'result'
  return `等效语句: SELECT * FROM (${sql}) AS ${name}`
})

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
      fromAi = true
      let sql = (parsed.sql || '').trim()
      if (sql.endsWith(';')) sql = sql.slice(0, -1).trim()
      store.processor.sql = sql
      if (parsed.outputTables?.length) {
        const clean = parsed.outputTables.filter((t: string) => !inputTableNames.value.includes(t))
        if (clean.length) store.processor.outputTable = clean[0]
      }
    } catch {
      let sql = content.trim()
      if (sql.endsWith(';')) sql = sql.slice(0, -1).trim()
      store.processor.sql = sql
    }
    showNlInput.value = false
    nlText.value = ''
  }
}

watch(() => store.processor.sql, (sql) => {
  const trimmed = sql.trim()
  if (!trimmed) {
    delete store.aiSuggestions['sql']
    isPlainSelect.value = false
    return
  }

  isPlainSelect.value = !(
    /\bCREATE\s+(?:TEMP\s+|TEMPORARY\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\w+\s+AS\b/i.test(trimmed) ||
    /\bINSERT\s+INTO\s+\w+\b/i.test(trimmed) ||
    /\bWITH\s+\w+\s+AS\s*\(/i.test(trimmed)
  )

  const tableName = inferOutputTable(trimmed)
  lastInferredName.value = tableName
  if (!store.processor.outputTable) {
    store.processor.outputTable = tableName
  }

  if (fromAi) {
    fromAi = false
    return
  }

  const reason = isPlainSelect.value
    ? '因为当前 SQL 查询的结果集没有显式命名，系统已自动命名为'
    : '已自动推断输出表名:'
  store.setSuggestion('sql', {
    category: 'sql',
    status: 'auto',
    content: `${reason} <strong>${tableName}</strong>。`,
    timestamp: Date.now()
  })
}, { immediate: true })

watch(() => store.processor.outputTable, (newVal) => {
  if (fromAi) return
  if (newVal !== lastInferredName.value) {
    delete store.aiSuggestions['sql']
  }
})

watch(() => store.processor.sql, () => {
  queryResult.value = null
  queryError.value = ''
  queryVisible.value = false
})

function onAcceptSuggestion() {
  store.acceptSuggestion('sql')
}

function onRegenerateSuggestion() {
  store.rejectSuggestion('sql')
}
</script>

<style scoped>
.sql-preview {
  margin: 16px 0;
}

.sql-preview__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.sql-preview__row-count {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.sql-preview__error {
  font-size: var(--font-size-xs);
  color: var(--color-error);
  margin: 4px 0 0;
}
</style>
