<template>
  <div class="processor-card bg-white border border-slate-200 rounded-lg overflow-hidden">
    <!-- Header: name + plugin badge + delete -->
    <div class="flex items-center gap-2 px-3 py-2 bg-slate-50 border-b border-slate-200">
      <span class="text-lg">{{ proc.plugin === 'python' ? '🐍' : '🧪' }}</span>
      <span class="text-sm font-medium truncate flex-1">{{ proc.name || '步骤 ' + (index + 1) }}</span>
      <NTag size="small" :type="proc.plugin === 'python' ? 'warning' : 'success'">{{ proc.plugin === 'python' ? 'Python' : 'SQL' }}</NTag>
      <NTag v-if="proc.checkpoints?.length" size="small" type="info">检查点 ×{{ proc.checkpoints.length }}</NTag>
      <NButton text type="error" size="tiny" class="ml-auto" @click="$emit('remove')">删除</NButton>
    </div>
    <!-- Body -->
    <div class="p-3 space-y-3">
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
    <CheckpointSection
      :checkpoints="proc.checkpoints || []"
      :proc-index="index"
      @update:checkpoints="(rules: CheckRule[]) => $emit('update', { checkpoints: rules } as Partial<ProcessorStep>)"
    />
  </div>
</template>

<script setup lang="ts">
import { NButton, NTag } from 'naive-ui'
import type { ProcessorStep, CheckRule } from '../../types/wizard'
import SqlProcessorContent from './SqlProcessorContent.vue'
import PythonProcessorContent from './PythonProcessorContent.vue'
import CheckpointSection from './CheckpointSection.vue'

defineProps<{
  proc: ProcessorStep
  index: number
  availableTables: Array<{ label: string; value: string }>
  pulseSql?: boolean
}>()

defineEmits<{
  remove: []
  update: [partial: Partial<ProcessorStep>]
}>()
</script>

<style scoped>
.processor-card {
  margin-bottom: 8px;
}
</style>
