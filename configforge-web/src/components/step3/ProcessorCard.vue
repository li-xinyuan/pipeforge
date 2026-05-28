<template>
  <NCard size="small" class="processor-card">
    <template #header>
      <div class="flex items-center gap-2">
        <NTag size="tiny" :type="proc.plugin === 'python' ? 'warning' : 'info'" class="cursor-pointer" @click="$emit('switchType')">{{ proc.plugin === 'python' ? 'Python' : 'SQL' }}</NTag>
        <span class="text-sm font-medium truncate flex-1">{{ proc.name || '步骤 ' + (index + 1) }}</span>
        <NButton text size="tiny" type="error" @click="$emit('remove')" :disabled="!canRemove">删除</NButton>
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
import { NCard, NButton, NTag } from 'naive-ui'
import type { ProcessorStep } from '../../types/wizard'
import SqlProcessorContent from './SqlProcessorContent.vue'
import PythonProcessorContent from './PythonProcessorContent.vue'

defineProps<{
  proc: ProcessorStep
  index: number
  canRemove: boolean
  availableTables: Array<{ label: string; value: string }>
  pulseSql?: boolean
}>()

defineEmits<{
  remove: []
  update: [partial: Partial<ProcessorStep>]
  switchType: []
}>()
</script>

<style scoped>
.processor-card {
  margin-bottom: 8px;
}
</style>
