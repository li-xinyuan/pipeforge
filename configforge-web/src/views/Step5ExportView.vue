<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <NSteps :current="store.currentStep" @update:current="onStepClick">
      <NStep title="场景信息" description="基本信息" />
      <NStep title="数据源配置" description="上传与解析" />
      <NStep title="数据转换/处理" description="SQL 编写" />
      <NStep title="输出定义" description="格式与映射" />
      <NStep title="预览与导出" description="YAML 查看" />
    </NSteps>

    <div class="mb-6 mt-8">
      <h2 class="text-lg font-semibold mb-1">预览与导出</h2>
      <p class="text-sm text-slate-500">预览生成的 pipeline.yaml 配置，确认无误后可复制或下载，也可返回前面步骤继续修改。</p>
    </div>

    <NCard>
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-base font-semibold">pipeline.yaml</h2>
        <div class="flex gap-2">
          <NButton size="small" :loading="aiLoading" @click="autoUpdateSceneDesc">自动更新场景描述</NButton>
          <NButton size="small" :loading="yamlLoading" @click="refreshPreview">刷新预览</NButton>
        </div>
      </div>
      <YamlPreview ref="yamlRef" />
    </NCard>

    <!-- 数据预览 -->
    <NCard class="mt-4">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-base font-semibold">数据预览</h2>
        <NButton size="small" type="info" :loading="dryRunLoading" @click="runDryRun">运行预览</NButton>
      </div>
      <p v-if="dryRunError" class="text-xs text-red-500 mb-2">{{ dryRunError }}</p>
      <div v-if="store.dryRunResults && store.dryRunResults.length > 0" class="space-y-4">
        <div v-for="table in store.dryRunResults" :key="table.table_name" class="border border-slate-200 dark:border-slate-700 rounded p-3">
          <div class="flex items-center gap-2 mb-2">
            <NTag size="tiny" :bordered="false" type="info">{{ table.table_name }}</NTag>
            <span class="text-xs text-slate-400">{{ table.columns.length }} 列 / {{ table.total_rows }} 行</span>
          </div>
          <DataPreviewTable :columns="table.columns" :rows="table.rows" :table-name="table.table_name" />
        </div>
      </div>
      <div v-else-if="!dryRunLoading" class="text-center py-6 text-slate-400 text-sm">
        点击「运行预览」查看数据处理结果
      </div>
    </NCard>

    <div v-if="descUpdated" class="mt-4 px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800 flex items-start gap-2">
      <span class="text-green-500 mt-0.5">✓</span>
      <span>场景描述已更新：<span class="font-medium">{{ descUpdated }}</span></span>
      <NButton text size="tiny" class="ml-auto" @click="descUpdated = ''">关闭</NButton>
    </div>

    <ExportActions />

    <div class="mt-4 flex items-center gap-3">
      <NButton type="success" :loading="saving" @click="onSaveConfig">保存配置</NButton>
      <span v-if="saveMsg" :class="['text-xs', saveError ? 'text-red-500' : 'text-green-600']">{{ saveMsg }}</span>
    </div>

    <div class="flex justify-between items-center pt-6 mt-6">
      <NButton text @click="store.prevStep(); router.push('/step/4')">上一步</NButton>
      <NButton type="primary" @click="router.push('/')">完成</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import { NSteps, NStep, NButton, NCard, NTag } from 'naive-ui'
import YamlPreview from '../components/step4/YamlPreview.vue'
import ExportActions from '../components/step4/ExportActions.vue'
import DataPreviewTable from '../components/step4/DataPreviewTable.vue'
import { useAiApi, useWizardApi } from '../composables/useWizardApi'
import { useConfigApi } from '../composables/useConfigApi'
import { stateToSnakeCase } from '../utils/serialization'

const router = useRouter()
const store = useWizardStore()
const yamlRef = ref<InstanceType<typeof YamlPreview>>()
const { askSuggestion } = useAiApi()
const { dryRun: dryRunApi, error: wizardApiError } = useWizardApi()
const { saveConfig, error: apiError } = useConfigApi()
const aiLoading = ref(false)
const yamlLoading = ref(false)
const dryRunLoading = ref(false)
const dryRunError = ref('')
const descUpdated = ref('')
const saving = ref(false)
const saveMsg = ref('')
const saveError = ref(false)
let descTimer: ReturnType<typeof setTimeout> | null = null
let saveMsgTimer: ReturnType<typeof setTimeout> | null = null

onMounted(() => { store.currentStep = 5 })

onUnmounted(() => {
  if (descTimer) clearTimeout(descTimer)
  if (saveMsgTimer) clearTimeout(saveMsgTimer)
})

function onStepClick(step: number) {
  const s = step
  if (s <= store.currentStep) {
    store.goToStep(s); router.push(`/step/${s}`)
  }
}

async function autoUpdateSceneDesc() {
  aiLoading.value = true
  try {
    const inputSummary = store.inputs.map(i => ({
      table: i.table,
      plugin: i.plugin,
      file: store.uploadedFiles[i.fileId]?.originalName || '',
    }))
    const outputConfig = store.output?.config as any
    const context = {
      inputs: inputSummary,
      sql: store.processors[0]?.plugin === 'sql' ? store.processors[0].sql : '',
      outputTables: store.processors[0]?.outputTables ?? [],
      output: {
        plugin: store.output?.plugin,
        filename: outputConfig?.filename || '',
        columns: (outputConfig?.columns || []).map((c: any) => ({ source: c.source, target: c.target })),
      },
    }
    const content = await askSuggestion('scene', context)
    if (content) {
      try {
        const parsed = JSON.parse(content)
        if (parsed.description) {
          store.scene.description = parsed.description
          descUpdated.value = parsed.description
          yamlRef.value?.loadYaml()
          if (descTimer) clearTimeout(descTimer)
          descTimer = setTimeout(() => { descUpdated.value = '' }, 6000)
        }
      } catch { /* ignore */ }
    }
  } finally {
    aiLoading.value = false
  }
}

async function refreshPreview() {
  yamlLoading.value = true
  try { await yamlRef.value?.loadYaml() }
  finally { yamlLoading.value = false }
}

async function runDryRun() {
  dryRunError.value = ''
  dryRunLoading.value = true
  try {
    const state = stateToSnakeCase(store.getWizardState())
    const result = await dryRunApi(state)
    if (result?.tables?.length) {
      store.setDryRunResults(result.tables)
    } else {
      const apiMsg = wizardApiError.value?.message || ''
      dryRunError.value = apiMsg ? `预览执行失败: ${apiMsg}` : '预览执行失败，请检查配置'
    }
  } finally {
    dryRunLoading.value = false
  }
}

async function onSaveConfig() {
  saving.value = true; saveMsg.value = ''; saveError.value = false
  const id = await saveConfig(store.$state)
  if (id) {
    store.setConfigId(id)
    saveMsg.value = '配置已保存'
    if (saveMsgTimer) clearTimeout(saveMsgTimer)
    saveMsgTimer = setTimeout(() => { saveMsg.value = '' }, 3000)
  } else {
    saveError.value = true
    saveMsg.value = '保存失败：' + (apiError.value?.message || '未知错误')
  }
  saving.value = false
}
</script>
