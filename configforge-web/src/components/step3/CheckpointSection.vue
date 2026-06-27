<template>
  <div class="border border-[var(--color-border-light)] dark:border-[var(--color-border)] rounded-lg overflow-hidden">
    <div
      class="flex items-center gap-2 px-3 py-2 bg-[var(--color-bg-secondary)] dark:bg-[var(--color-surface-hover)] border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] cursor-pointer"
      @click="expanded = !expanded"
    >
      <span class="text-xs font-medium flex-1">数据检查点</span>
      <NTag v-if="rules.length" size="small" type="info">
        {{ rules.length }} 条规则
      </NTag>
      <NButton text size="tiny" @click.stop="expanded = !expanded">
        {{ expanded ? '收起' : '展开' }}
      </NButton>
    </div>

    <div v-if="expanded" class="p-3 space-y-3">
      <div
        v-for="(rule, i) in rules"
        :key="i"
        class="border border-slate-200 dark:border-slate-700 rounded-lg p-3 space-y-2"
      >
        <!-- Type selector + on_failure + delete -->
        <div class="flex items-center gap-2">
          <NSelect
            v-model:value="rule.type"
            :options="ruleTypeOptions"
            size="small"
            style="width: 140px"
            @update:value="onRuleTypeChange(i, $event)"
          />
          <NSelect
            v-model:value="rule.on_failure"
            :options="onFailureOptions"
            size="small"
            style="width: 100px"
          />
          <NButton text type="error" size="tiny" class="ml-auto" @click="removeRule(i)">
            删除
          </NButton>
        </div>

        <!-- Table selector (all types except custom_sql) -->
        <div v-if="needsTable(rule)" class="flex items-center gap-2">
          <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-14 flex-shrink-0">检查表</label>
          <NSelect
            :value="getRuleTable(rule)"
            :options="tableOptions"
            size="small"
            class="flex-1"
            placeholder="默认使用输出表"
            clearable
            @update:value="(v: string) => setRuleTable(rule, v)"
          />
        </div>

        <!-- row_count fields -->
        <template v-if="rule.type === 'row_count'">
          <div class="flex items-center gap-2">
            <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-14 flex-shrink-0">最小行数</label>
            <NInputNumber v-model:value="(rule as RowCountRule).min" size="small" :min="0" style="width: 120px" />
            <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-14 flex-shrink-0">最大行数</label>
            <NInputNumber v-model:value="(rule as RowCountRule).max" size="small" :min="0" style="width: 120px" />
          </div>
        </template>

        <!-- null_rate fields -->
        <template v-if="rule.type === 'null_rate'">
          <div class="flex items-center gap-2">
            <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-14 flex-shrink-0">检查列</label>
            <NSelect
              v-model:value="(rule as NullRateRule).column"
              :options="columnOptions(getRuleTable(rule))"
              size="small"
              class="flex-1"
              placeholder="选择列或手动输入"
              filterable
              tag
            />
            <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-20 flex-shrink-0">最大空值率</label>
            <NInputNumber
              v-model:value="(rule as NullRateRule).max_null_rate"
              size="small"
              :min="0"
              :max="1"
              :step="0.01"
              style="width: 100px"
            />
          </div>
        </template>

        <!-- uniqueness fields -->
        <template v-if="rule.type === 'uniqueness'">
          <div class="flex items-center gap-2">
            <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-14 flex-shrink-0">检查列</label>
            <NSelect
              v-model:value="(rule as UniquenessRule).column"
              :options="columnOptions(getRuleTable(rule))"
              size="small"
              class="flex-1"
              placeholder="选择列或手动输入"
              filterable
              tag
            />
          </div>
        </template>

        <!-- value_range fields -->
        <template v-if="rule.type === 'value_range'">
          <div class="flex items-center gap-2">
            <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-14 flex-shrink-0">检查列</label>
            <NSelect
              v-model:value="(rule as ValueRangeRule).column"
              :options="columnOptions(getRuleTable(rule))"
              size="small"
              class="flex-1"
              placeholder="选择列或手动输入"
              filterable
              tag
            />
            <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-14 flex-shrink-0">最小值</label>
            <NInputNumber v-model:value="(rule as ValueRangeRule).min_value" size="small" style="width: 100px" />
            <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-14 flex-shrink-0">最大值</label>
            <NInputNumber v-model:value="(rule as ValueRangeRule).max_value" size="small" style="width: 100px" />
          </div>
        </template>

        <!-- custom_sql fields -->
        <template v-if="rule.type === 'custom_sql'">
          <div class="space-y-2">
            <label class="text-xs font-medium text-slate-500 dark:text-slate-400 block">SQL 语句</label>
            <textarea
              v-model="(rule as CustomSqlRule).sql"
              rows="3"
              class="w-full font-mono text-xs p-2 border border-slate-200 dark:border-slate-700 rounded resize-y"
              placeholder="SELECT COUNT(*) AS result FROM ..."
            />
            <div class="flex items-center gap-2">
              <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-16 flex-shrink-0">结果列名</label>
              <NInput v-model:value="(rule as CustomSqlRule).result_column" size="small" style="width: 100px" />
              <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-16 flex-shrink-0">比较方式</label>
              <NSelect
                v-model:value="(rule as CustomSqlRule).comparison"
                :options="comparisonOptions"
                size="small"
                style="width: 80px"
              />
              <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-14 flex-shrink-0">期望值</label>
              <NInputNumber
                v-model:value="(rule as CustomSqlRule).expected_value"
                size="small"
                style="width: 100px"
              />
            </div>
          </div>
        </template>

        <!-- enum_check fields -->
        <template v-if="rule.type === 'enum_check'">
          <div class="flex items-center gap-2">
            <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-14 flex-shrink-0">检查列</label>
            <NSelect
              v-model:value="(rule as EnumCheckRule).column"
              :options="columnOptions(getRuleTable(rule))"
              size="small"
              class="flex-1"
              placeholder="选择列或手动输入"
              filterable
              tag
            />
          </div>
          <div class="flex items-center gap-2">
            <label class="text-xs font-medium text-slate-500 dark:text-slate-400 w-14 flex-shrink-0">允许值</label>
            <NInput
              :value="enumValuesText(i)"
              size="small"
              class="flex-1"
              placeholder="值1,值2,值3（逗号分隔）"
              @update:value="updateEnumValues(i, $event)"
            />
          </div>
        </template>
      </div>

      <p v-if="!rules.length" class="text-xs text-slate-400 dark:text-slate-500 text-center py-2">
        暂未配置检查点规则
      </p>

      <NButton dashed size="small" block @click="addRule">+ 添加规则</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  NButton,
  NTag,
  NSelect,
  NInput,
  NInputNumber,
} from 'naive-ui'
import type {
  CheckRule,
  RowCountRule,
  NullRateRule,
  UniquenessRule,
  ValueRangeRule,
  CustomSqlRule,
  EnumCheckRule,
} from '../../types/wizard'

/**
 * CheckpointSection — 数据检查点规则编辑器（限制①第三阶段迁移为命名 widget）。
 *
 * Widget 协议：
 * - modelValue: CheckRule[]（检查点规则数组）
 * - update:modelValue: 规则变更时 emit
 *
 * 额外 props（通过 widgetProps 透传）：
 * - procIndex: 处理器索引
 * - availableTables: 可用表及其列（用于列选择选项）
 */
const props = defineProps<{
  /** 检查点规则数组（widget 协议：modelValue）。 */
  modelValue: CheckRule[]
  procIndex: number
  availableTables?: Array<{ table_name: string; columns: string[] }>
}>()

const emit = defineEmits<{
  'update:modelValue': [rules: CheckRule[]]
}>()

const expanded = ref(false)

const rules = computed<CheckRule[]>({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const ruleTypeOptions = [
  { label: '行数检查', value: 'row_count' },
  { label: '空值率检查', value: 'null_rate' },
  { label: '唯一性检查', value: 'uniqueness' },
  { label: '范围检查', value: 'value_range' },
  { label: '自定义 SQL', value: 'custom_sql' },
  { label: '枚举检查', value: 'enum_check' },
]

const onFailureOptions = [
  { label: '阻断 (block)', value: 'block' },
  { label: '警告 (warn)', value: 'warn' },
]

const comparisonOptions = [
  { label: '≤', value: '<=' },
  { label: '<', value: '<' },
  { label: '=', value: '==' },
  { label: '≠', value: '!=' },
  { label: '>', value: '>' },
  { label: '≥', value: '>=' },
]

const tableOptions = computed(() => {
  if (!props.availableTables) return []
  return props.availableTables.map((t) => ({
    label: t.table_name,
    value: t.table_name,
  }))
})

function columnOptions(tableName: string) {
  if (!tableName || !props.availableTables) return []
  const table = props.availableTables.find((t) => t.table_name === tableName)
  if (!table) return []
  return table.columns.map((c) => ({ label: c, value: c }))
}

function needsTable(rule: CheckRule): boolean {
  return rule.type !== 'custom_sql'
}

function getRuleTable(rule: CheckRule): string {
  if (rule.type === 'custom_sql') return ''
  return rule.table
}

function setRuleTable(rule: CheckRule, value: string): void {
  if (rule.type !== 'custom_sql') {
    rule.table = value
  }
}

function addRule() {
  const newRule: RowCountRule = {
    type: 'row_count',
    table: '',
    min: 0,
    max: undefined,
    on_failure: 'block',
  }
  emit('update:modelValue', [...rules.value, newRule])
  expanded.value = true
}

function removeRule(index: number) {
  const updated = [...rules.value]
  updated.splice(index, 1)
  emit('update:modelValue', updated)
}

function onRuleTypeChange(index: number, newType: string) {
  const oldRule = rules.value[index]
  const base = { on_failure: oldRule.on_failure, table: getRuleTable(oldRule) }

  let newRule: CheckRule
  switch (newType) {
    case 'row_count':
      newRule = { type: 'row_count', ...base, min: 0, max: undefined } as RowCountRule
      break
    case 'null_rate':
      newRule = { type: 'null_rate', ...base, column: '', max_null_rate: 0.05 } as NullRateRule
      break
    case 'uniqueness':
      newRule = { type: 'uniqueness', ...base, column: '' } as UniquenessRule
      break
    case 'value_range':
      newRule = { type: 'value_range', ...base, column: '', min_value: undefined, max_value: undefined } as ValueRangeRule
      break
    case 'custom_sql':
      newRule = { type: 'custom_sql', on_failure: base.on_failure, sql: '', result_column: 'result', comparison: '<=', expected_value: undefined } as CustomSqlRule
      break
    case 'enum_check':
      newRule = { type: 'enum_check', ...base, column: '', allowed_values: [] } as EnumCheckRule
      break
    default:
      newRule = { type: 'row_count', ...base, min: 0, max: undefined } as RowCountRule
  }

  const updated = [...rules.value]
  updated[index] = newRule
  emit('update:modelValue', updated)
}

function enumValuesText(index: number): string {
  const rule = rules.value[index]
  if (rule.type === 'enum_check') {
    return (rule as EnumCheckRule).allowed_values.join(',')
  }
  return ''
}

function updateEnumValues(index: number, text: string) {
  const rule = rules.value[index]
  if (rule.type === 'enum_check') {
    const updated = [...rules.value]
    ;(updated[index] as EnumCheckRule).allowed_values = text
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    emit('update:modelValue', updated)
  }
}
</script>


