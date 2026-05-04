<template>
  <div>
    <!-- Output type selector -->
    <div class="grid grid-cols-3 gap-3 mb-5">
      <div class="p-4 border-2 border-green-600 bg-green-50 rounded-lg text-center cursor-default relative">
        <span class="text-2xl block mb-2">📊</span>
        <span class="text-sm font-semibold">Excel</span>
      </div>
      <div class="p-4 border-2 border-dashed border-slate-200 rounded-lg text-center opacity-55 cursor-not-allowed bg-slate-50 relative">
        <span class="absolute top-1.5 right-1.5 px-1.5 py-0.5 bg-amber-50 text-amber-600 text-[10px] font-medium rounded-sm">v0.3</span>
        <span class="text-2xl block mb-2">🗄</span>
        <span class="text-sm font-semibold">CSV</span>
      </div>
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

    <!-- Excel output form -->
    <div class="space-y-4">
      <!-- Template file select -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">模板文件</label>
        <select v-model="outputConfig.template" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none bg-white">
          <option value="">-- 无模板 --</option>
          <option v-for="(f, id) in store.uploadedFiles" :key="id" :value="id">{{ f.originalName }}</option>
        </select>
      </div>

      <!-- Source table dropdown -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">数据源表（source_table）</label>
        <select v-model="outputConfig.sourceTable" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none bg-white">
          <option value="">-- 选择表 --</option>
          <option v-for="t in store.processor.outputTables" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>

      <!-- Sheet name -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">Sheet 名称</label>
        <input v-model="outputConfig.sheet" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none" />
      </div>

      <!-- Filename template -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">输出文件名</label>
        <input v-model="outputConfig.filename" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none" />
      </div>

      <!-- Output directory -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">输出目录</label>
        <input v-model="outputConfig.outputDir" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none" />
      </div>

      <!-- Column mapping -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <label class="text-sm font-medium text-slate-900">列映射</label>
          <div class="flex gap-2">
            <button class="px-2 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">🤖 AI 自动映射</button>
            <button @click="addColumn" class="px-2 py-1 text-xs font-medium bg-white text-slate-700 border border-dashed border-slate-200 rounded-md hover:bg-slate-50">+ 添加列</button>
          </div>
        </div>
        <ColumnMapping v-if="outputConfig.columns.length > 0" :columns="outputConfig.columns" @remove="removeColumn" />
        <p v-else class="text-xs text-slate-400 mt-1">点击"+ 添加列"添加源列到目标列的映射</p>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import type { ExcelOutputConfig } from '../../types/wizard'
import ColumnMapping from './ColumnMapping.vue'

const store = useWizardStore()

const outputConfig = computed<ExcelOutputConfig>(() => {
  if (!store.output) {
    store.setOutput({ plugin: 'excel', config: { type: 'excel', template: '', sheet: 'Sheet1', outputDir: './output/', sourceTable: '', filename: 'output.xlsx', columns: [] } })
  }
  return store.output!.config as ExcelOutputConfig
})

function addColumn() {
  outputConfig.value.columns.push({ source: '', target: '' })
}

function removeColumn(index: number) {
  outputConfig.value.columns.splice(index, 1)
}
</script>
