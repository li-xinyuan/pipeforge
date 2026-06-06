<template>
  <table class="w-full text-sm border-collapse">
    <thead>
      <tr class="bg-slate-50">
        <th class="px-3 py-1.5 text-left text-xs font-medium text-slate-500 border border-slate-200">源列 (source)</th>
        <th class="px-3 py-1.5 text-left text-xs font-medium text-slate-500 border border-slate-200">目标列 (target)</th>
        <th class="w-10 border border-slate-200"></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(col, i) in columns" :key="i">
        <td class="border border-slate-200">
          <NInput v-if="!col.source || editingIndex === i" v-model:value="col.source" size="tiny" placeholder="输入源列名" @blur="editingIndex = null" />
          <span v-else class="group inline-flex items-center gap-1 w-full px-2 py-1 text-xs text-slate-700 bg-slate-50 cursor-pointer hover:bg-slate-100 rounded transition-colors" @click="editingIndex = i">{{ col.source }} <span class="opacity-0 group-hover:opacity-100 text-slate-400 transition-opacity">✏</span></span>
        </td>
        <td class="border border-slate-200">
          <NInput v-model:value="col.target" size="tiny" />
        </td>
        <td class="border border-slate-200 text-center">
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
