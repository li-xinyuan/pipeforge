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
import type { ColumnMappingItem } from '../../types/wizard'
import { NButton, useMessage } from 'naive-ui'
import { inferSelectColumns } from '../../utils/sql'
import ColumnMapping from './ColumnMapping.vue'
import AiTriggerButton from '../common/AiTriggerButton.vue'

/**
 * ColumnMappingEditor — 列映射编辑器（限制①第三阶段迁移为命名 widget）。
 *
 * Widget 协议：
 * - modelValue: ColumnMappingItem[]（列映射数组）
 * - update:modelValue: 列映射数组变更时 emit
 *
 * Store 访问保留用于读取上下文（inputs/processors/uploadedFiles），
 * 列数据通过 modelValue/update:modelValue 流转，不再直接写 store。
 * ColumnMapping.vue 的 v-model 就地修改仍通过共享引用更新 store（行为不变）。
 */
const props = defineProps<{
  /** 列映射数组（widget 协议：modelValue）。 */
  modelValue: ColumnMappingItem[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: ColumnMappingItem[]]
}>()

const store = useWizardStore()
const message = useMessage()
const { executeSql } = useWizardApi()
const { suggesting: mappingLoading, askSuggestion } = useAiApi()

const columns = computed(() => props.modelValue)
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
  if (hasChange && props.modelValue.length > 0) {
    emit('update:modelValue', [])
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
  if (store.output?.plugin === 'csv' && props.modelValue.length === 0 && hasCode) {
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
      emit('update:modelValue', result.columns.map(col => ({ source: col, target: col })))
      _lastAutoInferred = true
      return
    }
    message.warning('无法从当前 SQL 中提取列名（可能是 SELECT * 或复杂语句），请手动添加列映射。')
    return
  }
  emit('update:modelValue', cols.map(col => ({ source: col, target: col })))
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
  const targetCols = props.modelValue.map((c: ColumnMappingItem) => c.target)
  const content = await askSuggestion('mapping', {
    sourceColumns: sourceCols,
    targetColumns: targetCols,
  })
  if (content) {
    try {
      const parsed = JSON.parse(content)
      if (parsed.mappings) {
        emit('update:modelValue', parsed.mappings as ColumnMappingItem[])
      }
      store.setSuggestion('mapping', { category: 'mapping', status: 'pending', content, timestamp: Date.now() })
    } catch { /* ignore */ }
  }
}

function addColumn() {
  emit('update:modelValue', [...props.modelValue, { source: '', target: '' }])
}

function removeColumn(index: number) {
  emit('update:modelValue', props.modelValue.filter((_, i) => i !== index))
}

function normalizeColumnName(name: string): string {
  return name.toLowerCase().replace(/[_\s]/g, '')
}

function onMapAll() {
  const sourceCols = getSourceColumns()
  const newColumns = props.modelValue.map(col => {
    if (!col.source && col.target) {
      const match = sourceCols.find(s => s === col.target)
      if (match) return { ...col, source: match }
    }
    return col
  })
  emit('update:modelValue', newColumns)
}

function onSmartMatch() {
  const sourceCols = getSourceColumns()
  const newColumns = props.modelValue.map(col => {
    if (col.source) return col
    const normalizedTarget = normalizeColumnName(col.target)
    const match = sourceCols.find(s => normalizeColumnName(s) === normalizedTarget)
    if (match) return { ...col, source: match }
    return col
  })
  emit('update:modelValue', newColumns)
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
