<template>
  <NCard size="small" class="processor-card">
    <template #header>
      <div class="flex items-center gap-2">
        <NDropdown trigger="click" :options="typeOptions" @select="(k: string) => $emit('switchType', k)">
          <NTag size="medium" :type="proc.plugin === 'python' ? 'warning' : 'success'" class="cursor-pointer">{{ proc.plugin === 'python' ? 'Python' : 'SQL' }} ▾</NTag>
        </NDropdown>
        <span class="text-sm font-medium truncate flex-1">{{ proc.name || '步骤 ' + (index + 1) }}</span>
        <NButton text type="error" size="small" @click="$emit('remove')">删除</NButton>
      </div>
    </template>
    <div class="space-y-3">
      <SqlProcessorContent
        v-if="proc.plugin === 'sql'"
        :proc="proc"
        :index="index"
        :available-tables="availableTables"
        :pulse-sql="pulseSql"
        @update="(p: any) => $emit('update', p)"
      />
      <PythonProcessorContent
        v-else-if="proc.plugin === 'python'"
        :proc="proc"
        :index="index"
        :available-tables="availableTables"
        @update="(p: any) => $emit('update', p)"
      />
    </div>
  </NCard>
</template>

<script setup lang="ts">
import { NCard, NButton, NTag, NDropdown } from 'naive-ui'
import type { ProcessorStep } from '../../types/wizard'
import SqlProcessorContent from './SqlProcessorContent.vue'
import PythonProcessorContent from './PythonProcessorContent.vue'

const typeOptions = [
  { label: 'SQL', key: 'sql' },
  { label: 'Python', key: 'python' },
]

defineProps<{
  proc: ProcessorStep
  index: number
  availableTables: Array<{ label: string; value: string }>
  pulseSql?: boolean
}>()

defineEmits<{
  remove: []
  update: [partial: Partial<ProcessorStep>]
  switchType: [plugin: string]
}>()
</script>

<style scoped>
.processor-card {
  margin-bottom: 8px;
}
</style>
