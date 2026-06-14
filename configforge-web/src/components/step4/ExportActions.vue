<template>
  <ConfettiBurst ref="confettiRef" />
  <div class="flex gap-2">
    <NButton @click="copyYaml">复制</NButton>
    <NButton @click="downloadYaml">下载 YAML</NButton>
    <NButton type="primary" class="btn-primary" :loading="executing" @click="downloadResult">下载结果文件</NButton>
    <NButton :loading="saving" @click="saveConfigHandler">保存配置</NButton>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, useMessage, useDialog } from 'naive-ui'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi } from '../../composables/useWizardApi'
import { useConfigApi } from '../../composables/useConfigApi'
import ConfettiBurst from '../ConfettiBurst.vue'

const props = defineProps<{ yaml?: string }>()
const message = useMessage()
const dialog = useDialog()
const router = useRouter()
const store = useWizardStore()
const { executePipeline, error: apiError } = useWizardApi()
const { saveConfig } = useConfigApi()
const executing = ref(false)
const saving = ref(false)
const confettiRef = ref<InstanceType<typeof ConfettiBurst>>()

function buildExecutionFilename(storedFilename: string): string {
  const now = new Date()
  const ts = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
  const ext = storedFilename.includes('.') ? storedFilename.split('.').pop()! : 'xlsx'
  const base = safeSceneName()
  return `${base}_${ts}.${ext}`
}

function safeSceneName(): string {
  return store.scene.name.replace(/[\/\\:*?"<>|]/g, '-').trim() || 'output'
}

async function copyYaml() {
  if (!props.yaml) return
  await navigator.clipboard.writeText(props.yaml)
  message.success('已复制到剪贴板')
}

function downloadYaml() {
  if (!props.yaml) return
  const blob = new Blob([props.yaml], { type: 'text/yaml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const name = store.scene.name.trim() || 'pipeline'
  a.href = url; a.download = `${name}_pipeline.yaml`; a.click()
  URL.revokeObjectURL(url)
}

async function downloadResult() {
  // Check if any file-based input source is missing its uploaded file
  const missingFileInputs = store.inputs.filter(
    inp => inp.plugin !== 'database' && !inp.fileId
  )
  if (missingFileInputs.length > 0) {
    const names = missingFileInputs.map(inp => inp.table || inp.paramKey).join('、')
    dialog.warning({
      title: '文件需要重新上传',
      content: `以下输入源的文件未上传（编辑已保存的配置时，上传文件不会保留）：${names}。请返回第 2 步重新上传文件后再执行。`,
      positiveText: '知道了',
    })
    return
  }

  executing.value = true
  try {
    const state = store.getWizardState()
    const result = await executePipeline(state)
    if (result) {
      if (result instanceof Blob) {
        const url = URL.createObjectURL(result)
        const a = document.createElement('a')
        const storedFilename = (store.output?.config as any)?.filename || 'output.xlsx'
        a.href = url; a.download = buildExecutionFilename(storedFilename); a.click()
        URL.revokeObjectURL(url)
        confettiRef.value?.burst()
        message.success('结果文件下载成功')
      } else {
        // Database output: JSON response with success message
        confettiRef.value?.burst()
        message.success(result.message || '执行成功')
      }
    } else {
      message.error(apiError.value?.message || '执行失败，请检查配置')
    }
  } finally {
    executing.value = false
  }
}

async function saveConfigHandler() {
  saving.value = true
  try {
    const state = store.getWizardState()
    const id = await saveConfig(state, store.configId)
    if (id) {
      store.setConfigId(id)
      dialog.success({
        title: '保存成功',
        content: '配置已保存。是否跳转到首页？',
        positiveText: '去首页',
        negativeText: '留在当前页',
        onPositiveClick: () => { router.push('/') },
      })
    } else {
      message.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}
</script>
