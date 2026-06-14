<template>
  <NModal
    :show="visible"
    preset="card"
    title="AI 列分析结果"
    :trap-focus="true"
    :auto-focus="true"
    style="max-width: 520px"
    @update:show="$emit('close')"
  >
    <div class="ai-confirm__body">
      <!-- Analyzing spinner -->
      <div v-if="analyzing" class="ai-confirm__loading">
        <NSpin size="medium" />
        <span class="ai-confirm__loading-text">AI 分析中...</span>
      </div>

      <!-- Error state -->
      <div v-else-if="errorMessage && !parsed" class="ai-confirm__error">
        <span class="ai-confirm__error-icon">⚠</span>
        <span class="ai-confirm__error-text">{{ errorMessage }}</span>
      </div>

      <!-- Raw text fallback -->
      <div v-else-if="rawText && !parsed" class="ai-confirm__raw">
        <p class="ai-confirm__raw-label">AI 返回内容无法解析，你可查看原文后重试：</p>
        <pre>{{ rawText }}</pre>
      </div>

      <!-- Editable fields -->
      <template v-else-if="parsed && !analyzing">
        <!-- Table name section -->
        <div class="ai-confirm__section">
          <p class="ai-confirm__section-title">表名</p>
          <div
            class="ai-confirm__radio-label"
            :class="{ 'ai-confirm__radio-label--active': tableNameOption === 'ai' }"
            @click="tableNameOption = 'ai'"
          >
            <span class="ai-confirm__radio-mark">{{ tableNameOption === 'ai' ? '●' : '○' }}</span>
            <span class="ai-confirm__radio-text">AI 建议：<strong>{{ parsed.tableName }}</strong></span>
          </div>
          <div
            class="ai-confirm__radio-label"
            :class="{ 'ai-confirm__radio-label--active': tableNameOption === 'current' }"
            @click="tableNameOption = 'current'"
          >
            <span class="ai-confirm__radio-mark">{{ tableNameOption === 'current' ? '●' : '○' }}</span>
            <span class="ai-confirm__radio-text">当前值：<strong>{{ input.table }}</strong></span>
          </div>
          <div
            class="ai-confirm__radio-label"
            :class="{ 'ai-confirm__radio-label--active': tableNameOption === 'custom' }"
            @click="tableNameOption = 'custom'"
          >
            <span class="ai-confirm__radio-mark">{{ tableNameOption === 'custom' ? '●' : '○' }}</span>
            <span class="ai-confirm__radio-text">自定义：</span>
            <NInput
              v-model:value="customTableName"
              size="tiny"
              placeholder="输入自定义表名"
              :status="tableNameConflict ? 'error' : undefined"
              @click.stop
            />
          </div>
          <p v-if="tableNameConflict" class="ai-confirm__warn">{{ tableNameConflict }}</p>
        </div>

        <!-- Column types section -->
        <div class="ai-confirm__section">
          <p class="ai-confirm__section-title">列类型</p>
          <div class="ai-confirm__columns">
            <div
              v-for="col in columns"
              :key="col"
              class="ai-confirm__col-row"
            >
              <span class="ai-confirm__col-name">{{ col }}</span>
              <NSelect
                :value="editableColumnTypes[col] || 'string'"
                @update:value="editableColumnTypes[col] = $event"
                :options="columnTypeOptions"
                size="tiny"
                class="ai-confirm__col-select"
              />
            </div>
          </div>
        </div>

        <!-- Param keys section -->
        <div class="ai-confirm__section">
          <p class="ai-confirm__section-title">参数键</p>
          <div class="ai-confirm__param-keys">
            <NTag
              v-for="(key, ki) in editableParamKeys"
              :key="key"
              size="tiny"
              type="info"
              closable
              @close="removeParamKey(ki)"
            >{{ key }}</NTag>
          </div>
          <div class="ai-confirm__add-key">
            <NInput
              v-model:value="newParamKeyInput"
              size="tiny"
              placeholder="新增参数键"
              @keyup.enter="addParamKey"
            />
            <NButton size="tiny" @click="addParamKey" :disabled="!newParamKeyInput.trim()">添加</NButton>
          </div>
        </div>
      </template>
    </div>

    <template #footer>
      <div class="ai-confirm__footer">
        <NButton size="small" @click="$emit('close')" :disabled="analyzing">关闭</NButton>
        <span class="ai-confirm__spacer" />
        <NButton
          v-if="!parsed && !analyzing"
          size="small"
          :type="rawText || errorMessage ? 'warning' : 'info'"
          @click="$emit('regenerate')"
        >重新分析</NButton>
        <NButton
          v-if="parsed && !analyzing"
          size="small"
          type="info"
          @click="$emit('regenerate')"
        >重新生成</NButton>
        <NButton
          v-if="parsed && !analyzing"
          size="small"
          type="success"
          :disabled="!!tableNameConflict"
          @click="onConfirm"
        >确认应用</NButton>
      </div>
    </template>
  </NModal>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import type { InputSource, ConfirmedAnalysis } from '../../types/wizard'
import { NModal, NInput, NButton, NTag, NSelect, NSpin } from 'naive-ui'

interface ParsedResult {
  columnTypes: Record<string, string>
  tableName: string
  paramKeys: string[]
}

const props = defineProps<{
  visible: boolean
  analyzing: boolean
  parsed: ParsedResult | null
  rawText: string | null
  errorMessage: string | null
  input: InputSource
  columns: string[]
  conflictingTableNames: string[]
}>()

const emit = defineEmits<{
  confirm: [confirmed: ConfirmedAnalysis]
  regenerate: []
  close: []
}>()

const columnTypeOptions = [
  { label: 'string', value: 'string' },
  { label: 'number', value: 'number' },
  { label: 'date', value: 'date' },
  { label: 'boolean', value: 'boolean' },
]

const tableNameOption = ref<'ai' | 'current' | 'custom'>('ai')
const customTableName = ref('')
const editableColumnTypes = reactive<Record<string, string>>({})
const editableParamKeys = ref<string[]>([])
const newParamKeyInput = ref('')

const resolvedTableName = computed(() => {
  switch (tableNameOption.value) {
    case 'ai': return props.parsed?.tableName || ''
    case 'current': return props.input.table
    case 'custom': return customTableName.value.trim()
    default: return ''
  }
})

const tableNameConflict = computed(() => {
  const name = resolvedTableName.value
  if (!name) return ''
  if (props.conflictingTableNames.includes(name)) return `表名 "${name}" 已被其他输入源使用`
  return ''
})

function initState() {
  if (!props.visible || !props.parsed) return

  // Init column types from parsed data
  for (const key of Object.keys(editableColumnTypes)) {
    delete editableColumnTypes[key]
  }
  for (const col of props.columns) {
    editableColumnTypes[col] = props.parsed.columnTypes[col] || 'string'
  }

  // Init table name
  tableNameOption.value = props.parsed.tableName ? 'ai' : 'current'
  customTableName.value = ''

  // Init param keys
  editableParamKeys.value = [...props.parsed.paramKeys]
  newParamKeyInput.value = ''
}

watch(() => [props.visible, props.parsed] as const, () => initState())

function addParamKey() {
  const key = newParamKeyInput.value.trim()
  if (key && !editableParamKeys.value.includes(key)) {
    editableParamKeys.value.push(key)
  }
  newParamKeyInput.value = ''
}

function removeParamKey(index: number) {
  editableParamKeys.value.splice(index, 1)
}

function onConfirm() {
  if (tableNameConflict.value || !props.parsed) return
  emit('confirm', {
    columnTypes: { ...editableColumnTypes },
    tableName: resolvedTableName.value,
    paramKeys: [...editableParamKeys.value],
    timestamp: Date.now(),
  })
}
</script>

<style scoped>
.ai-confirm__body {
  max-height: 55vh;
  overflow-y: auto;
}

.ai-confirm__section {
  margin-bottom: 16px;
}

.ai-confirm__section:last-child {
  margin-bottom: 0;
}

.ai-confirm__section-title {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
  margin: 0 0 8px;
}

/* Radio labels */
.ai-confirm__radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-light);
  margin-bottom: 6px;
  cursor: pointer;
  transition: border-color var(--transition-fast), background var(--transition-fast);
}

.ai-confirm__radio-label:last-child {
  margin-bottom: 0;
}

.ai-confirm__radio-label:hover {
  border-color: var(--color-info-border);
}

.ai-confirm__radio-label--active {
  border-color: var(--color-info-border);
  background: var(--color-info-bg);
}

.ai-confirm__radio-mark {
  font-size: 12px;
  color: var(--color-info);
  flex-shrink: 0;
}

.ai-confirm__radio-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.ai-confirm__radio-text strong {
  color: var(--color-text);
}

/* Columns grid */
.ai-confirm__columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.ai-confirm__col-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  background: var(--color-surface-hover);
  border-radius: var(--radius-sm);
}

.ai-confirm__col-name {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.ai-confirm__col-select {
  width: 110px;
}

/* Param keys */
.ai-confirm__param-keys {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-bottom: 8px;
}

.ai-confirm__add-key {
  display: flex;
  gap: 6px;
  align-items: center;
}

/* Loading */
.ai-confirm__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 32px 0;
}

.ai-confirm__loading-text {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
}

/* Error */
.ai-confirm__error {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px;
  background: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  border-radius: var(--radius-md);
}

.ai-confirm__error-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.ai-confirm__error-text {
  font-size: var(--font-size-xs);
  color: var(--color-error);
}

/* Raw text fallback */
.ai-confirm__raw {
  padding: 12px;
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning-border);
  border-radius: var(--radius-md);
}

.ai-confirm__raw-label {
  font-size: var(--font-size-xs);
  color: var(--color-warning);
  margin: 0 0 6px;
}

.ai-confirm__raw pre {
  font-size: 11px;
  color: var(--color-text-muted);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 160px;
  overflow-y: auto;
  margin: 0;
}

/* Warning */
.ai-confirm__warn {
  font-size: var(--font-size-xs);
  color: var(--color-error);
  margin: 4px 0 0;
}

/* Footer */
.ai-confirm__footer {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-confirm__spacer {
  flex: 1;
}
</style>
