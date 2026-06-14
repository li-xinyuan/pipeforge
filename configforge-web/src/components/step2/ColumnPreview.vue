<template>
  <div class="overflow-x-auto mt-2 rounded-md border border-slate-200 dark:border-slate-700">
    <table class="text-sm border-collapse min-w-max">
      <thead>
        <tr>
          <th v-for="(col, ci) in columns" :key="col" :class="[typeBgColors[columnTypes[ci]] || '', 'px-3 py-1.5 text-left border-b border-slate-200 dark:border-slate-700 whitespace-nowrap sticky top-0']">
            <div class="flex items-center gap-1.5">
              <span class="text-xs font-medium text-slate-700 dark:text-slate-200">{{ col }}</span>
              <span :class="typeBadgeClass(ci)" class="text-[10px] px-1.5 py-0.5 rounded font-medium">{{ columnTypes[ci] }}</span>
            </div>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, ri) in pagedRows" :key="ri" class="border-b border-slate-100 dark:border-slate-700 last:border-0">
          <td v-for="(cell, ci) in row" :key="ci" :class="[typeBgColors[columnTypes[ci]] || '', 'px-3 py-1 text-xs text-slate-700 dark:text-slate-200 whitespace-nowrap']">{{ cell }}</td>
        </tr>
      </tbody>
    </table>
    <div v-if="totalPages > 1" class="flex items-center justify-between px-3 py-1.5 bg-slate-50 dark:bg-slate-700/50 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400">
      <span>{{ (page - 1) * ps + 1 }}-{{ Math.min(page * ps, rows.length) }} / {{ rows.length }} 行</span>
      <div class="flex gap-1">
        <NButton size="tiny" :disabled="page <= 1" @click="page--">上一页</NButton>
        <NButton size="tiny" :disabled="page >= totalPages" @click="page++">下一页</NButton>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed } from 'vue'
import { NButton } from 'naive-ui'

const props = defineProps<{ columns: string[]; rows: string[][]; pageSize?: number }>()
const page = ref(1)
const ps = computed(() => props.pageSize ?? 25)
const totalPages = computed(() => Math.ceil(props.rows.length / ps.value))
const pagedRows = computed(() => props.rows.slice((page.value - 1) * ps.value, page.value * ps.value))

const datePattern = /^\d{4}[-\/]\d{1,2}[-\/]\d{1,2}$|^\d{8}$|^\d{4}年\d{1,2}月\d{1,2}日$|^\d{1,2}[-\/]\d{1,2}[-\/]\d{4}$/

const columnTypes = computed(() =>
  props.columns.map((_, ci) => {
    const samples = props.rows.slice(0, 10).map(r => r[ci]).filter(v => v != null && String(v).trim())
    if (samples.length === 0) return 'TEXT'
    if (samples.every(v => /^(true|false|yes|no|0|1)$/i.test(String(v)))) return 'BOOL'
    if (samples.every(v => /^-?\d+$/.test(String(v)))) return 'INT'
    if (samples.every(v => /^-?\d+\.?\d*$/.test(String(v)) && !isNaN(Number(v)))) return 'NUM'
    if (samples.every(v => datePattern.test(String(v)))) return 'DATE'
    return 'TEXT'
  })
)

const typeColors: Record<string, string> = { INT: 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300', NUM: 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300', BOOL: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300', DATE: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300', TEXT: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300' }
const typeBgColors: Record<string, string> = { INT: 'bg-blue-50/50 dark:bg-blue-900/30', NUM: 'bg-purple-50/50 dark:bg-purple-900/30', BOOL: 'bg-amber-50/50 dark:bg-amber-900/30', DATE: 'bg-green-50/50 dark:bg-green-900/30', TEXT: '' }

function typeBadgeClass(ci: number) { return typeColors[columnTypes.value[ci]] || typeColors.TEXT }
</script>
