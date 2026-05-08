<template>
  <div class="overflow-x-auto mt-2 rounded-md border border-slate-200">
    <table class="text-sm border-collapse min-w-max">
      <thead>
        <tr class="bg-slate-50">
          <th v-for="col in columns" :key="col" class="px-3 py-1.5 text-left text-xs font-medium text-slate-500 border-b border-slate-200 whitespace-nowrap sticky top-0 bg-slate-50">{{ col }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, ri) in rows" :key="ri" class="border-b border-slate-100 last:border-0">
          <td v-for="(cell, ci) in row" :key="ci" class="px-3 py-1 text-xs text-slate-700 whitespace-nowrap">{{ cell }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup lang="ts">
defineProps<{ columns: string[]; rows: string[][] }>()
</script>
