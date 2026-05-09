<template>
  <div>
    <!-- Processor type selector -->
    <div class="grid grid-cols-3 gap-3 mb-5">
      <div class="p-4 border-2 border-blue-600 bg-blue-50 rounded-lg text-center cursor-default relative">
        <span class="text-2xl block mb-2">🧪</span>
        <span class="text-sm font-semibold">SQL</span>
        <span class="text-xs text-slate-500 mt-1 block">SQLite 执行</span>
      </div>
      <div class="p-4 border-2 border-dashed border-slate-200 rounded-lg text-center opacity-55 cursor-not-allowed bg-slate-50 relative">
        <span class="absolute top-1.5 right-1.5 px-1.5 py-0.5 bg-amber-50 text-amber-600 text-[10px] font-medium rounded-sm">v0.3</span>
        <span class="text-2xl block mb-2">🔗</span>
        <span class="text-sm font-semibold">Jinja2</span>
      </div>
      <div class="p-4 border-2 border-dashed border-slate-200 rounded-lg text-center opacity-55 cursor-not-allowed bg-slate-50 relative">
        <span class="absolute top-1.5 right-1.5 px-1.5 py-0.5 bg-amber-50 text-amber-600 text-[10px] font-medium rounded-sm">v0.4</span>
        <span class="text-2xl block mb-2">🖥</span>
        <span class="text-sm font-semibold">Python</span>
      </div>
    </div>

    <!-- SQL textarea -->
    <div class="mb-4">
      <label class="block text-sm font-medium text-slate-900 mb-1">SQL</label>
      <textarea v-model="store.processor.sql" class="w-full min-h-[160px] px-3 py-2 text-sm font-mono border border-slate-200 rounded-md focus:border-blue-600 outline-none resize-y leading-relaxed"></textarea>
    </div>
    <div class="flex gap-2 items-center mb-4">
      <button @click="showNlInput = true" class="px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">🤖 AI 生成 SQL</button>
      <button class="px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">🧪 验证语法</button>
      <span v-if="sqlValid" class="text-xs text-green-600 font-medium">✓ 验证通过</span>
    </div>

    <div v-if="showNlInput" class="mt-3 p-3 bg-sky-50 border border-sky-200 rounded-lg">
      <textarea v-model="nlText" placeholder="用自然语言描述你想要的查询，例如：查询每个部门有多少员工，按人数降序" rows="3" class="w-full text-sm border border-sky-200 rounded-md px-3 py-2 focus:outline-none focus:border-sky-400" />
      <div class="flex gap-2 mt-2">
        <button @click="onAiGenerateSql" :disabled="suggesting" class="px-3 py-1 text-xs font-medium bg-sky-600 text-white rounded-md hover:bg-sky-700 disabled:opacity-50">{{ suggesting ? '生成中...' : '生成 SQL' }}</button>
        <button @click="showNlInput = false" class="px-3 py-1 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50">取消</button>
      </div>
      <p v-if="aiError" class="text-xs text-red-500 mt-1">{{ aiError }}</p>
    </div>

    <!-- output_tables -->
    <div class="mb-4">
      <label class="block text-sm font-medium text-slate-900 mb-1">输出表名（output_tables）</label>
      <div class="flex flex-wrap gap-2 items-center">
        <span v-for="(t, i) in store.processor.outputTables" :key="i" class="inline-flex items-center gap-1 px-2.5 py-1 bg-purple-50 text-purple-700 text-sm rounded-full font-medium">
          {{ t }} <span class="cursor-pointer ml-1 opacity-60" @click="store.processor.outputTables.splice(i, 1)">&times;</span>
        </span>
        <template v-if="showTableInput">
          <input
            ref="tableInputRef"
            v-model="newTableName"
            @keyup.enter="confirmAddTable"
            @keyup.escape="cancelAddTable"
            @blur="confirmAddTable"
            placeholder="输入表名后回车"
            class="w-40 px-2 py-1 text-sm border border-blue-300 rounded-md focus:border-blue-600 outline-none"
          />
        </template>
        <button v-else @click="startAddTable" class="px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-dashed border-slate-200 rounded-md hover:bg-slate-50">+ 添加表名</button>
      </div>
      <p class="text-xs text-slate-400 mt-1">声明此 SQL 创建的表名，供后续输出步骤引用</p>
    </div>

    <AiSuggestPanel
      :visible="!!store.aiSuggestions['sql']"
      :content="store.aiSuggestions['sql']?.content || ''"
      @accept="onAcceptSuggestion"
      @regenerate="onRegenerateSuggestion"
    />
  </div>
</template>
<script setup lang="ts">
import { computed, ref, nextTick, watch } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import AiSuggestPanel from '../common/AiSuggestPanel.vue'
import { inferOutputTable } from '../../utils/sql'
import { useAiApi } from '../../composables/useWizardApi'

const store = useWizardStore()
const { suggesting, aiError, askSuggestion } = useAiApi()
const sqlValid = computed(() => store.processor.sql.trim().length > 0)
const showTableInput = ref(false)
const newTableName = ref('')
const tableInputRef = ref<HTMLInputElement>()
const showNlInput = ref(false)
const nlText = ref('')

async function onAiGenerateSql() {
  if (!nlText.value.trim()) return
  const content = await askSuggestion('sql', {
    inputs: store.inputs.map(inp => ({
      name: inp.name, table: inp.table, columns: [],
    })),
    naturalLanguage: nlText.value,
  })
  if (content) {
    try {
      const parsed = JSON.parse(content)
      store.processor.sql = parsed.sql || ''
      if (parsed.outputTables) store.processor.outputTables = parsed.outputTables
      store.setSuggestion('sql', { category: 'sql', status: 'pending', content: parsed.explanation || content, timestamp: Date.now() })
    } catch {
      store.processor.sql = content
    }
    showNlInput.value = false
    nlText.value = ''
  }
}

watch(() => store.processor.sql, (sql) => {
  const trimmed = sql.trim()
  if (!trimmed) {
    delete store.aiSuggestions['sql']
    return
  }

  const tableName = inferOutputTable(trimmed)
  if (!store.processor.outputTables.includes(tableName)) {
    store.processor.outputTables.push(tableName)
  }
  store.setSuggestion('sql', {
    category: 'sql',
    status: 'accepted',
    content: `已自动推断输出表名: <strong>${tableName}</strong>。`,
    timestamp: Date.now()
  })
}, { immediate: true })

function startAddTable() {
  showTableInput.value = true
  nextTick(() => tableInputRef.value?.focus())
}

function confirmAddTable() {
  const name = newTableName.value.trim()
  if (name && !store.processor.outputTables.includes(name)) {
    store.processor.outputTables.push(name)
  }
  newTableName.value = ''
  showTableInput.value = false
}

function cancelAddTable() {
  newTableName.value = ''
  showTableInput.value = false
}

function onAcceptSuggestion() {
  const content = store.aiSuggestions['sql']?.content
  if (!content) return

  const match = content.match(/output_tables\s*(?:设为|set to|include)?\s*[：:]*\s*([a-zA-Z_]\w*)/i)
  if (match) {
    const name = match[1]
    if (!store.processor.outputTables.includes(name)) {
      store.processor.outputTables.push(name)
    }
  }
  store.acceptSuggestion('sql')
}

function onRegenerateSuggestion() {
  store.rejectSuggestion('sql')
}
</script>
