<template>
  <div>
    <!-- Initial state: only type selector (no processors yet) -->
    <template v-if="showAddSelector && defaultEmpty">
      <div class="text-center mb-4">
        <p class="text-sm text-slate-500">选择处理方式开始配置数据加工步骤</p>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <span :class="{ 'pulse-cta': pulseCta }" style="display:inline-block;border-radius:8px;">
          <NCard hoverable class="cursor-pointer text-center border-2 border-blue-600 bg-blue-50" @click="pickProcessor('sql')">
            <span class="text-2xl block mb-2">🧪</span>
            <span class="text-sm font-semibold">SQL</span>
            <span class="text-xs text-slate-500 mt-1 block">SQLite 查询处理</span>
          </NCard>
        </span>
        <span :class="{ 'pulse-cta': pulseCta }" style="display:inline-block;border-radius:8px;">
          <NCard hoverable class="cursor-pointer text-center border-2 border-orange-500 bg-orange-50" @click="pickProcessor('python')">
            <span class="text-2xl block mb-2">🐍</span>
            <span class="text-sm font-semibold">Python</span>
            <span class="text-xs text-slate-500 mt-1 block">Python 脚本处理</span>
          </NCard>
        </span>
      </div>
    </template>

    <!-- Normal state: cards + selector + button -->
    <template v-else>
      <!-- Table rename prompt -->
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
        :expanded="true"
        :can-remove="store.processors.length > 1"
        :available-tables="tableOptionsFor(i)"
        :pulse-sql="pulseCta && (proc.plugin === 'sql' ? !proc.sql.trim() : !proc.script.trim()) && proc.outputTables.length === 0"
        @remove="store.removeProcessor(i)"
        @update="(p: Partial<ProcessorStep>) => store.updateProcessor(i, { ...store.processors[i], ...p } as ProcessorStep)"
      />

      <!-- Type selector for adding more steps -->
      <template v-if="showAddSelector">
        <div class="flex items-center justify-between mb-2 mt-3">
          <span class="text-sm font-semibold text-slate-700">选择处理方式</span>
          <NButton text type="error" size="small" @click="showAddSelector = false">取消</NButton>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <span style="display:inline-block;border-radius:8px;">
            <NCard hoverable class="cursor-pointer text-center border-2 border-blue-600 bg-blue-50" @click="pickProcessor('sql')">
              <span class="text-2xl block mb-2">🧪</span>
              <span class="text-sm font-semibold">SQL</span>
              <span class="text-xs text-slate-500 mt-1 block">SQLite 查询处理</span>
            </NCard>
          </span>
          <span style="display:inline-block;border-radius:8px;">
            <NCard hoverable class="cursor-pointer text-center border-2 border-orange-500 bg-orange-50" @click="pickProcessor('python')">
              <span class="text-2xl block mb-2">🐍</span>
              <span class="text-sm font-semibold">Python</span>
              <span class="text-xs text-slate-500 mt-1 block">Python 脚本处理</span>
            </NCard>
          </span>
        </div>
      </template>

      <!-- Add button -->
      <NButton
        v-if="!showAddSelector"
        dashed
        block
        class="mt-3"
        :class="{ 'pulse-cta': pulseCta && store.processors.every(p => (p.plugin === 'sql' ? p.sql.trim() : p.script.trim()) && p.outputTables.length) }"
        @click="showAddSelector = true"
      >添加处理步骤</NButton>

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
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { ProcessorStep } from '../../types/wizard'
import { useWizardStore } from '../../stores/wizard'
import { NCard, NButton, NTag, NAlert } from 'naive-ui'
import AiSuggestPanel from '../common/AiSuggestPanel.vue'
import ProcessorCard from './ProcessorCard.vue'
import { inferOutputTable } from '../../utils/sql'
import { useAiApi } from '../../composables/useWizardApi'

const store = useWizardStore()
const { getAiSettings } = useAiApi()
const props = defineProps<{ pulseCta?: boolean }>()
const aiConfigured = ref(false)
const lastInferredName = ref('')

const hasNoSteps = computed(() =>
  store.processors.length === 0 || store.processors.every(p =>
    (p.plugin === 'sql' ? !p.sql.trim() : !p.script.trim()) &&
    !p.name.trim() &&
    p.outputTables.length === 0
  )
)

const defaultEmpty = computed(() =>
  store.processors.length === 1 && hasNoSteps.value
)

const showAddSelector = ref(defaultEmpty.value)

function pickProcessor(plugin: 'sql' | 'python') {
  const baseName = plugin === 'python' ? 'Python 脚本' : 'SQL 查询'
  const sameType = store.processors.filter(p => p.plugin === plugin).length
  const name = defaultEmpty.value ? baseName : `${baseName} ${sameType + 1}`
  const step = plugin === 'python'
    ? { name, plugin: 'python' as const, script: '', inputTables: [], outputTables: [] }
    : { name, plugin: 'sql' as const, sql: '', inputTables: [], outputTables: [] }
  if (defaultEmpty.value) {
    store.processors[0] = step
  } else {
    store.addProcessor(plugin)
    store.processors[store.processors.length - 1] = step
  }
  showAddSelector.value = false
  // Trigger SQL fill for the newly created processor
  const tables = inputTableNames.value
  const last = store.processors[store.processors.length - 1]
  if (plugin === 'sql' && tables.length > 0 && last.plugin === 'sql' && !last.sql.trim()) {
    last.sql = `SELECT * FROM "${tables[0]}"`
  }
}

onMounted(async () => {
  lastKnownTables.value = store.inputs.map(inp => inp.table.trim()).filter(Boolean)
  const settings = await getAiSettings()
  aiConfigured.value = !!(settings?.enabled && settings?.api_key)
})

const inputTableNames = computed(() =>
  store.inputs.map(inp => inp.table.trim()).filter(Boolean)
)

function tableOptionsFor(currentIndex: number) {
  const seen = new Set<string>()
  const options: Array<{ label: string; value: string }> = []
  // Input source tables
  for (const inp of store.inputs) {
    const t = inp.table.trim()
    if (t && !seen.has(t)) { seen.add(t); options.push({ label: t, value: t }) }
  }
  // Previous processors' output tables (not current or later ones)
  for (let i = 0; i < currentIndex; i++) {
    for (const t of store.processors[i].outputTables) {
      if (t && !seen.has(t)) { seen.add(t); options.push({ label: t + ' (上一步)', value: t }) }
    }
  }
  return options
}

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

function inferPythonStepName(script: string): string {
  if (!script.trim()) return ''
  if (/DELETE\s+FROM/i.test(script)) return '数据清洗'
  if (/CREATE\s+TABLE/i.test(script) && /WHERE/i.test(script)) return '数据过滤'
  if (/GROUP\s+BY/i.test(script)) return '数据聚合'
  if (/JOIN/i.test(script)) return '表连接'
  if (/import\s+re|re\.sub|re\.match|re\.findall/i.test(script)) return '正则提取'
  if (/import\s+requests|urllib|httpx/i.test(script)) return 'API 调用'
  return 'Python 处理'
}

function inferPythonOutputTable(script: string): string | null {
  const m = script.match(/CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["']?(\w+)["']?/i)
  return m ? m[1] : null
}

watch(inputTableNames, (tables) => {
  if (tables.length > 0 && !defaultEmpty.value) {
    for (const proc of store.processors) {
      if (proc.plugin === 'sql' && !proc.sql.trim()) {
        proc.sql = `SELECT * FROM "${tables[0]}"`
        break
      }
    }
  }
})

watch(
  () => store.processors.map(p => ({ code: p.plugin === 'sql' ? p.sql : p.script, outputTables: [...p.outputTables] })),
  (newVal, oldVal) => {
    if (!oldVal) return
    for (let i = 0; i < newVal.length; i++) {
      const proc = store.processors[i]
      if (proc.plugin === 'python') {
        const script = proc.script.trim()
        if (!script) continue
        if (!proc.name || !proc.name.trim()) {
          const name = inferPythonStepName(script)
          if (name) store.updateProcessor(i, { ...proc, name })
        }
        if (proc.outputTables.length === 0 || proc.outputTables.every(t => !t.trim())) {
          const tableName = inferPythonOutputTable(script) || `step_${i + 1}_output`
          store.updateProcessor(i, { ...proc, outputTables: [tableName] })
        }
        continue
      }
      if (proc.plugin !== 'sql') continue
      const trimmed = proc.sql.trim()
      if (!trimmed) continue
      const tableName = inferOutputTable(trimmed)
      lastInferredName.value = tableName
      if (!proc.name || !proc.name.trim()) {
        const inferredName = inferStepName(trimmed)
        if (inferredName) store.updateProcessor(i, { ...proc, name: inferredName })
      }
      if (proc.outputTables.length === 0 || proc.outputTables.every(t => !t.trim())) {
        store.updateProcessor(i, { ...proc, outputTables: [tableName] })
      }
      const isPlainSelect = !(
        /\bCREATE\s+(?:TEMP\s+|TEMPORARY\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\w+\s+AS\b/i.test(trimmed) ||
        /\bINSERT\s+INTO\s+\w+\b/i.test(trimmed) ||
        /\bWITH\s+\w+\s+AS\s*\(/i.test(trimmed)
      )
      store.setSuggestion('sql', {
        category: 'sql', status: 'auto',
        content: `${isPlainSelect ? '系统已自动命名为' : '已自动推断输出表名:'} <strong>${tableName}</strong>。`,
        timestamp: Date.now()
      })
    }
  },
  { deep: true }
)

const renamePrompt = ref<{ oldName: string; newName: string } | null>(null)
const lastKnownTables = ref<string[]>([])

function checkTableRenames() {
  const currentTables = store.inputs.map(inp => inp.table.trim()).filter(Boolean)
  const prev = lastKnownTables.value
  for (let i = 0; i < Math.min(currentTables.length, prev.length); i++) {
    const oldName = prev[i]; const newName = currentTables[i]
    if (!oldName || !newName || oldName === newName) continue
    for (const proc of store.processors) {
      if (proc.plugin !== 'sql') continue
      if (i === 0 && proc.sql.trim() === `SELECT * FROM "${oldName}"`) { proc.sql = `SELECT * FROM "${newName}"`; break }
      if (proc.sql.includes(`"${oldName}"`)) { renamePrompt.value = { oldName, newName }; return }
    }
  }
  lastKnownTables.value = [...currentTables]
}

function onReplaceTableName() {
  if (!renamePrompt.value) return
  const { oldName, newName } = renamePrompt.value
  const escaped = oldName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  for (const proc of store.processors) {
    if (proc.plugin === 'sql') proc.sql = proc.sql.replace(new RegExp(`"${escaped}"`, 'g'), `"${newName}"`)
  }
  renamePrompt.value = null
  lastKnownTables.value = store.inputs.map(inp => inp.table.trim()).filter(Boolean)
}

defineExpose({ checkTableRenames })

function onAcceptSuggestion() { store.acceptSuggestion('sql') }
function onRegenerateSuggestion() { store.rejectSuggestion('sql') }

watch(() => hasNoSteps.value, (v) => {
  if (v) showAddSelector.value = true
})
</script>
