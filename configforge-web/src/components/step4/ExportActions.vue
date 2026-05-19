<template>
  <div class="flex gap-2 mt-4">
    <NButton size="small" @click="copyYaml">复制</NButton>
    <NButton size="small" type="primary" @click="downloadYaml">下载 YAML</NButton>
    <NButton size="small" type="primary" :loading="executing" @click="downloadResult">下载结果文件</NButton>
    <NButton size="small" type="primary" :loading="saving" @click="saveConfigHandler">保存配置</NButton>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, useMessage, useDialog } from 'naive-ui'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi } from '../../composables/useWizardApi'
import { useConfigApi } from '../../composables/useConfigApi'

const props = defineProps<{ yaml?: string }>()
const message = useMessage()
const dialog = useDialog()
const router = useRouter()
const store = useWizardStore()
const { executePipeline, error: apiError } = useWizardApi()
const { saveConfig } = useConfigApi()
const executing = ref(false)
const saving = ref(false)

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
  executing.value = true
  try {
    const state = {
      scene: {
        name: store.scene.name,
        description: store.scene.description,
        version: store.scene.version,
      },
      inputs: store.inputs.map(inp => ({
        name: inp.table,
        plugin: inp.plugin,
        table: inp.table,
        param_key: inp.paramKey,
        file_id: inp.fileId,
        config: inp.config.type === 'csv'
          ? { type: 'csv', delimiter: (inp.config as any).delimiter, encoding: (inp.config as any).encoding, has_header: (inp.config as any).hasHeader }
          : { type: inp.config.type, sheet: (inp.config as any).sheet },
      })),
      processor: {
        plugin: store.processor.plugin,
        sql: store.processor.sql,
        output_tables: [store.processor.outputTable],
      },
      output: store.output ? {
        plugin: store.output.plugin,
        config: store.output.config.type === 'csv'
          ? {
              type: 'csv',
              source_table: (store.output.config as any).sourceTable,
              output_dir: (store.output.config as any).outputDir,
              filename: (store.output.config as any).filename,
              delimiter: (store.output.config as any).delimiter,
              encoding: (store.output.config as any).encoding,
              columns: store.output.config.columns.map((c: any) => ({ source: c.source, target: c.target })),
            }
          : {
              type: store.output.config.type,
              template: (store.output.config as any).template,
              sheet: (store.output.config as any).sheet,
              output_dir: (store.output.config as any).outputDir,
              source_table: (store.output.config as any).sourceTable,
              filename: (store.output.config as any).filename,
              columns: store.output.config.columns.map((c: any) => ({ source: c.source, target: c.target })),
            },
      } : null,
    }

    const blob = await executePipeline(state)
    if (blob) {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      const storedFilename = (store.output?.config as any)?.filename || 'output.xlsx'
      a.href = url; a.download = buildExecutionFilename(storedFilename); a.click()
      URL.revokeObjectURL(url)
      message.success('结果文件下载成功')
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
    const state = {
      currentStep: 5,
      scene: {
        name: store.scene.name,
        description: store.scene.description,
        version: store.scene.version,
      },
      inputs: store.inputs.map(inp => ({
        name: inp.table,
        plugin: inp.plugin,
        table: inp.table,
        paramKey: inp.paramKey,
        fileId: inp.fileId,
        config: inp.config,
      })),
      processor: {
        plugin: store.processor.plugin,
        sql: store.processor.sql,
        outputTable: store.processor.outputTable,
      },
      output: store.output,
    }
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
