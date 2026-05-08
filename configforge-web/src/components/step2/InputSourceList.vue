<template>
  <div class="space-y-4">
    <InputSourceCard
      v-for="(input, idx) in store.inputs"
      :key="idx"
      :input="input"
      :index="idx"
      @update="(val) => store.updateInput(idx, val)"
      @remove="store.removeInput(idx)"
    />

    <!-- Add area -->
    <template v-if="showAddSelector">
      <div class="grid grid-cols-3 gap-3 mt-2">
        <button
          @click="addInput('excel')"
          class="p-4 border-2 border-green-600 bg-green-50 rounded-lg text-center cursor-pointer hover:bg-green-100 transition-colors"
        >
          <span class="text-2xl block mb-2">📊</span>
          <span class="text-sm font-semibold">Excel</span>
          <span class="text-xs text-slate-500 mt-1 block">.xlsx / .xls</span>
        </button>
        <button
          @click="addInput('csv')"
          class="p-4 border-2 border-blue-600 bg-blue-50 rounded-lg text-center cursor-pointer hover:bg-blue-100 transition-colors"
        >
          <span class="text-2xl block mb-2">🗄</span>
          <span class="text-sm font-semibold">CSV</span>
        </button>
        <div class="p-4 border-2 border-dashed border-slate-200 rounded-lg text-center opacity-55 cursor-not-allowed bg-slate-50 relative">
          <span class="absolute top-1.5 right-1.5 px-1.5 py-0.5 bg-amber-50 text-amber-600 text-[10px] font-medium rounded-sm">v0.4</span>
          <span class="text-2xl block mb-2">🔌</span>
          <span class="text-sm font-semibold">Database</span>
        </div>
        <div class="p-4 border-2 border-dashed border-slate-200 rounded-lg text-center opacity-55 cursor-not-allowed bg-slate-50 relative">
          <span class="absolute top-1.5 right-1.5 px-1.5 py-0.5 bg-amber-50 text-amber-600 text-[10px] font-medium rounded-sm">v0.3</span>
          <span class="text-2xl block mb-2">📄</span>
          <span class="text-sm font-semibold">PDF</span>
        </div>
        <div class="p-4 border-2 border-dashed border-slate-200 rounded-lg text-center opacity-55 cursor-not-allowed bg-slate-50 relative">
          <span class="absolute top-1.5 right-1.5 px-1.5 py-0.5 bg-amber-50 text-amber-600 text-[10px] font-medium rounded-sm">v0.4</span>
          <span class="text-2xl block mb-2">🖥</span>
          <span class="text-sm font-semibold">PPT</span>
        </div>
        <div class="p-4 border-2 border-dashed border-slate-200 rounded-lg text-center opacity-55 cursor-not-allowed bg-slate-50 relative">
          <span class="absolute top-1.5 right-1.5 px-1.5 py-0.5 bg-amber-50 text-amber-600 text-[10px] font-medium rounded-sm">v0.5</span>
          <span class="text-2xl block mb-2">🌐</span>
          <span class="text-sm font-semibold">API</span>
        </div>
      </div>
      <button
        @click="showAddSelector = false"
        class="mt-2 w-full text-center text-sm text-slate-400 hover:text-slate-600 transition-colors py-1"
      >取消</button>
    </template>

    <button
      v-if="!showAddSelector"
      @click="showAddSelector = true"
      class="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-slate-200 rounded-lg text-sm text-slate-500 hover:border-blue-300 hover:text-blue-600 transition-colors"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
      添加输入源
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import InputSourceCard from './InputSourceCard.vue'

const store = useWizardStore()
const showAddSelector = ref(false)

function addInput(plugin: 'excel' | 'csv' = 'excel') {
  store.addInput(plugin)
  showAddSelector.value = false
}
</script>
