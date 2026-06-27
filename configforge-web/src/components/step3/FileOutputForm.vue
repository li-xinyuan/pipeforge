<template>
  <!--
    FileOutputForm — csv/excel 输出配置表单（限制①第二阶段迁移）。

    迁移策略：
    - Excel 模板上传 + sheet 选择器：保留为自定义 UI（含副作用：上传后自动填充
      columns、sheet 变更触发列重映射），不迁入 SchemaForm。
    - 其余字段（csv: delimiter/encoding/outputDir/filename；excel: outputDir/filename）
      迁入 SchemaForm，filename 通过 filename-template 命名 widget 渲染。
  -->
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
        :options="templateSheets.map(s => ({ label: s, value: s }))"
        placeholder="选择 Sheet"
        size="small"
        @update:value="(v: string) => { updateExcelConfig({ sheet: v }); $emit('sheet-change', v) }"
      />
      <NInput
        v-else
        :value="excelConfig.sheet"
        :disabled="!excelConfig.template"
        placeholder="Sheet1"
        size="small"
        @update:value="v => updateExcelConfig({ sheet: v })"
      />
    </div>
  </template>

  <!-- CSV/Excel 输出字段 — SchemaForm 驱动（限制①第二阶段迁移） -->
  <SchemaForm
    v-if="store.output?.plugin === 'csv' && csvOutputSchema"
    :model-value="store.output.config as unknown as Record<string, unknown>"
    :schema="csvOutputSchema"
    :skip-fields="['columns', 'sourceTable']"
    :widget-props="{ 'filename-template': { extension: '.csv' } }"
    @update:model-value="onSchemaUpdate"
  />
  <SchemaForm
    v-else-if="store.output?.plugin === 'excel' && excelOutputSchema"
    :model-value="store.output.config as unknown as Record<string, unknown>"
    :schema="excelOutputSchema"
    :skip-fields="['columns', 'sourceTable', 'template', 'sheet']"
    :widget-props="{ 'filename-template': { extension: '.xlsx' } }"
    @update:model-value="onSchemaUpdate"
  />
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { useFileUpload } from '../../composables/useFileUpload'
import { useWizardApi } from '../../composables/useWizardApi'
import type { ExcelOutputConfig } from '../../types/wizard'
import type { UploadCustomRequestOptions } from 'naive-ui'
import { NInput, NButton, NTag, NUpload, NSelect, useMessage } from 'naive-ui'
import SchemaForm from '../common/SchemaForm.vue'
import FilenameTemplate from '../common/FilenameTemplate.vue'
import { usePluginSchema } from '../../composables/usePluginSchema'
import { registerWidget, registerAsyncOptionsLoader } from '../../composables/widgetRegistry'
import { ENCODING_OPTIONS } from '../../constants/encodings'

const store = useWizardStore()
const message = useMessage()
const { fetchPreview } = useWizardApi()
const { uploading: templateUploading, error: templateUploadError, upload: uploadTemplate } = useFileUpload()

const templateUploadRef = ref<InstanceType<typeof NUpload>>()
const templateSheets = ref<string[]>([])

const emit = defineEmits<{
  'remove-template': []
  'sheet-change': [sheet: string]
  'template-uploaded': []
}>()

const excelConfig = computed(() => store.output!.config as ExcelOutputConfig)

// 限制①：csv/excel output 用 SchemaForm 渲染，schema 从后端获取
const { getSchema, load } = usePluginSchema()
const csvOutputSchema = computed(() => getSchema('csv', 'output'))
const excelOutputSchema = computed(() => getSchema('excel', 'output'))

// 注册编码选项 loader（csv output 的 encoding 字段引用）
registerAsyncOptionsLoader('encodings', () => Promise.resolve(ENCODING_OPTIONS))
// 注册 filename-template 命名 widget（csv/excel output 的 filename 字段引用）
registerWidget('filename-template', FilenameTemplate)

onMounted(() => {
  load()
})

/** SchemaForm update:modelValue 回调：可变更新，保留 config 对象引用。 */
function onSchemaUpdate(updated: Record<string, unknown>): void {
  Object.assign(store.output!.config, updated)
}

function updateExcelConfig(partial: Partial<ExcelOutputConfig>): void {
  Object.assign(store.output!.config, partial)
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
