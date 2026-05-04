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
        <td class="border border-slate-200"><input v-model="col.source" class="w-full px-2 py-1 text-xs border-0 outline-none" /></td>
        <td class="border border-slate-200"><input v-model="col.target" class="w-full px-2 py-1 text-xs border-0 outline-none" /></td>
        <td class="border border-slate-200 text-center"><button @click="$emit('remove', i)" class="text-slate-400 hover:text-red-500">&times;</button></td>
      </tr>
    </tbody>
  </table>
</template>
<script setup lang="ts">
import type { ColumnMappingItem } from '../../types/wizard'
defineProps<{ columns: ColumnMappingItem[] }>()
defineEmits<{ remove: [index: number] }>()
</script>
