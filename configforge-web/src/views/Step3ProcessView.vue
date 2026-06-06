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
      <h2 class="text-lg font-semibold mb-1">数据转换/处理</h2>
      <p class="text-sm text-slate-500">编写 SQL 对第二步导入的数据源进行处理，例如多表关联、字段计算、数据过滤等。</p>
    </div>

    <NCard>
      <SqlEditorTab />
    </NCard>

    <div class="flex justify-between items-center pt-6 mt-6">
      <NButton text @click="router.push('/step/2')">上一步</NButton>
      <NButton type="primary" :disabled="!store.canProceed" @click="onNext">下一步</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import { NSteps, NStep, NButton, NCard } from 'naive-ui'
import SqlEditorTab from '../components/step3/SqlEditorTab.vue'

const router = useRouter()
const store = useWizardStore()

onMounted(() => {
  store.currentStep = 3

  const firstProc = store.processors[0]
  if (firstProc && firstProc.plugin === 'sql' && !firstProc.sql.trim() && store.inputs.length > 0) {
    const firstTable = store.inputs[0]?.table
    if (firstTable) firstProc.sql = `SELECT * FROM ${firstTable}`
  }
})

function onStepClick(step: number) {
  const s = step
  if (s <= store.currentStep) {
    store.goToStep(s); router.push(`/step/${s}`)
  } else if (s === store.currentStep + 1 && store.canProceed) {
    store.goToStep(s); router.push(`/step/${s}`)
  }
}

function onNext() {
  if (store.canProceed) {
    store.nextStep()
    router.push('/step/4')
  }
}
</script>
