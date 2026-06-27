<template>
  <!--
    SchemaForm — 通用 JSON schema 驱动表单（限制①动态表单基础设施）。

    通过 schema.properties 渲染通用 widget；支持 `x-ui-widget` 引用命名 widget
    （如 CodeEditor、ConnectionManager），`x-ui-options-from` 引用异步选项 loader。

    跳过字段：
    - `type`：鉴别联合 discriminator，由父组件窄化决定
    - `file`：pipeforge 运行时注入字段，前端不收集
  -->
  <div class="schema-form">
    <div v-for="field in renderableFields" :key="field.key" class="schema-form-field">
      <!-- 命名 widget：完全委托，由 widget 自行管理 v-model -->
      <component
        :is="field.widget"
        v-if="field.widget"
        :model-value="modelValue[field.key] ?? field.default"
        @update:model-value="onUpdate(field.key, $event)"
      />

      <!-- boolean: NCheckbox + label 内联 -->
      <div v-else-if="field.kind === 'boolean'" class="flex items-center gap-2" style="padding-top: 22px;">
        <NCheckbox
          :checked="Boolean(modelValue[field.key] ?? field.default)"
          :disabled="disabled"
          @update:checked="onUpdate(field.key, $event)"
        />
        <span class="cf-label" style="margin-bottom: 0;">{{ field.label }}</span>
      </div>

      <!-- 其他类型: label + 控件两行 -->
      <template v-else>
        <label class="cf-label">{{ field.label }}</label>
        <!-- enum / async options → NSelect -->
        <NSelect
          v-if="field.kind === 'enum' || field.kind === 'async-select'"
          :value="(modelValue[field.key] ?? field.default) as string | null"
          :options="(field.options as never)"
          :loading="field.asyncLoading"
          :disabled="disabled"
          size="small"
          @update:value="onUpdate(field.key, $event)"
        />
        <!-- integer/number → NInputNumber -->
        <NInputNumber
          v-else-if="field.kind === 'number'"
          :value="(modelValue[field.key] ?? field.default) as number | null"
          :disabled="disabled"
          size="small"
          @update:value="onUpdate(field.key, $event)"
        />
        <!-- string 默认 → NInput -->
        <NInput
          v-else
          :value="String(modelValue[field.key] ?? field.default ?? '')"
          :placeholder="field.placeholder"
          :disabled="disabled"
          size="small"
          @update:value="onUpdate(field.key, $event)"
        />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { Component } from 'vue'
import { NInput, NSelect, NInputNumber, NCheckbox } from 'naive-ui'
import { getWidget, getAsyncOptionsLoader, type SelectOption } from '../../composables/widgetRegistry'

/**
 * JSON schema 字段描述（最小子集，按需扩展）。
 */
interface JsonSchemaProperty {
  type?: string
  const?: unknown
  default?: unknown
  enum?: unknown[]
  /** UI hint: 引用命名 widget（如 'code-editor'）。 */
  'x-ui-widget'?: string
  /** UI hint: 引用异步选项 loader（如 'db-tables'）。 */
  'x-ui-options-from'?: string
  /** UI hint: 占位符。 */
  'x-ui-placeholder'?: string
  /** UI hint: 字段标签（默认从 title 或 key 派生）。 */
  'x-ui-label'?: string
}

interface JsonSchema {
  properties?: Record<string, JsonSchemaProperty>
}

type FieldKind = 'string' | 'number' | 'boolean' | 'enum' | 'async-select'

interface RenderableField {
  key: string
  label: string
  placeholder: string
  default: unknown
  kind: FieldKind
  options?: SelectOption[]
  widget?: Component
  asyncLoading: boolean
}

const props = defineProps<{
  modelValue: Record<string, unknown>
  schema: JsonSchema
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, unknown>]
}>()

/** 跳过的字段：discriminator 和 runtime 注入字段。 */
const SKIP_FIELDS = new Set(['type', 'file'])

/** 异步选项加载状态缓存（按 loader name 索引）。 */
const asyncOptionsMap = ref<Record<string, SelectOption[]>>({})
const asyncLoadingMap = ref<Record<string, boolean>>({})

/** 计算可渲染字段列表（顺序与 schema.properties 一致）。 */
const renderableFields = computed<RenderableField[]>(() => {
  const properties = props.schema.properties || {}
  const result: RenderableField[] = []
  for (const [key, prop] of Object.entries(properties)) {
    if (SKIP_FIELDS.has(key)) continue
    const widgetName = prop['x-ui-widget']
    const asyncFrom = prop['x-ui-options-from']
    const widget = widgetName ? getWidget(widgetName) : undefined
    const hasEnum = Array.isArray(prop.enum) && prop.enum.length > 0

    let kind: FieldKind = 'string'
    if (prop.type === 'boolean') kind = 'boolean'
    else if (prop.type === 'integer' || prop.type === 'number') kind = 'number'
    else if (hasEnum) kind = 'enum'
    else if (asyncFrom) kind = 'async-select'

    result.push({
      key,
      label: prop['x-ui-label'] ?? deriveLabel(key),
      placeholder: prop['x-ui-placeholder'] ?? '',
      default: prop.default,
      kind,
      options: hasEnum
        ? prop.enum!.map((v) => ({ label: String(v), value: v as string | number }))
        : asyncFrom
          ? (asyncOptionsMap.value[asyncFrom] || [])
          : undefined,
      widget,
      asyncLoading: asyncFrom ? Boolean(asyncLoadingMap.value[asyncFrom]) : false,
    })
  }
  return result
})

/** 从字段 key 派生中文标签（可按需扩展映射表）。 */
function deriveLabel(key: string): string {
  const known: Record<string, string> = {
    delimiter: '分隔符',
    encoding: '编码',
    hasHeader: '包含表头',
    sheet: '工作表',
    flattenSeparator: '扁平化分隔符',
    rowElement: '行元素路径',
    sql: 'SQL',
    script: '脚本',
    sourceTable: '源表',
    targetTable: '目标表',
    writeMode: '写入模式',
    outputDir: '输出目录',
    filename: '文件名',
    template: '模板',
    batchSize: '批大小',
    createTableIfNotExists: '不存在则建表',
    connectionId: '连接',
    queryType: '查询类型',
    primaryKeyColumns: '主键列',
  }
  return known[key] ?? key
}

function onUpdate(key: string, value: unknown): void {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}

onMounted(() => {
  // 收集所有异步选项 loader，并行加载
  const properties = props.schema.properties || {}
  const asyncNames = new Set<string>()
  for (const prop of Object.values(properties)) {
    if (prop['x-ui-options-from']) {
      asyncNames.add(prop['x-ui-options-from'])
    }
  }
  asyncNames.forEach((name) => loadAsyncOptions(name))
})

async function loadAsyncOptions(name: string): Promise<void> {
  const loader = getAsyncOptionsLoader(name)
  if (!loader) return
  asyncLoadingMap.value[name] = true
  try {
    const options = await loader()
    asyncOptionsMap.value = { ...asyncOptionsMap.value, [name]: options }
  } finally {
    asyncLoadingMap.value[name] = false
  }
}
</script>
