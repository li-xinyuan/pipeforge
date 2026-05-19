<template>
  <Teleport to="body">
    <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30" @click.self="$emit('close')">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-xl mx-4 max-h-[85vh] overflow-y-auto">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 class="text-base font-bold text-slate-900">🤖 AI 列分析结果</h3>
          <button @click="$emit('close')" class="text-slate-400 hover:text-slate-600 text-xl leading-none">&times;</button>
        </div>

        <div class="px-6 py-4 space-y-4 text-sm">
          <!-- Empty state: no sources with files -->
          <p v-if="sourceStates.length === 0 && !rawText" class="text-slate-400 text-center py-4">请先上传文件以使用 AI 列分析</p>

          <!-- Raw text fallback -->
          <div v-if="rawText" class="p-3 bg-amber-50 border border-amber-200 rounded-md">
            <p class="text-xs text-amber-700 mb-1">AI 返回内容无法解析为结构化结果：</p>
            <pre class="text-xs text-amber-800 whitespace-pre-wrap max-h-32 overflow-y-auto">{{ rawText }}</pre>
          </div>

          <!-- Join Keys (shared) -->
          <div v-if="joinKeys.length" class="p-3 bg-amber-50 border border-amber-200 rounded-md">
            <h4 class="text-xs font-semibold text-amber-800 mb-1">关联键检测</h4>
            <div v-for="(jk, i) in joinKeys" :key="i" class="text-xs text-amber-700">
              {{ jk.file1 || jk.file }}.{{ jk.column || jk.col }} ↔ {{ jk.file2 }}.{{ jk.column2 || jk.col2 || jk.column || jk.col }}
            </div>
          </div>

          <!-- Per-source sections -->
          <div v-for="src in sourceStates" :key="src.sourceIndex" class="border border-slate-200 rounded-lg p-4">
            <!-- Section header -->
            <div class="flex items-center gap-2 mb-3">
              <span class="text-xs font-semibold text-slate-700">{{ src.label }}</span>
              <span class="text-[10px] text-slate-400">(输入源 {{ src.sourceIndex + 1 }})</span>
            </div>

            <!-- Column types -->
            <div class="mb-3">
              <h4 class="text-xs font-medium text-slate-500 mb-1.5">列类型</h4>
              <div class="grid grid-cols-2 gap-1">
                <div v-for="col in src.columns" :key="col" class="flex items-center justify-between px-2 py-1 bg-slate-50 rounded">
                  <span class="text-xs text-slate-600 truncate mr-2">{{ col }}</span>
                  <select
                    :value="src.columnTypes[col]"
                    @change="src.columnTypes[col] = ($event.target as HTMLSelectElement).value"
                    class="text-xs border border-slate-200 rounded px-1.5 py-0.5 bg-white focus:border-blue-400 focus:outline-none"
                  >
                    <option value="string">string</option>
                    <option value="number">number</option>
                    <option value="date">date</option>
                    <option value="boolean">boolean</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- Table name -->
            <div class="mb-3">
              <h4 class="text-xs font-medium text-slate-500 mb-1.5">表名</h4>
              <div class="flex flex-wrap gap-1.5">
                <label
                  v-for="t in suggestedTableNames"
                  :key="t"
                  class="flex items-center gap-1 px-2 py-0.5 rounded text-xs border transition-colors"
                  :class="suggestedTableNameClasses(src, t)"
                  :title="tableNameConflictHint(src, t)"
                >
                  <input
                    type="radio"
                    :value="t"
                    v-model="src.selectedTableName"
                    :disabled="conflictsFor(src).includes(t) && src.selectedTableName !== t"
                    class="sr-only"
                  />
                  {{ t }}
                  <span v-if="conflictBadgeText(src, t)" class="text-[10px] text-red-400">占用</span>
                </label>
                <input
                  v-model="src.customTableNameInput"
                  @input="src.selectedTableName = src.customTableNameInput"
                  placeholder="自定义表名"
                  class="text-xs border rounded px-2 py-0.5 w-32 focus:outline-none"
                  :class="customTableNameInputClasses(src)"
                />
              </div>
              <p v-if="tableNameConflictMsg(src)" class="text-xs text-red-500 mt-1">{{ tableNameConflictMsg(src) }}</p>
            </div>

            <!-- Param keys -->
            <div>
              <h4 class="text-xs font-medium text-slate-500 mb-1.5">参数键（可多选）</h4>
              <!-- Suggested keys -->
              <div class="flex flex-wrap gap-1.5 mb-1.5">
                <label
                  v-for="k in suggestedParamKeys"
                  :key="k"
                  class="flex items-center gap-1 px-2 py-0.5 rounded text-xs cursor-pointer border transition-colors"
                  :class="src.selectedParamKeys.includes(k) ? 'bg-purple-100 border-purple-400 text-purple-700' : 'bg-white border-slate-200 text-slate-600 hover:border-purple-300'"
                >
                  <input type="checkbox" :value="k" v-model="src.selectedParamKeys" class="sr-only" />
                  {{ k }}
                </label>
              </div>
              <!-- Custom key input -->
              <div class="flex items-center gap-1">
                <input
                  v-model="src.customParamKeyInput"
                  @keyup.enter="addCustomParamKey(src)"
                  placeholder="添加自定义键"
                  class="flex-1 text-xs border border-slate-200 rounded px-2 py-0.5 focus:border-blue-400 focus:outline-none"
                />
                <button
                  @click="addCustomParamKey(src)"
                  class="px-2 py-0.5 text-xs bg-slate-100 text-slate-600 rounded hover:bg-slate-200 flex-shrink-0"
                >添加</button>
              </div>
              <!-- Custom added keys (removable) -->
              <div v-if="customKeysFor(src).length" class="flex flex-wrap gap-1 mt-1.5">
                <span
                  v-for="k in customKeysFor(src)"
                  :key="k"
                  class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[11px] bg-purple-100 text-purple-700 rounded"
                >
                  {{ k }}
                  <button @click="removeCustomKey(src, k)" class="text-purple-400 hover:text-purple-600">&times;</button>
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="px-6 py-3 border-t border-slate-100 flex gap-2">
          <button @click="onConfirm" :disabled="suggesting" class="px-4 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50">确认</button>
          <button @click="$emit('regenerate')" :disabled="suggesting" class="px-4 py-1.5 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50 disabled:opacity-50">{{ suggesting ? '⏳ 分析中...' : '重新生成' }}</button>
          <button @click="$emit('close')" class="px-4 py-1.5 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50 ml-auto">关闭</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { InputSource, UploadedFileMeta, ConfirmedAnalysis } from '../../types/wizard'

interface EditablePerSource {
  sourceIndex: number
  label: string
  columns: string[]
  columnTypes: Record<string, string>
  selectedTableName: string
  selectedParamKeys: string[]
  customParamKeyInput: string
  customTableNameInput: string
}

const props = defineProps<{
  visible: boolean
  suggesting: boolean
  inputs: InputSource[]
  uploadedFiles: Record<string, UploadedFileMeta>
  analysis: Record<string, any>
}>()

const emit = defineEmits<{
  confirm: [results: Array<{ sourceIndex: number; confirmed: ConfirmedAnalysis }>]
  regenerate: []
  close: []
}>()

const sourceStates = ref<EditablePerSource[]>([])
const rawText = ref('')
const joinKeys = ref<any[]>([])
const suggestedTableNames = ref<string[]>([])
const suggestedParamKeys = ref<string[]>([])

watch(() => props.visible, (isVisible) => {
  if (isVisible) initialize()
})

function initialize() {
  const anal = props.analysis
  rawText.value = anal.rawText || ''
  joinKeys.value = anal.joinKeys || []
  suggestedTableNames.value = anal.suggestedTableNames || []
  suggestedParamKeys.value = anal.suggestedParamKeys || []

  let tableNameIdx = 0
  sourceStates.value = props.inputs
    .map((input, i) => ({ input, index: i }))
    .filter(({ input }) => {
      const file = props.uploadedFiles[input.fileId]
      return file && file.columns && file.columns.length > 0
    })
    .map(({ input, index }) => {
      const file = props.uploadedFiles[input.fileId]
      const columnTypes: Record<string, string> = {}
      for (const col of file.columns!) {
        columnTypes[col] = anal.columnTypes?.[col] || 'string'
      }

      return {
        sourceIndex: index,
        label: input.table || file!.originalName,
        columns: file!.columns!,
        columnTypes,
        selectedTableName: input.table || anal.suggestedTableNames?.[tableNameIdx++] || '',
        selectedParamKeys: input.paramKey ? input.paramKey.split(',').filter(Boolean) : [],
        customParamKeyInput: '',
        customTableNameInput: '',
      }
    })
}

function addCustomParamKey(src: EditablePerSource) {
  const key = src.customParamKeyInput.trim()
  if (key && !src.selectedParamKeys.includes(key)) {
    src.selectedParamKeys.push(key)
  }
  src.customParamKeyInput = ''
}

function removeCustomKey(src: EditablePerSource, key: string) {
  src.selectedParamKeys = src.selectedParamKeys.filter(k => k !== key)
}

function customKeysFor(src: EditablePerSource): string[] {
  return src.selectedParamKeys.filter(k => !suggestedParamKeys.value.includes(k))
}

function conflictsFor(src: EditablePerSource): string[] {
  const conflicts: string[] = []
  for (const other of sourceStates.value) {
    if (other.sourceIndex !== src.sourceIndex && other.selectedTableName) {
      conflicts.push(other.selectedTableName)
    }
  }
  // 也要检查不在弹窗中的其他输入源
  for (const inp of props.inputs) {
    const inModal = sourceStates.value.some(s => s.sourceIndex === props.inputs.indexOf(inp))
    if (!inModal && inp.table) {
      conflicts.push(inp.table)
    }
  }
  return conflicts
}

function tableNameConflictMsg(src: EditablePerSource): string {
  const name = src.selectedTableName.trim()
  if (!name) return ''
  const conflicts = conflictsFor(src)
  if (conflicts.includes(name)) return `表名 "${name}" 已被其他输入源使用`
  return ''
}

function isConflictingSuggestion(src: EditablePerSource, name: string): boolean {
  return conflictsFor(src).includes(name) && src.selectedTableName !== name
}

function suggestedTableNameClasses(src: EditablePerSource, name: string): Record<string, boolean> {
  const selected = src.selectedTableName === name
  const conflict = isConflictingSuggestion(src, name)
  return {
    'bg-blue-100 border-blue-400 text-blue-700': selected && !conflict,
    'bg-white border-slate-200 text-slate-600 hover:border-blue-300': !selected && !conflict,
    'bg-slate-100 border-slate-200 text-slate-400 line-through cursor-not-allowed': conflict,
    'cursor-pointer': !conflict,
  }
}

function tableNameConflictHint(src: EditablePerSource, name: string): string {
  return isConflictingSuggestion(src, name) ? '该表名已被其他输入源使用' : ''
}

function conflictBadgeText(src: EditablePerSource, name: string): string {
  return isConflictingSuggestion(src, name) ? '占用' : ''
}

function customTableNameInputClasses(src: EditablePerSource): Record<string, boolean> {
  const hasError = !!tableNameConflictMsg(src)
  const isCustom = src.selectedTableName === src.customTableNameInput && !!src.customTableNameInput
  return {
    'border-red-400 focus:border-red-500': hasError,
    'border-blue-400 bg-blue-50': !hasError && isCustom,
    'border-slate-200 focus:border-blue-400': !hasError && !isCustom,
  }
}

function onConfirm() {
  const results = sourceStates.value.map(src => ({
    sourceIndex: src.sourceIndex,
    confirmed: {
      columnTypes: { ...src.columnTypes },
      tableName: src.selectedTableName,
      paramKeys: [...src.selectedParamKeys],
      timestamp: Date.now(),
    } as ConfirmedAnalysis,
  }))
  emit('confirm', results)
}
</script>
