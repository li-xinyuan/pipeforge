<template>
  <!--
    FilenameTemplate — 文件名模板命名 widget（限制①第二阶段迁移）。

    支持 {{date:%Y%m%d}} / {{time:%H%M%S}} 标签插入，组合成输出文件名。
    从 FileOutputForm 提取，通过 SchemaForm 的 x-ui-widget: 'filename-template' 引用。

    per-instance 数据通过 widgetProps 透传：
      { extension: string }  // '.csv' 或 '.xlsx'
  -->
  <div class="cf-form-group--full">
    <div class="flex items-center gap-1 mb-1">
      <label class="cf-label" style="margin-bottom: 0;">输出文件名</label>
      <NTag size="tiny" class="cursor-pointer" @click="insertTag('{{date:%Y%m%d}}')">年月日</NTag>
      <NTag size="tiny" class="cursor-pointer" @click="insertTag('{{time:%H%M%S}}')">时分秒</NTag>
    </div>
    <div class="flex items-center flex-wrap gap-1 border border-[var(--color-border-light)] rounded px-2 py-1.5 min-h-[32px] bg-[var(--color-surface)]">
      <template v-for="(part, i) in filenameParts" :key="i">
        <NTag size="tiny" :type="part.tag ? 'info' : 'default'" :bordered="true" closable @close="removeTagPart(i)">{{ part.text }}</NTag>
      </template>
      <input
        ref="plainInputRef"
        v-model="plainText"
        class="flex-1 min-w-[40px] outline-none text-sm bg-transparent"
        :placeholder="filenameParts.length === 0 ? '输入文件名' : ''"
        @keyup.enter="commitPlainText"
        @blur="commitPlainText"
      >
      <NButton v-if="baseFilename" text size="tiny" type="error" class="ml-auto" aria-label="清除文件名" @click="clearFilename">✕</NButton>
    </div>
    <span class="text-sm text-slate-400 font-medium">{{ extension }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NTag, NButton } from 'naive-ui'

const props = defineProps<{
  modelValue: string | null
  /** 文件扩展名（含点），如 '.csv'、'.xlsx'。 */
  extension?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const plainInputRef = ref<HTMLInputElement>()
const plainText = ref('')

const extension = computed(() => props.extension ?? '')

/** 去除扩展名后的文件名基础部分。 */
const baseFilename = computed(() => {
  const fn = props.modelValue || ''
  const ext = extension.value
  if (ext && fn.endsWith(ext)) return fn.slice(0, -ext.length)
  return fn
})

/** 将文件名解析为 tag/文本片段序列。 */
const filenameParts = computed(() => {
  const fn = baseFilename.value
  const parts: Array<{ text: string; tag: boolean }> = []
  const re = /\{\{.+?\}\}/g
  let last = 0
  let m
  while ((m = re.exec(fn)) !== null) {
    if (m.index > last) parts.push({ text: fn.slice(last, m.index), tag: false })
    parts.push({ text: m[0], tag: true })
    last = m.index + m[0].length
  }
  if (last < fn.length) parts.push({ text: fn.slice(last), tag: false })
  return parts
})

function insertTag(tag: string): void {
  emit('update:modelValue', baseFilename.value + tag + extension.value)
}

function commitPlainText(): void {
  const v = plainText.value.trim()
  if (!v) return
  emit('update:modelValue', baseFilename.value + v + extension.value)
  plainText.value = ''
}

function removeTagPart(idx: number): void {
  const parts = filenameParts.value
  const removed = parts[idx].text
  emit('update:modelValue', baseFilename.value.replace(removed, '') + extension.value)
}

function clearFilename(): void {
  emit('update:modelValue', extension.value)
  plainText.value = ''
}
</script>
