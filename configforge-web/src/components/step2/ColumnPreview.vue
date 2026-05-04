<template>
  <table class="w-full text-sm border-collapse mt-2">
    <thead>
      <tr class="bg-slate-50">
        <th v-for="col in columns" :key="col" class="px-3 py-1.5 text-left text-xs font-medium text-slate-500 border border-slate-200">{{ col }}</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(row, ri) in rows" :key="ri">
        <td v-for="(cell, ci) in row" :key="ci" class="px-3 py-1 text-xs text-slate-700 border border-slate-200">{{ cell }}</td>
      </tr>
    </tbody>
  </table>
</template>
<script setup lang="ts">
defineProps<{ columns: string[]; rows: string[][] }>()
</script>
