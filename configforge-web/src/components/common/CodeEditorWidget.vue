<template>
  <!--
    CodeEditorWidget — 代码编辑器命名 widget（限制①第三阶段迁移）。

    CodeEditor 的薄包装，添加 label 支持。通过 schema 的 x-ui-widget: 'code-editor' 引用。
    per-instance 数据通过 widgetProps 透传：
      { language: 'sql'|'python'|'yaml', label: string, required?: boolean,
        placeholder?: string, minHeight?: string }
  -->
  <div>
    <label class="cf-label">
      <span v-if="required" class="cf-required">*</span> {{ label || '代码' }}
    </label>
    <CodeEditor
      :model-value="modelValue"
      :language="language || 'sql'"
      :placeholder="placeholder"
      :min-height="minHeight"
      @update:model-value="$emit('update:modelValue', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import CodeEditor from './CodeEditor.vue'

defineProps<{
  modelValue: string
  language?: 'sql' | 'python' | 'yaml'
  placeholder?: string
  minHeight?: string
  required?: boolean
  label?: string
}>()

defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>
