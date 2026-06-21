<template>
  <template v-if="store.output?.plugin === 'excel'">
    <!-- Template file upload (Excel only, drag-and-drop style) -->
    <div class="cf-form-group--full">
      <label class="cf-label">模板文件</label>
      <template v-if="excelConfig.template && store.uploadedFiles[excelConfig.template]">
        <div class="flex items-center gap-1">
          <NTag type="success" size="small" class="truncate">
            {{ store.uploadedFiles[excelConfig.template].originalName }}
          </NTag>
          <NButton text size="tiny" type="error" @click="$emit('remove-template')">移除</NButton>
        </div>
      </template>
      <NUpload
        v-else
        ref="templateUploadRef"
        :custom-request="handleTemplateUpload"
        :show-file-list="false"
        accept=".xlsx,.xls"
        class="w-full"
      >
        <div class="border-2 border-dashed rounded-lg py-4 px-6 text-center cursor-pointer transition-colors border-slate-300 hover:border-teal-400 hover:bg-teal-50/30">
          <span class="text-2xl block mb-1.5">{{ templateUploading ? '⏳' : '📤' }}</span>
          <span class="text-sm text-slate-500 block">{{ templateUploading ? '上传中...' : '将模板文件拖拽到此处，或点击选择文件' }}</span>
          <span class="text-xs text-slate-400 mt-1 block">支持 .xlsx / .xls 格式</span>
        </div>
      </NUpload>
      <p v-if="templateUploadError" class="text-xs text-red-500 mt-1">{{ templateUploadError }}</p>
    </div>

    <!-- Sheet name (Excel only, disabled until template uploaded) -->
    <div>
      <label class="cf-label">Sheet 名称</label>
      <NSelect
        v-if="templateSheets.length > 0"
        :value="excelConfig.sheet"
        @update:value="(v: string) => { updateExcelConfig({ sheet: v }); $emit('sheet-change', v) }"
        :options="templateSheets.map(s => ({ label: s, value: s }))"
        placeholder="选择 Sheet"
        size="small"
      />
      <NInput
        v-else
        :value="excelConfig.sheet"
        :disabled="!excelConfig.template"
        @update:value="v => updateExcelConfig({ sheet: v })"
        placeholder="Sheet1"
        size="small"
      />
    </div>
  </template>

  <!-- Filename template (Excel & CSV) -->
  <div v-if="store.output?.plugin !== 'database'" class="cf-form-group--full">
    <div class="flex items-center gap-1 mb-1">
      <label class="cf-label" style="margin-bottom: 0;">输出文件名</label>
      <NTag size="tiny" class="cursor-pointer" @click="insertTag('{{date:%Y%m%d}}')">年月日</NTag>
      <NTag size="tiny" class="cursor-pointer" @click="insertTag('{{time:%H%M%S}}')">时分秒</NTag>
    </div>
    <div class="flex items-center flex-wrap gap-1 border border-[var(--color-border-light)] rounded px-2 py-1.5 min-h-[32px] bg-[var(--color-surface)]">
      <template v-for="(part, i) in filenameParts" :key="i">
        <NTag size="tiny" :type="part.tag ? 'info' : 'default'" :bordered="true" closable @close="removeTagPart(i)">{{ part.text }}</NTag>
      </template>
      <input
        ref="plainInputRef"
        v-model="plainText"
        class="flex-1 min-w-[40px] outline-none text-sm bg-transparent"
        :placeholder="filenameParts.length === 0 ? '输入文件名' : ''"
        @keyup.enter="commitPlainText"
        @blur="commitPlainText"
      />
      <NButton v-if="baseFilename" text size="tiny" type="error" class="ml-auto" aria-label="清除文件名" @click="clearFilename">✕</NButton>
    </div>
    <span class="text-sm text-slate-400 font-medium">{{ fileExtension }}</span>
  </div>

  <!-- Delimiter (CSV only) -->
  <div v-if="store.output?.plugin === 'csv'">
    <label class="cf-label">分隔符</label>
    <NInput
      :value="csvConfig.delimiter"
      @update:value="updateCsvConfig({ delimiter: $event })"
      size="small"
    />
  </div>

  <!-- Encoding (CSV only) -->
  <div v-if="store.output?.plugin === 'csv'">
    <label class="cf-label">编码</label>
    <NSelect
      :value="csvConfig.encoding"
      @update:value="updateCsvConfig({ encoding: $event })"
      :options="ENCODING_OPTIONS"
      size="small"
    />
  </div>

  <!-- Output directory (Excel & CSV) -->
  <div v-if="store.output?.plugin !== 'database'">
    <label class="cf-label">输出目录</label>
    <NInput v-model:value="fileOutputConfig!.outputDir" size="small" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { useFileUpload } from '../../composables/useFileUpload'
import { useWizardApi } from '../../composables/useWizardApi'
import type { ExcelOutputConfig, CsvOutputConfig } from '../../types/wizard'
import type { UploadCustomRequestOptions } from 'naive-ui'
import { NInput, NButton, NTag, NUpload, NSelect } from 'naive-ui'
import { ENCODING_OPTIONS } from '../../constants/encodings'
import { useMessage } from 'naive-ui'

const store = useWizardStore()
const message = useMessage()
const { fetchPreview } = useWizardApi()
const { uploading: templateUploading, error: templateUploadError, upload: uploadTemplate } = useFileUpload()

const templateUploadRef = ref<InstanceType<typeof NUpload>>()
const templateSheets = ref<string[]>([])
const plainInputRef = ref<HTMLInputElement>()
const plainText = ref('')

const emit = defineEmits<{
  'remove-template': []
  'sheet-change': [sheet: string]
  'template-uploaded': []
}>()

const fileOutputConfig = computed(() => store.output?.plugin !== 'database' ? store.output!.config as ExcelOutputConfig | CsvOutputConfig : null)
const fileExtension = computed(() => {
  if (store.output?.plugin === 'csv') return '.csv'
  if (store.output?.plugin === 'database') return ''
  return '.xlsx'
})
const excelConfig = computed(() => store.output!.config as ExcelOutputConfig)
const csvConfig = computed(() => store.output!.config as CsvOutputConfig)

const baseFilename = computed(() => {
  const fn = fileOutputConfig.value?.filename || ''
  const ext = fileExtension.value
  return fn.endsWith(ext) ? fn.slice(0, -ext.length) : fn
})

const filenameParts = computed(() => {
  const fn = baseFilename.value
  const parts: Array<{ text: string; tag: boolean }> = []
  const re = /\{\{.+?\}\}/g
  let last = 0; let m
  while ((m = re.exec(fn)) !== null) {
    if (m.index > last) parts.push({ text: fn.slice(last, m.index), tag: false })
    parts.push({ text: m[0], tag: true })
    last = m.index + m[0].length
  }
  if (last < fn.length) parts.push({ text: fn.slice(last), tag: false })
  return parts
})

function insertTag(tag: string) {
  if (fileOutputConfig.value) fileOutputConfig.value.filename = baseFilename.value + tag + fileExtension.value
}

function commitPlainText() {
  const v = plainText.value.trim()
  if (!v) return
  if (fileOutputConfig.value) fileOutputConfig.value.filename = baseFilename.value + v + fileExtension.value
  plainText.value = ''
}

function removeTagPart(idx: number) {
  const parts = filenameParts.value
  const removed = parts[idx].text
  if (fileOutputConfig.value) fileOutputConfig.value.filename = baseFilename.value.replace(removed, '') + fileExtension.value
}

function clearFilename() {
  if (fileOutputConfig.value) fileOutputConfig.value.filename = fileExtension.value
  plainText.value = ''
}

function updateExcelConfig(partial: Partial<ExcelOutputConfig>) {
  const cfg = store.output!.config as ExcelOutputConfig
  Object.assign(cfg, partial)
}

function updateCsvConfig(patch: Partial<CsvOutputConfig>) {
  if (store.output) {
    store.setOutput({
      ...store.output,
      config: { ...store.output.config, ...patch } as CsvOutputConfig,
    })
  }
}

async function handleTemplateUpload({ file, onFinish, onError }: UploadCustomRequestOptions) {
  if (!file.file) return
  const meta = await uploadTemplate(file.file)
  if (meta) {
    store.addFileRef(meta.fileId, meta)
    const excelCfg = store.output!.config as ExcelOutputConfig
    excelCfg.template = meta.fileId

    const preview = await fetchPreview(meta.fileId)
    if (preview) {
      templateSheets.value = preview.sheets || []
      if (preview.sheets?.length) excelCfg.sheet = preview.sheets[0]
      // Auto-fill columns
      const sourceCols: string[] = []
      for (const input of store.inputs) {
        if (input.fileId) {
          const src = await fetchPreview(input.fileId)
          if (src) sourceCols.push(...src.columns)
        }
      }
      if (preview.columns?.length) {
        excelCfg.columns = preview.columns.map(col => ({
          source: sourceCols.includes(col) ? col : '',
          target: col
        }))
      } else if (sourceCols.length) {
        excelCfg.columns = sourceCols.map(col => ({ source: col, target: col }))
        message.info('这个sheet页没有找到表头信息，将直接用数据源字段作为表头，你可以修改或删除列')
      }
    }
    emit('template-uploaded')
    onFinish()
  } else {
    onError()
  }
}

defineExpose({ templateUploadRef, templateSheets })
</script>
