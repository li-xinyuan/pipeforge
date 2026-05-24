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

    <!-- Multi-processor header -->
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-semibold text-slate-700">处理步骤</h3>
      <NButton size="small" type="primary" dashed :class="{ 'pulse-cta': pulseCta && store.processors.every(p => p.sql.trim() && p.outputTables.length) }" @click="addProcessorAndExpand">+ SQL 步骤</NButton>
    </div>

    <!-- Table rename prompt (checks all processors) -->
    <div v-if="renamePrompt" class="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-3">
      <span class="text-sm text-amber-700 leading-relaxed">
        表名已从 <strong>"{{ renamePrompt.oldName }}"</strong> 改为 <strong>"{{ renamePrompt.newName }}"</strong>，SQL 中引用了旧表名，是否替换？
      </span>
      <NButton size="tiny" type="warning" @click="onReplaceTableName">替换</NButton>
      <NButton size="tiny" @click="renamePrompt = null">忽略</NButton>
    </div>

    <!-- Processor cards -->
    <ProcessorCard
      v-for="(proc, i) in store.processors"
      :key="i"
      :proc="proc"
      :index="i"
      :expanded="expandedIndex === i"
      :can-remove="store.processors.length > 1"
      :available-tables="tableOptions"
      :pulse-sql="pulseCta && !proc.sql.trim() && proc.outputTables.length === 0"
      @toggle-expand="expandedIndex = expandedIndex === i ? -1 : i"
      @remove="store.removeProcessor(i); if (expandedIndex === i) expandedIndex = -1"
      @update="(p: Partial<ProcessorStep>) => store.updateProcessor(i, { ...store.processors[i], ...p })"
    />

    <!-- Validation -->
    <NAlert v-if="store.stepValidation.length" type="warning" class="mt-3">
      <ul class="list-disc pl-4 text-xs">
        <li v-for="msg in store.stepValidation" :key="msg">{{ msg }}</li>
      </ul>
    </NAlert>

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
import type { ProcessorStep } from '../../types/wizard'
import { useWizardStore } from '../../stores/wizard'
import { NCard, NInput, NButton, NTag, NTooltip, NAlert } from 'naive-ui'
import AiSuggestPanel from '../common/AiSuggestPanel.vue'
import ProcessorCard from './ProcessorCard.vue'
import { inferOutputTable } from '../../utils/sql'
import { useAiApi } from '../../composables/useWizardApi'

const store = useWizardStore()
const { getAiSettings } = useAiApi()
const showProcessorChoices = ref(false)
defineProps<{ pulseCta?: boolean }>()
const expandedIndex = ref(0)
const aiConfigured = ref(false)
const lastInferredName = ref('')

onMounted(async () => {
  lastKnownTables.value = store.inputs.map(inp => inp.table.trim()).filter(Boolean)
  const settings = await getAiSettings()
  aiConfigured.value = !!(settings?.enabled && settings?.api_key)
})

function addProcessorAndExpand() {
  store.addProcessor()
  expandedIndex.value = store.processors.length - 1
}

const inputTableNames = computed(() =>
  store.inputs.map(inp => inp.table.trim()).filter(Boolean)
)

// Collect all available table names: from inputs + from earlier processor outputTables
const tableOptions = computed(() => {
  const seen = new Set<string>()
  const options: Array<{ label: string; value: string }> = []

  // Input source tables
  for (const inp of store.inputs) {
    const t = inp.table.trim()
    if (t && !seen.has(t)) {
      seen.add(t)
      options.push({ label: t, value: t })
    }
  }

  // Output tables from processors (theirs are available to later steps)
  for (const proc of store.processors) {
    for (const t of proc.outputTables) {
      if (t && !seen.has(t)) {
        seen.add(t)
        options.push({ label: t + ' (输出)', value: t })
      }
    }
  }

  return options
})

// Step name auto-inference from SQL content
function inferStepName(sql: string): string {
  if (!sql.trim()) return ''
  if (/DELETE\s+FROM/i.test(sql)) return '数据清洗'
  if (/CREATE\s+TABLE/i.test(sql) && /WHERE/i.test(sql)) return '数据过滤'
  if (/GROUP\s+BY/i.test(sql)) return '数据聚合'
  if (/JOIN/i.test(sql)) return '表连接'
  if (/ORDER\s+BY/i.test(sql)) return '数据排序'
  if (/CREATE\s+TABLE/i.test(sql)) return '创建中间表'
  return 'SQL 处理'
}

// Watch input table names: fill first empty processor's SQL
watch(inputTableNames, (tables) => {
  if (tables.length > 0) {
    for (const proc of store.processors) {
      if (!proc.sql.trim()) {
        proc.sql = `SELECT * FROM "${tables[0]}"`
        break
      }
    }
  }
})

// Watch all processors' SQL for inference and auto-suggestion
watch(
  () => store.processors.map(p => ({ sql: p.sql, outputTables: [...p.outputTables] })),
  (newVal, oldVal) => {
    if (!oldVal) return
    for (let i = 0; i < newVal.length; i++) {
      const proc = store.processors[i]
      const trimmed = proc.sql.trim()
      if (!trimmed) continue

      const tableName = inferOutputTable(trimmed)
      lastInferredName.value = tableName

      // Auto-infer step name if empty
      if (!proc.name || !proc.name.trim()) {
        const inferredName = inferStepName(trimmed)
        if (inferredName) {
          store.updateProcessor(i, { ...proc, name: inferredName })
        }
      }

      // Auto-fill output table if empty
      if (proc.outputTables.length === 0 || proc.outputTables.every(t => !t.trim())) {
        store.updateProcessor(i, { ...proc, outputTables: [tableName] })
      }

      // Set auto suggestion
      const isPlainSelect = !(
        /\bCREATE\s+(?:TEMP\s+|TEMPORARY\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\w+\s+AS\b/i.test(trimmed) ||
        /\bINSERT\s+INTO\s+\w+\b/i.test(trimmed) ||
        /\bWITH\s+\w+\s+AS\s*\(/i.test(trimmed)
      )
      const reason = isPlainSelect
        ? '因为当前 SQL 查询的结果集没有显式命名，系统已自动命名为'
        : '已自动推断输出表名:'
      store.setSuggestion('sql', {
        category: 'sql',
        status: 'auto',
        content: `${reason} <strong>${tableName}</strong>。`,
        timestamp: Date.now()
      })
    }
  },
  { deep: true }
)

// Watch outputTables changes to clear suggestion
watch(
  () => store.processors.map(p => [...p.outputTables]),
  (newVal, oldVal) => {
    if (!oldVal) return
    for (let i = 0; i < newVal.length; i++) {
      const newName = newVal[i]?.[0] || ''
      if (newName !== lastInferredName.value) {
        delete store.aiSuggestions['sql']
      }
    }
  },
  { deep: true }
)

// ── Table rename detection ──
const renamePrompt = ref<{ oldName: string; newName: string } | null>(null)
const lastKnownTables = ref<string[]>([])

function checkTableRenames() {
  const currentTables = store.inputs.map(inp => inp.table.trim()).filter(Boolean)
  const prev = lastKnownTables.value

  for (let i = 0; i < Math.min(currentTables.length, prev.length); i++) {
    const oldName = prev[i]
    const newName = currentTables[i]
    if (!oldName || !newName || oldName === newName) continue

    // Check all processors' SQL
    for (const proc of store.processors) {
      const sql = proc.sql.trim()
      if (!sql) continue

      if (i === 0 && sql === `SELECT * FROM "${oldName}"`) {
        proc.sql = `SELECT * FROM "${newName}"`
        break
      }

      if (sql.includes(`"${oldName}"`)) {
        renamePrompt.value = { oldName, newName }
        return
      }
    }
  }

  lastKnownTables.value = [...currentTables]
}

function onReplaceTableName() {
  if (!renamePrompt.value) return
  const { oldName, newName } = renamePrompt.value
  const escaped = oldName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  for (const proc of store.processors) {
    proc.sql = proc.sql.replace(new RegExp(`"${escaped}"`, 'g'), `"${newName}"`)
  }
  renamePrompt.value = null
  lastKnownTables.value = store.inputs.map(inp => inp.table.trim()).filter(Boolean)
}

defineExpose({ checkTableRenames, expandedIndex })

function onAcceptSuggestion() {
  store.acceptSuggestion('sql')
}

function onRegenerateSuggestion() {
  store.rejectSuggestion('sql')
}
</script>

<style scoped>
</style>
