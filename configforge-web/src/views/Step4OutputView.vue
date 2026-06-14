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
      <h2 class="text-lg font-semibold mb-1">输出定义</h2>
      <p class="text-sm text-slate-500">上传 Excel 模板文件并定义输出列映射，模板首行列名会自动填充，同名列自动匹配数据源。</p>
    </div>

    <NCard>
      <OutputConfigTab />
    </NCard>

    <div class="mt-4 pt-4">
      <NButton type="success" :loading="executing" @click="testRunConfirmVisible = true">试运行并下载</NButton>
      <p v-if="executeError" class="text-xs text-red-500 mt-1">{{ executeError }}</p>
    </div>

    <!-- 试运行确认弹窗 -->
    <NModal v-model:show="testRunConfirmVisible" preset="card" title="确认试运行" style="max-width: 400px">
      <p class="text-sm text-slate-600 mb-0">将使用当前配置执行流水线并下载输出文件。确认继续？</p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <NButton @click="testRunConfirmVisible = false">取消</NButton>
          <NButton type="success" @click="testRunConfirmVisible = false; onTestRun()">确认执行</NButton>
        </div>
      </template>
    </NModal>

    <div class="flex justify-between items-center pt-6 mt-6">
      <NButton text @click="router.push('/step/3')">上一步</NButton>
      <NButton type="primary" :disabled="!store.canProceed" @click="onNext">下一步</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import { NSteps, NStep, NButton, NCard, NModal } from 'naive-ui'
import OutputConfigTab from '../components/step3/OutputConfigTab.vue'
import { useWizardApi } from '../composables/useWizardApi'

const router = useRouter()
const store = useWizardStore()
const { executePipeline, error: apiError } = useWizardApi()
const executing = ref(false)
const executeError = ref('')
const testRunConfirmVisible = ref(false)

onMounted(() => { store.currentStep = 4 })

function onStepClick(step: number) {
  const s = step
  if (s <= store.currentStep) {
    store.goToStep(s); router.push(`/step/${s}`)
  } else if (s === store.currentStep + 1 && store.canProceed(store.currentStep)) {
    store.goToStep(s); router.push(`/step/${s}`)
  }
}

async function onTestRun() {
  executing.value = true
  executeError.value = ''
  try {
    const outCfg = store.output?.config as any
    const state = {
      current_step: store.currentStep,
      scene: { name: store.scene.name, description: store.scene.description, version: store.scene.version },
      inputs: store.inputs.map(inp => ({
        name: inp.table,
        plugin: inp.plugin,
        table: inp.table,
        param_key: inp.paramKey,
        file_id: inp.fileId,
        config: inp.config,
      })),
      processors: store.processors.map(p => ({
        plugin: p.plugin,
        sql: p.plugin === 'sql' ? p.sql : '',
        script: p.plugin === 'python' ? p.script : '',
        output_tables: p.outputTables,
      })),
      output: store.output ? {
        plugin: store.output.plugin,
        config: {
          ...outCfg,
          source_table: outCfg.sourceTable,
          output_dir: outCfg.outputDir || './output/',
          columns: (outCfg.columns || []).map((c: any) => ({ source: c.source, target: c.target })),
        },
      } : null,
      uploaded_files: {},
    }
    const result = await executePipeline(state)
    if (result && result instanceof Blob) {
      const url = URL.createObjectURL(result)
      try {
        const a = document.createElement('a')
        a.href = url
        a.download = outCfg?.filename || 'output.xlsx'
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      } finally {
        URL.revokeObjectURL(url)
      }
    } else if (apiError.value) {
      executeError.value = apiError.value.message
    }
  } catch (e: any) {
    executeError.value = e?.message || '执行失败'
  } finally {
    executing.value = false
  }
}

function onNext() {
  if (store.canProceed(store.currentStep)) {
    store.nextStep()
    router.push('/step/5')
  }
}
</script>
