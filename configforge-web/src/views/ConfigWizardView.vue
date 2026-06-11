<template>
  <div class="wizard">
    <!-- Top Nav -->
    <AppNavBar current-route="wizard" :badge="route.query.load ? '编辑配置' : '新配置'" />

    <!-- Main: steps area + Guide Panel -->
    <div class="wizard__main">
      <!-- Scrollable steps -->
      <div class="wizard__steps" ref="scrollEl">
        <WizardProgress :steps="progressSteps" @step-click="scrollToStep" />

        <!-- Step 1: Scene Info -->
        <WizardStepCard
          ref="step1El"
          title="场景信息"
          description="告诉 ConfigForge 你想做什么"
          icon="🎨"
          icon-bg="#f0fdfa"
          :status="stepStatus(1)"
          :badge="stepBadge(1)"
        >
          <div class="wizard__form-grid">
            <div class="wizard__form-group">
              <label class="wizard__label">场景名称 <span class="wizard__required">*</span></label>
              <NInput size="small" :class="{ 'pulse-cta-input': currentStep === 1 && !store.scene.name.trim() }" v-model:value="store.scene.name" placeholder="例如：销售报表生成" />
              <p v-if="currentStep === 1 && !store.scene.name.trim()" class="wizard__validation-msg">请输入场景名称</p>
            </div>
            <div class="wizard__form-group">
              <label class="wizard__label">版本号（可选）</label>
              <NInput size="small" v-model:value="store.scene.version" placeholder="1.0" />
            </div>
            <div class="wizard__form-group wizard__form-group--full">
              <label class="wizard__label">场景描述（可选）</label>
              <NInput
                type="textarea"
                size="small"
                v-model:value="store.scene.description"
                placeholder="描述这个配置管道的用途..."
                :rows="3"
              />
            </div>
          </div>
          <template #footer>
            <span :class="{ 'pulse-cta': currentStep === 1 && store.scene.name.trim() }" style="display:inline-block;border-radius:8px;"><NButton class="btn-primary" :disabled="!store.scene.name.trim()" @click="completeStep(1)">下一步</NButton></span>
          </template>
        </WizardStepCard>

        <!-- Step 2: Input Sources -->
        <WizardStepCard
          ref="step2El"
          title="输入源"
          description="添加数据文件作为管道的输入"
          icon="📂"
          icon-bg="#ccfbf1"
          :status="stepStatus(2)"
          :badge="stepBadge(2)"
        >
          <InputSourceList :pulse-cta="currentStep === 2" @file-ready="onFileReady" />
          <template #footer>
            <div style="display:flex;gap:10px;align-items:center">
              <NButton v-if="currentStep === 2" text size="small" @click="onGoBack(2)">← 返回上一步</NButton>
              <span :class="{ 'pulse-cta': currentStep === 2 && store.inputs.length > 0 && store.inputs.every(inp => inp.fileId) }" style="display:inline-block;border-radius:8px;"><NButton class="btn-primary" :disabled="store.inputs.length === 0 || !store.inputs.every(inp => inp.fileId)" @click="completeStep(2)">下一步</NButton></span>
            </div>
            <p v-if="currentStep === 2 && store.inputs.length === 0" class="wizard__validation-msg">至少需要添加 1 个输入源</p>
          </template>
        </WizardStepCard>

        <!-- Step 3: SQL Processing -->
        <WizardStepCard
          ref="step3El"
          title="处理步骤"
          description="对输入数据进行加工和转换"
          icon="⚡"
          icon-bg="#fef3c7"
          :status="stepStatus(3)"
          :badge="stepBadge(3)"
        >
          <SqlEditorTab ref="sqlEditorRef" :pulse-cta="currentStep === 3 && (store.processors.length === 0 || store.processors.some(p => (p.plugin === 'sql' ? !p.sql.trim() : !p.script.trim()) || !p.outputTables.length))" />
          <template #footer>
            <div style="display:flex;gap:10px;align-items:center">
              <NButton v-if="currentStep === 3" text size="small" @click="onGoBack(3)">← 返回上一步</NButton>
              <span :class="{ 'pulse-cta': currentStep === 3 && store.processors.length > 0 && store.processors.every(p => (p.plugin === 'sql' ? p.sql.trim() : p.script.trim()) && p.outputTables.length) }" style="display:inline-block;border-radius:8px;"><NButton class="btn-primary" :disabled="!store.processors.length || store.processors.some(p => (p.plugin === 'sql' ? !p.sql.trim() || !p.outputTables.length : !p.script.trim() || !p.outputTables.length))" @click="completeStep(3)">下一步</NButton></span>
            </div>
            <p v-if="currentStep === 3 && store.processors.some(p => (p.plugin === 'sql' ? !p.sql.trim() : !p.script.trim()) || !p.outputTables.length)" class="wizard__validation-msg">
              {{ store.processors.some(p => p.plugin === 'sql' ? !p.sql.trim() : !p.script.trim()) ? '请输入代码' : '请输入输出表名' }}
            </p>
          </template>
        </WizardStepCard>

        <!-- Step 4: Output Config -->
        <WizardStepCard
          ref="step4El"
          title="输出配置"
          description="配置输出格式和列映射"
          icon="📤"
          icon-bg="#fef2f2"
          :status="stepStatus(4)"
          :badge="stepBadge(4)"
        >
          <OutputConfigTab :pulse-cta="currentStep === 4" />
          <template #footer>
            <div style="display:flex;gap:10px;align-items:center">
              <NButton v-if="currentStep === 4" text size="small" @click="onGoBack(4)">← 返回上一步</NButton>
              <span :class="{ 'pulse-cta': currentStep === 4 && store.output?.config?.columns?.length }" style="display:inline-block;border-radius:8px;"><NButton class="btn-primary" :disabled="!store.output?.config?.columns?.length" @click="completeStep(4)">下一步</NButton></span>
            </div>
            <p v-if="currentStep === 4 && !store.output?.config?.columns?.length" class="wizard__validation-msg">请先配置列映射</p>
          </template>
        </WizardStepCard>

        <!-- Step 5: Preview & Export -->
        <WizardStepCard
          ref="step5El"
          title="预览与导出"
          description="查看 YAML 配置并导出"
          icon="🚀"
          icon-bg="#eff6ff"
          :status="stepStatus(5)"
          :badge="stepBadge(5)"
        >
          <YamlPreview ref="yamlPreviewRef" />
          <template #footer>
            <div style="display:flex;gap:10px;align-items:center">
              <NButton v-if="currentStep === 5" text size="small" @click="onGoBack(5)">← 返回上一步</NButton>
              <ExportActions :yaml="yamlPreviewRef?.yamlText || ''" />
            </div>
          </template>
        </WizardStepCard>

        <div class="wizard__bottom-spacer" />
      </div>

      <!-- Guide Panel (always visible) -->
      <GuidePanel :current-step="currentStep" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import { useConfigApi } from '../composables/useConfigApi'
import { useTheme } from '../composables/useTheme'
import { NButton, NInput } from 'naive-ui'
import WizardProgress from '../components/wizard/WizardProgress.vue'
import type { StepState } from '../components/wizard/WizardProgress.vue'
import WizardStepCard from '../components/wizard/WizardStepCard.vue'
import GuidePanel from '../components/wizard/GuidePanel.vue'
import InputSourceList from '../components/step2/InputSourceList.vue'
import SqlEditorTab from '../components/step3/SqlEditorTab.vue'
import OutputConfigTab from '../components/step3/OutputConfigTab.vue'
import YamlPreview from '../components/step4/YamlPreview.vue'
import ExportActions from '../components/step4/ExportActions.vue'
import AppNavBar from '../components/common/AppNavBar.vue'

const store = useWizardStore()
const theme = useTheme()
const route = useRoute()
const { loadConfigState } = useConfigApi()

// Local state
const currentStep = ref(1)
const scrollEl = ref<HTMLElement>()

// Step refs for scrolling
const step1El = ref<InstanceType<typeof WizardStepCard>>()
const step2El = ref<InstanceType<typeof WizardStepCard>>()
const step3El = ref<InstanceType<typeof WizardStepCard>>()
const step4El = ref<InstanceType<typeof WizardStepCard>>()
const step5El = ref<InstanceType<typeof WizardStepCard>>()
const sqlEditorRef = ref<InstanceType<typeof SqlEditorTab>>()
const yamlPreviewRef = ref<InstanceType<typeof YamlPreview>>()

const stepRefs = [step1El, step2El, step3El, step4El, step5El]

// Step status helpers
function stepStatus(n: number): 'completed' | 'active' | 'locked' {
  if (n < currentStep.value) return 'completed'
  if (n === currentStep.value) return 'active'
  return 'locked'
}

function stepBadge(n: number): string {
  if (n < currentStep.value) return '✓ 已完成'
  if (n === currentStep.value) return '⟳ 当前步骤'
  return '待解锁'
}

// Progress steps for WizardProgress
const progressSteps = ref<StepState[]>([
  { label: '场景信息', status: 'active' },
  { label: '输入源', status: 'locked' },
  { label: '处理步骤', status: 'locked' },
  { label: '输出配置', status: 'locked' },
  { label: '预览导出', status: 'locked' },
])

// Navigation
function completeStep(n: number) {
  if (n < 5) {
    currentStep.value = n + 1
    scrollToStep(n + 1)
    if (n === 2) {
      sqlEditorRef.value?.checkTableRenames()
    }
    if (n === 4) {
      nextTick(() => {
        yamlPreviewRef.value?.loadYaml()
      })
    }
  }
}

function scrollToStep(n: number) {
  if (n < 1 || n > 5) return
  manualScroll = true
  setTimeout(() => { manualScroll = false }, 1000)
  const el = stepRefs[n - 1]?.value
  if (el?.$el instanceof HTMLElement) {
    el.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

function onGoBack(fromStep: number) {
  const targetStep = fromStep - 1
  if (targetStep < 1) return

  // Only clear the step we're leaving, NOT downstream steps
  if (fromStep === 2) {
    store.inputs = []
    store.uploadedFiles = {}
  } else if (fromStep === 3) {
    store.processors = []
    store.output = null
  } else if (fromStep === 4) {
    store.output = null
  }
  // fromStep === 5: nothing to clear

  // Update local currentStep (this is the critical fix!)
  currentStep.value = targetStep
  scrollToStep(targetStep)
}

function onFileReady(_fileId: string) {
  // File upload handled by InputSourceList component
}

// ── Intersection Observer ──
let observer: IntersectionObserver | null = null
let manualScroll = false
let lastScrollY = 0
const enteredSteps = ref(new Set<number>())

function onPageScroll() {
  lastScrollY = window.scrollY
}

onMounted(async () => {
  theme.initTheme()

  const loadId = route.query.load as string | undefined
  if (loadId) {
    const state = await loadConfigState(loadId)
    if (state) {
      store.setConfigId(loadId)
      store.loadFromConfigState(state)
      currentStep.value = 5
      await nextTick()
    } else {
      store.resetAll()
    }
  } else {
    store.resetAll()
  }

  const prompt = route.query.prompt as string | undefined
  if (prompt) {
    store.scene.description = prompt
  }

  lastScrollY = window.scrollY
  window.addEventListener('scroll', onPageScroll, { passive: true })

  observer = new IntersectionObserver(
    (entries) => {
      if (manualScroll) return
      // Ignore callbacks triggered by content height changes, not actual scrolling
      if (Math.abs(window.scrollY - lastScrollY) < 5) return
      for (const entry of entries) {
        const stepNum = Number((entry.target as HTMLElement).dataset.step)
        if (!stepNum) continue
        if (entry.isIntersecting && entry.intersectionRatio >= 0.4) {
          currentStep.value = stepNum
          if (!enteredSteps.value.has(stepNum)) {
            enteredSteps.value = new Set([...enteredSteps.value, stepNum])
            ;(entry.target as HTMLElement).classList.add('wizard-step-card--entering')
            setTimeout(() => {
              ;(entry.target as HTMLElement).classList.remove('wizard-step-card--entering')
            }, 400)
          }
        }
      }
    },
    { threshold: [0.4] }
  )

  stepRefs.forEach((ref) => {
    const el = ref.value?.$el as HTMLElement | undefined
    if (el) {
      el.dataset.step = String(stepRefs.indexOf(ref) + 1)
      observer!.observe(el)
    }
  })
})

onUnmounted(() => {
  observer?.disconnect()
  window.removeEventListener('scroll', onPageScroll)
})
</script>

<style scoped>
.wizard {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--color-bg);
}

.wizard__main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* === Scrollable Steps === */
.wizard__steps {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px 0;
  background: linear-gradient(180deg, var(--color-bg) 0%, var(--color-bg-secondary) 100%);
  scroll-padding-top: 80px;
}

/* === Step 1 Form === */
.wizard__form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.wizard__form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.wizard__form-group--full {
  grid-column: 1 / -1;
}

.wizard__label {
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--color-text);
}

.wizard__required {
  color: var(--color-error);
}

/* === Validation message === */
.wizard__validation-msg {
  margin: 8px 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-error);
}

/* === Bottom Spacer === */
.wizard__bottom-spacer {
  height: 80px;
}

/* ─── Step card entrance animation ─── */
:deep(.wizard-step-card--entering) {
  animation: cf-slide-up 0.4s ease-out;
}

/* ─── Responsive: Tablet ─── */
@media (max-width: 1023px) {
  .wizard__steps {
    padding: 12px 14px 0;
  }
}

/* ─── Responsive: Mobile ─── */
@media (max-width: 767px) {
  .wizard__steps {
    padding: 8px 10px 0;
  }
  .wizard__form-grid {
    grid-template-columns: 1fr;
  }
  .wizard__bottom-spacer {
    height: 100px;
  }
}
</style>
