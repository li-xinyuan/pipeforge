<template>
  <div class="overflow-x-auto mt-2 rounded-md border border-slate-200">
    <table class="text-sm border-collapse min-w-max">
      <thead>
        <tr class="bg-slate-50">
          <th v-for="col in columns" :key="col" class="px-3 py-1.5 text-left text-xs font-medium text-slate-500 border-b border-slate-200 whitespace-nowrap sticky top-0 bg-slate-50">{{ col }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, ri) in pagedRows" :key="ri" class="border-b border-slate-100 last:border-0">
          <td v-for="(cell, ci) in row" :key="ci" class="px-3 py-1 text-xs text-slate-700 whitespace-nowrap">{{ cell }}</td>
        </tr>
      </tbody>
    </table>
    <div v-if="totalPages > 1" class="flex items-center justify-between px-3 py-1.5 bg-slate-50 border-t border-slate-200 text-xs text-slate-500">
      <span>{{ (page - 1) * ps + 1 }}-{{ Math.min(page * ps, rows.length) }} / {{ rows.length }} 行</span>
      <div class="flex gap-1">
        <button :disabled="page <= 1" @click="page--" class="px-2 py-0.5 rounded border border-slate-300 disabled:opacity-30 hover:bg-slate-100">上一页</button>
        <button :disabled="page >= totalPages" @click="page++" class="px-2 py-0.5 rounded border border-slate-300 disabled:opacity-30 hover:bg-slate-100">下一页</button>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{ columns: string[]; rows: string[][]; pageSize?: number }>()
const page = ref(1)
const ps = computed(() => props.pageSize ?? 25)
const totalPages = computed(() => Math.ceil(props.rows.length / ps.value))
const pagedRows = computed(() => props.rows.slice((page.value - 1) * ps.value, page.value * ps.value))
</script>
