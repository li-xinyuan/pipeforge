<template>
  <div class="orchestration-result border border-green-200 bg-green-50/40 rounded-lg p-3">
    <p class="text-xs font-medium text-green-700 mb-2">{{ result.explanation || 'AI 规划了以下处理链：' }}</p>
    <div v-for="(step, i) in result.steps" :key="i" class="mb-2 last:mb-0 border border-green-100 bg-white rounded p-2">
      <div class="flex items-center gap-2 mb-1">
        <NTag size="tiny" type="info">SQL</NTag>
        <span class="text-xs font-medium">{{ step.name || '步骤 ' + (i + 1) }}</span>
        <span class="text-[10px] text-slate-400">
          入: {{ step.input_tables?.join(', ') || '源表' }} → 出: {{ step.output_tables?.join(', ') || '未指定' }}
        </span>
      </div>
      <pre class="text-[11px] bg-slate-50 p-2 rounded font-mono overflow-x-auto"><code>{{ step.sql }}</code></pre>
    </div>
    <div v-if="result.parse_error" class="text-xs text-amber-600 mt-2">
      AI 返回格式异常，请尝试重新生成。原始响应：{{ (result.raw || '').slice(0, 300) }}
    </div>
    <div class="flex gap-2 mt-3">
      <NButton size="tiny" type="primary" :disabled="!result.steps?.length" @click="$emit('confirm')">确认并填入向导</NButton>
      <NButton size="tiny" @click="$emit('regenerate')">重新生成</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NTag, NButton } from 'naive-ui'
import type { OrchestrationResult } from '../../types/wizard'

defineProps<{ result: OrchestrationResult }>()
defineEmits<{ confirm: []; regenerate: [] }>()
</script>
