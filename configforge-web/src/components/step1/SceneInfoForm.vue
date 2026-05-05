<template>
  <div class="bg-white border border-slate-200 rounded-lg p-6">
    <h2 class="text-base font-semibold mb-5">场景信息</h2>
    <p class="text-xs text-slate-400 mb-4" style="margin-top:-12px">定义流水线的基本信息，后续步骤中可添加数据源、配置处理逻辑和输出格式</p>
    <div class="grid grid-cols-2 gap-4 mb-4">
      <div>
        <label for="scene-name" class="block text-sm font-medium text-slate-900 mb-1">场景名称</label>
        <input id="scene-name" v-model="store.scene.name" class="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none transition-colors h-9" />
      </div>
      <div>
        <label for="scene-version" class="block text-sm font-medium text-slate-900 mb-1">版本</label>
        <input id="scene-version" v-model="store.scene.version" class="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none transition-colors h-9" />
      </div>
    </div>
    <div class="mb-4">
      <label for="scene-description" class="block text-sm font-medium text-slate-900 mb-1">场景描述</label>
      <input id="scene-description" v-model="store.scene.description" class="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none transition-colors h-9" />
    </div>

    <div class="mb-4">
      <label class="block text-sm font-medium text-slate-900 mb-1">上传数据文件</label>
      <div class="border-2 border-dashed border-slate-200 rounded-lg p-6 text-center cursor-pointer bg-slate-50 hover:border-blue-600 hover:bg-blue-50 transition-colors" @click="triggerUpload">
        <div class="text-2xl mb-1 opacity-60">📎</div>
        <div class="text-sm text-slate-500">拖拽或点击上传 Excel 文件</div>
        <div class="text-xs text-slate-400 mt-1">.xlsx .xls &nbsp;|&nbsp; 最大 50MB</div>
        <input type="file" ref="fileInput" class="hidden" accept=".xlsx,.xls" @change="onFileSelected" />
      </div>
      <div class="mt-3" v-if="Object.keys(store.uploadedFiles).length > 0">
        <span v-for="(f, id) in store.uploadedFiles" :key="id" class="inline-flex items-center gap-1 px-3 py-1 bg-green-50 border border-green-200 rounded-full text-sm text-green-700 mr-1 mb-1">
          ✓ {{ f.originalName }}
        </span>
      </div>
    </div>

    <ErrorBanner v-if="uploadError" level="error" :message="uploadError" />
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { useFileUpload } from '../../composables/useFileUpload'
import ErrorBanner from '../common/ErrorBanner.vue'

const store = useWizardStore()
const { uploading, error: uploadError, upload } = useFileUpload()
const fileInput = ref<HTMLInputElement>()

function triggerUpload() { fileInput.value?.click() }

async function onFileSelected(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (!files || files.length === 0) return
  for (const file of Array.from(files)) {
    const meta = await upload(file)
    if (meta) store.addFileRef(meta.fileId, meta)
  }
}
</script>
