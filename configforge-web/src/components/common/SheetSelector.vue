<template>
  <!--
    SheetSelector — Excel 工作表选择命名 widget（限制①动态表单）。

    双行为：
    - options.length > 0：渲染 NSelect（从已上传文件解析的工作表列表）
    - options.length === 0：渲染 NInput（手动输入 sheet 名，如尚未上传文件）

    per-instance 数据通过 SchemaForm 的 widgetProps 透传：
      { options: SelectOption[], disabled?: boolean }
  -->
  <div>
    <label class="cf-label">工作表</label>
    <NSelect
      v-if="resolvedOptions.length > 0"
      :value="modelValue"
      :options="(resolvedOptions as never)"
      size="small"
      :disabled="disabled"
      @update:value="$emit('update:modelValue', $event)"
    />
    <NInput
      v-else
      :value="modelValue"
      placeholder="Sheet1"
      size="small"
      :disabled="disabled"
      @update:value="$emit('update:modelValue', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NInput, NSelect } from 'naive-ui'
import type { SelectOption } from '../../composables/widgetRegistry'

const props = defineProps<{
  modelValue: string
  /** 工作表选项（per-instance，来自 fetchPreview 解析的 sheetNames）。 */
  options?: SelectOption[]
  disabled?: boolean
}>()

defineEmits<{
  'update:modelValue': [value: string]
}>()

/** 防御性 normalize：options 未传或非数组时回退为空数组。 */
const resolvedOptions = computed<SelectOption[]>(() =>
  Array.isArray(props.options) ? props.options : []
)
</script>
