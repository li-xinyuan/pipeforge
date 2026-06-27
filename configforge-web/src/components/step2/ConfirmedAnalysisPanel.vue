<template>
  <!-- Confirmed AI Analysis -->
  <div v-if="confirmedAnalysis" class="mb-4 border border-blue-200 bg-blue-50/40 dark:bg-blue-900/30 rounded-md px-3 py-2">
    <div class="flex items-center gap-2 mb-1.5">
      <span class="text-xs font-medium text-blue-700 dark:text-blue-300">AI 分析确认</span>
    </div>
    <div v-if="Object.keys(confirmedAnalysis.columnTypes).length" class="flex flex-wrap gap-1 mb-1.5">
      <NTag
        v-for="(type, col) in confirmedAnalysis.columnTypes"
        :key="col"
        size="tiny"
        :bordered="false"
        :type="columnTypeTagType(type)"
      >
        {{ col }}: {{ type }}
      </NTag>
    </div>
    <div v-if="confirmedAnalysis.paramKeys.length" class="flex flex-wrap gap-1">
      <span class="text-[10px] text-slate-400 dark:text-slate-500 mr-0.5">Keys:</span>
      <NTag
        v-for="key in confirmedAnalysis.paramKeys"
        :key="key"
        size="tiny"
        type="info"
      >
        {{ key }}
      </NTag>
    </div>
  </div>

  <!-- AI analysis overlay -->
  <div v-if="analyzing" class="absolute inset-0 bg-[var(--color-surface)]/65 backdrop-blur-sm flex flex-col items-center justify-center gap-3 z-10 rounded-md" style="pointer-events: auto; cursor: wait;">
    <NSpin size="medium" />
    <span class="text-sm text-teal-600 font-medium">AI 分析中...</span>
  </div>
</template>

<script setup lang="ts">
import type { ConfirmedAnalysis } from '../../types/wizard'
import { NTag, NSpin } from 'naive-ui'

defineProps<{
  confirmedAnalysis: ConfirmedAnalysis | null
  analyzing: boolean
}>()

function columnTypeTagType(type: string) {
  switch (type) {
    case 'string': return 'success' as const
    case 'number': return 'info' as const
    case 'date': return 'warning' as const
    case 'boolean': return 'error' as const
    default: return 'default' as const
  }
}
</script>
