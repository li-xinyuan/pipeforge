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
      <!-- Template file upload -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">模板文件</label>
        <template v-if="outputConfig.template && store.uploadedFiles[outputConfig.template]">
          <div class="flex items-center gap-1">
            <span class="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-2 py-1 text-xs flex-1">✓ {{ store.uploadedFiles[outputConfig.template].originalName }}</span>
            <button @click="removeTemplate" class="text-slate-400 hover:text-red-500 p-0.5" title="移除模板">&times;</button>
          </div>
        </template>
        <div v-else @click="triggerTemplateUpload" class="border-2 border-dashed border-slate-200 rounded-lg p-3 text-center cursor-pointer bg-slate-50 hover:border-blue-500 hover:bg-blue-50 transition-colors">
          <div v-if="templateUploading" class="text-sm text-slate-500">上传中...</div>
          <div v-else class="text-sm text-slate-400">📎 点击上传 Excel 模板</div>
          <input type="file" ref="templateInput" class="hidden" accept=".xlsx,.xls" @change="onTemplateSelected" />
        </div>
        <p v-if="templateUploadError" class="text-xs text-red-500 mt-1">{{ templateUploadError }}</p>
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
import { computed, ref } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { useFileUpload } from '../../composables/useFileUpload'
import { useWizardApi } from '../../composables/useWizardApi'
import type { ExcelOutputConfig } from '../../types/wizard'
import ColumnMapping from './ColumnMapping.vue'

const store = useWizardStore()
const { fetchPreview } = useWizardApi()
const { uploading: templateUploading, error: templateUploadError, upload: uploadTemplate } = useFileUpload()
const templateInput = ref<HTMLInputElement>()

const outputConfig = computed<ExcelOutputConfig>(() => store.output.config as ExcelOutputConfig)

function triggerTemplateUpload() { templateInput.value?.click() }

async function onTemplateSelected(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (!files || files.length === 0) return
  const meta = await uploadTemplate(files[0])
  if (meta) {
    store.addFileRef(meta.fileId, meta)
    outputConfig.value.template = meta.fileId

    // 解析模板文件列名，自动填充列映射
    const preview = await fetchPreview(meta.fileId)
    if (preview && preview.columns.length > 0) {
      // 收集所有数据源的列名
      const sourceCols: string[] = []
      for (const input of store.inputs) {
        if (input.fileId) {
          const src = await fetchPreview(input.fileId)
          if (src) sourceCols.push(...src.columns)
        }
      }
      outputConfig.value.columns = preview.columns.map(col => ({
        source: sourceCols.includes(col) ? col : '',
        target: col
      }))
    }
  }
}

function removeTemplate() {
  outputConfig.value.template = ''
  outputConfig.value.columns = []
}

function addColumn() {
  outputConfig.value.columns.push({ source: '', target: '' })
}

function removeColumn(index: number) {
  outputConfig.value.columns.splice(index, 1)
}
</script>
