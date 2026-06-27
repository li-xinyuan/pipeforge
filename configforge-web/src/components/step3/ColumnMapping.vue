<template>
  <table class="w-full text-sm border-collapse">
    <thead>
      <tr class="bg-slate-50 dark:bg-slate-700/50">
        <th class="px-3 py-1.5 text-left text-xs font-medium text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">源列 (source)</th>
        <th class="px-3 py-1.5 text-left text-xs font-medium text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">目标列 (target)</th>
        <th class="w-10 border border-slate-200 dark:border-slate-700" />
      </tr>
    </thead>
    <tbody>
      <tr v-for="(col, i) in columns" :key="i">
        <td class="border border-slate-200 dark:border-slate-700">
          <NInput v-if="!col.source || editingIndex === i" v-model:value="col.source" size="tiny" placeholder="输入源列名" @blur="editingIndex = null" />
          <span v-else class="column-source" @click="editingIndex = i">{{ col.source }} <span class="column-source__edit-icon">✏</span></span>
        </td>
        <td class="border border-slate-200 dark:border-slate-700">
          <NInput v-model:value="col.target" size="tiny" />
        </td>
        <td class="border border-slate-200 dark:border-slate-700 text-center">
          <NButton text size="tiny" type="error" @click="$emit('remove', i)">删除</NButton>
        </td>
      </tr>
    </tbody>
  </table>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { NInput, NButton } from 'naive-ui'
import type { ColumnMappingItem } from '../../types/wizard'
defineProps<{ columns: ColumnMappingItem[] }>()
defineEmits<{ remove: [index: number] }>()

const editingIndex = ref<number | null>(null)
</script>

<style scoped>
.column-source {
  display: block;
  width: 100%;
  padding: 2px 6px;
  font-size: 0.75rem;
  color: var(--color-text, #334155);
  background: var(--color-surface, #f8fafc);
  cursor: pointer;
  border-radius: var(--radius-sm, 4px);
  transition: background 0.15s;
}

.column-source:hover {
  background: var(--color-primary-bg, #f0fdfa);
}

.column-source__edit-icon {
  opacity: 0;
  font-size: 0.65rem;
  margin-left: 4px;
  transition: opacity 0.15s;
}

.column-source:hover .column-source__edit-icon {
  opacity: 0.6;
}
</style>
