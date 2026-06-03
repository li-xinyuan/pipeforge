<template>
  <NCard size="small" class="processor-card">
    <template #header>
      <div class="flex items-center gap-2">
        <span class="text-sm font-medium truncate flex-1">{{ proc.name || '步骤 ' + (index + 1) }}</span>
        <NTag size="medium" :type="proc.plugin === 'python' ? 'warning' : 'success'">{{ proc.plugin === 'python' ? 'Python' : 'SQL' }}</NTag>
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
    <div v-if="proc.checkpoints && proc.checkpoints.length > 0" class="processor-card__checks">
      <span class="text-xs text-slate-400">数据检查: {{ proc.checkpoints.length }} 条规则</span>
    </div>
  </NCard>
</template>

<script setup lang="ts">
import { NCard, NButton, NTag } from 'naive-ui'
import type { ProcessorStep } from '../../types/wizard'
import SqlProcessorContent from './SqlProcessorContent.vue'
import PythonProcessorContent from './PythonProcessorContent.vue'

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
.processor-card__checks {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--color-border-light);
}
</style>
