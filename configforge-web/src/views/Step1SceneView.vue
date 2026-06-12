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
      <h2 class="text-lg font-semibold mb-1">场景信息</h2>
      <p class="text-sm text-slate-500">填写场景的基本信息，名称用于标识流水线配置，版本和描述便于后续管理。</p>
    </div>

    <SceneInfoForm />

    <div class="flex justify-between items-center pt-6">
      <NButton text @click="router.push('/')">取消</NButton>
      <NButton type="primary" :disabled="!store.canProceed(1)" @click="onNext">下一步</NButton>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import { NSteps, NStep, NButton } from 'naive-ui'
import SceneInfoForm from '../components/step1/SceneInfoForm.vue'

const router = useRouter()
const store = useWizardStore()

onMounted(() => { store.currentStep = 1 })

function onStepClick(step: number) {
  const s = step
  if (s <= store.currentStep) {
    store.goToStep(s); router.push(`/step/${s}`)
  } else if (s === store.currentStep + 1 && store.canProceed(store.currentStep)) {
    store.goToStep(s); router.push(`/step/${s}`)
  }
}

async function onNext() {
  if (store.canProceed(store.currentStep)) { store.nextStep(); await nextTick(); router.push('/step/2') }
}
</script>
