<template>
  <NModal :show="visible" preset="card" :title="'执行：' + (config?.sceneName || '')" style="max-width: 600px" :trap-focus="true" :auto-focus="true" @update:show="$emit('close')">
    <div class="exec-modal__body">
      <p class="exec-modal__hint">请为每个数据源上传对应的文件：</p>

      <div v-for="inp in config?.inputs" :key="inp.paramKey" class="exec-modal__input-row">
        <div class="exec-modal__input-header">
          <span class="exec-modal__input-name">{{ inp.name }}</span>
          <NTag :type="inp.plugin === 'csv' ? 'info' : 'success'" size="tiny">
            {{ inp.plugin === 'csv' ? 'CSV' : 'Excel' }}
          </NTag>
        </div>

        <template v-if="fileStates[inp.paramKey]?.fileId">
          <div class="exec-modal__file-row">
            <NTag type="success" size="small" class="exec-modal__file-tag">
              {{ fileStates[inp.paramKey]?.originalName }}
            </NTag>
            <NButton text size="tiny" type="error" @click="removeFile(inp.paramKey)">移除</NButton>
            <NButton text size="tiny" :loading="fileStates[inp.paramKey]?.previewLoading" @click="loadPreview(inp.paramKey)">预览</NButton>
          </div>
        </template>
        <NUpload
          v-else
          :custom-request="(opts) => onUpload(inp.paramKey, opts)"
          :show-file-list="false"
          :accept="inp.plugin === 'csv' ? '.csv' : '.xlsx,.xls'"
        >
          <NButton size="small" dashed :loading="fileStates[inp.paramKey]?.uploading">上传文件</NButton>
        </NUpload>
        <p v-if="fileStates[inp.paramKey]?.uploadError" class="exec-modal__error">{{ fileStates[inp.paramKey]?.uploadError }}</p>

        <div v-if="fileStates[inp.paramKey]?.previewData" class="exec-modal__preview">
          <table class="exec-modal__table">
            <thead>
              <tr>
                <th v-for="col in fileStates[inp.paramKey]?.previewData?.columns" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in fileStates[inp.paramKey]?.previewData?.rows" :key="ri">
                <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="exec-modal__footer">
        <div v-if="execError" class="exec-modal__error-section">
          <!-- Show AI diagnosis first (user-friendly) -->
          <DiagnosisPanel
            v-if="execDiagnosis"
            :diagnosis="execDiagnosis"
            :autofix-loading="autofixLoading"
            :autofix-result="autofixResult"
            :raw-error="execError"
            :rewrite-loading="rewriteLoading"
            @goto-step="onGotoStep"
            @autofix="onAutofix"
            @apply-fixes="onApplyFixes"
            @ai-rewrite="onAiRewrite"
          />
          <!-- Fallback: show raw error only when no AI diagnosis -->
          <p v-else class="exec-modal__error">{{ execError }}</p>
        </div>
        <div class="exec-modal__footer-actions">
          <NButton @click="$emit('close')">取消</NButton>
          <NButton type="success" :loading="executing" :disabled="!allReady" @click="onExecute">执行并下载</NButton>
        </div>
      </div>
    </template>
  </NModal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { SavedConfig } from '../types/wizard'
import { useFileUpload } from '../composables/useFileUpload'
import { useWizardApi } from '../composables/useWizardApi'
import { useConfigApi } from '../composables/useConfigApi'
import { useAiApi } from '../composables/useAiApi'
import { NModal, NButton, NTag, NUpload } from 'naive-ui'
import DiagnosisPanel from './common/DiagnosisPanel.vue'

const props = defineProps<{ visible: boolean; config: SavedConfig | null }>()
const emit = defineEmits<{ close: []; gotoStep: [step: number, fixes?: { step: number; field: string; old: string; new: string; reason: string }[]] }>()

const { upload: uploadFile } = useFileUpload()
const { fetchPreview } = useWizardApi()
const { executeConfig } = useConfigApi()
const { askSuggestion } = useAiApi()

interface FileState {
  fileId: string | null
  originalName: string | null
  previewData: { columns: string[]; rows: string[][] } | null
  uploading: boolean
  uploadError: string | null
  previewLoading: boolean
}

const fileStates = ref<Record<string, FileState>>({})
const executing = ref(false)
const execError = ref('')
const execDiagnosis = ref<{ cause: string; suggestions: string[]; severity: 'error' | 'warning'; step?: number } | null>(null)
const autofixLoading = ref(false)
const autofixResult = ref<{ fixable: boolean; fixes?: { step: number; field: string; old: string; new: string; reason: string }[]; suggestions?: string[] } | null>(null)
const rewriteLoading = ref(false)

function initState() {
  if (!props.config) return
  const states: Record<string, FileState> = {}
  for (const inp of props.config.inputs) {
    states[inp.paramKey] = {
      fileId: null, originalName: null,
      previewData: null, uploading: false,
      uploadError: null, previewLoading: false,
    }
  }
  fileStates.value = states
}

watch(() => props.config, initState, { immediate: true })

const allReady = computed(() => {
  if (!props.config) return false
  return props.config.inputs.every(inp => !!fileStates.value[inp.paramKey]?.fileId)
})

async function onUpload(paramKey: string, { file, onFinish, onError }: { file: { file: File | null }; onFinish: () => void; onError: (msg?: string) => void }) {
  if (!file.file) return
  const st = fileStates.value[paramKey]
  if (!st) return
  st.uploading = true; st.uploadError = null
  const meta = await uploadFile(file.file)
  if (meta) {
    st.fileId = meta.fileId
    st.originalName = meta.originalName
    onFinish()
  } else {
    st.uploadError = '上传失败'
    onError()
  }
  st.uploading = false
}

function removeFile(paramKey: string) {
  fileStates.value[paramKey] = {
    fileId: null, originalName: null,
    previewData: null, uploading: false,
    uploadError: null, previewLoading: false,
  }
}

async function loadPreview(paramKey: string) {
  const st = fileStates.value[paramKey]
  if (!st?.fileId) return
  st.previewLoading = true
  const data = await fetchPreview(st.fileId)
  if (data) {
    st.previewData = { columns: data.columns, rows: data.rows.slice(0, 5) }
  }
  st.previewLoading = false
}

async function onExecute() {
  if (!props.config || !allReady.value) return
  executing.value = true; execError.value = ''; execDiagnosis.value = null
  const files: Record<string, string> = {}
  for (const inp of props.config.inputs) {
    const st = fileStates.value[inp.paramKey]
    if (st?.fileId) files[inp.paramKey] = st.fileId
  }
  try {
    const blob = await executeConfig(props.config.id, files)
    if (blob) {
      const url = URL.createObjectURL(blob)
      try {
        const a = document.createElement('a')
        a.href = url
        a.download = `output_${props.config.id}`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      } finally {
        URL.revokeObjectURL(url)
      }
    }
  } catch (err: any) {
    execError.value = err?.message || '执行失败'
    execDiagnosis.value = err?.diagnosis || null
  }
  executing.value = false
}

function onGotoStep(step: number) {
  emit('gotoStep', step)
  emit('close')
}

async function onAutofix() {
  if (!execDiagnosis.value) return
  autofixLoading.value = true
  autofixResult.value = null
  try {
    const result = await askSuggestion('autofix', {
      diagnosis: JSON.stringify(execDiagnosis.value),
      errorLog: execError.value,
    })
    if (result) {
      try {
        autofixResult.value = JSON.parse(result)
      } catch {
        autofixResult.value = { fixable: false, suggestions: ['AI 返回了无法解析的结果'] }
      }
    } else {
      autofixResult.value = { fixable: false, suggestions: ['AI 未返回修复建议'] }
    }
  } catch {
    autofixResult.value = { fixable: false, suggestions: ['AI 修复请求失败'] }
  } finally {
    autofixLoading.value = false
  }
}

function onApplyFixes(fixes: { step: number; field: string; old: string; new: string; reason: string }[]) {
  if (fixes.length > 0) {
    emit('gotoStep', fixes[0].step, fixes)
  }
  emit('close')
}

async function onAiRewrite() {
  if (!execDiagnosis.value || !props.config) return
  rewriteLoading.value = true
  try {
    const result = await askSuggestion('orchestrate', {
      currentStep: 3,
      naturalLanguage: `修复执行错误：${execDiagnosis.value.cause}。错误信息：${execError.value}`,
      inputs: props.config.inputs?.map(i => ({ name: i.name, plugin: i.plugin })),
      processors: [{ plugin: 'sql', name: 'query' }],
      outputColumns: [],
    })
    if (result) {
      // Navigate to wizard with the rewrite result
      emit('gotoStep', 3)
    }
  } catch {
    // AI rewrite failed, user can still manually fix
  } finally {
    rewriteLoading.value = false
  }
}
</script>

<style scoped>
.exec-modal__body {
  max-height: 60vh;
  overflow-y: auto;
}

.exec-modal__hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin: 0 0 12px;
}

.exec-modal__input-row {
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 12px;
  margin-bottom: 12px;
}

.exec-modal__input-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.exec-modal__input-name {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
}

.exec-modal__file-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.exec-modal__file-tag {
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.exec-modal__error {
  font-size: var(--font-size-xs);
  color: var(--color-error);
  margin-top: 4px;
}

.exec-modal__error-section {
  flex: 1;
  min-width: 0;
}

.exec-modal__preview {
  margin-top: 8px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.exec-modal__table {
  width: 100%;
  font-size: var(--font-size-xs);
  border-collapse: collapse;
}

.exec-modal__table thead {
  background: var(--color-surface-hover);
}

.exec-modal__table th {
  padding: 4px 8px;
  text-align: left;
  font-weight: 500;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border-light);
}

.exec-modal__table td {
  padding: 4px 8px;
  color: var(--color-text-muted);
  border-bottom: 1px solid var(--color-border-light);
}

.exec-modal__table tbody tr:hover {
  background: var(--color-surface-hover);
}

.exec-modal__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.exec-modal__footer-actions {
  display: flex;
  gap: 12px;
  margin-left: auto;
}
</style>
