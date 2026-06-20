<template>
  <!-- Sheet name (Excel) -->
  <div v-if="input.plugin === 'excel'">
    <label class="cf-label">工作表</label>
    <NSelect
      v-if="sheetNames.length > 0"
      :value="(input.config as ExcelInputConfig).sheet"
      @update:value="$emit('update', { ...input, config: { ...input.config, sheet: $event } as ExcelInputConfig })"
      :options="sheetOptions"
      size="small"
      :disabled="analyzing"
    />
    <NInput
      v-else
      :id="`input-sheet-${index}`"
      :value="(input.config as ExcelInputConfig).sheet"
      @update:value="$emit('update', { ...input, config: { ...input.config, sheet: $event } as ExcelInputConfig })"
      placeholder="Sheet1"
      size="small"
      :disabled="analyzing"
    />
  </div>

  <!-- CSV config fields -->
  <template v-if="input.plugin === 'csv'">
    <!-- Delimiter -->
    <div>
      <label class="cf-label">分隔符</label>
      <NInput
        :value="(input.config as CsvInputConfig).delimiter"
        @update:value="$emit('update', { ...input, config: { ...input.config, delimiter: $event } as CsvInputConfig })"
        placeholder=","
        size="small"
        :disabled="analyzing"
      />
    </div>
    <!-- Encoding -->
    <div>
      <label class="cf-label">编码</label>
      <NSelect
        :value="(input.config as CsvInputConfig).encoding"
        @update:value="$emit('update', { ...input, config: { ...input.config, encoding: $event } as CsvInputConfig })"
        :options="ENCODING_OPTIONS"
        size="small"
        :disabled="analyzing"
      />
    </div>
    <!-- Has header -->
    <div class="flex items-center gap-2" style="padding-top: 22px;">
      <NCheckbox
        :checked="(input.config as CsvInputConfig).hasHeader"
        @update:checked="$emit('update', { ...input, config: { ...input.config, hasHeader: $event } as CsvInputConfig })"
        :disabled="analyzing"
      />
      <span class="cf-label" style="margin-bottom: 0;">包含表头</span>
    </div>
  </template>

  <!-- JSON config fields -->
  <template v-if="input.plugin === 'json'">
    <div>
      <label class="cf-label">扁平化分隔符</label>
      <NInput
        :value="(input.config as JsonInputConfig).flattenSeparator"
        @update:value="$emit('update', { ...input, config: { ...input.config, flattenSeparator: $event } as JsonInputConfig })"
        placeholder="."
        size="small"
        :disabled="analyzing"
      />
      <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">嵌套字段展开时使用的分隔符，默认 "."</p>
    </div>
  </template>

  <!-- XML config fields -->
  <template v-if="input.plugin === 'xml'">
    <div>
      <label class="cf-label">行元素路径</label>
      <NInput
        :value="(input.config as XmlInputConfig).rowElement"
        @update:value="$emit('update', { ...input, config: { ...input.config, rowElement: $event } as XmlInputConfig })"
        placeholder="items/item"
        size="small"
        :disabled="analyzing"
      />
      <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">XPath 风格路径，指定 XML 中代表每行数据的元素</p>
    </div>
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { InputSource, CsvInputConfig, ExcelInputConfig, JsonInputConfig, XmlInputConfig } from '../../types/wizard'
import { NInput, NSelect, NCheckbox } from 'naive-ui'
import { ENCODING_OPTIONS } from '../../constants/encodings'

const props = defineProps<{
  input: InputSource
  index: number
  sheetNames: string[]
  analyzing: boolean
}>()

defineEmits<{
  update: [input: InputSource]
}>()

const sheetOptions = computed(() => props.sheetNames.map(s => ({ label: s, value: s })))
</script>
