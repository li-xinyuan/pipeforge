<template>
  <div class="wizard">
    <AppNavBar current-route="wizard" :badge="route.query.load ? '编辑配置' : '新配置'" />

    <!-- Main: steps area + Guide panel -->
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
          :step="1"
        >
          <div class="wizard__form-grid">
            <div class="wizard__form-group">
              <label class="wizard__label">场景名称 <span class="wizard__required">*</span></label>
              <NInput :class="{ 'pulse-cta-input': currentStep === 1 && !store.canProceed(1) }" v-model:value="store.scene.name" placeholder="例如：销售报表生成" size="small" />
              <p v-if="currentStep === 1 && store.stepValidation(1).length" class="wizard__validation-msg">{{ store.stepValidation(1).join('；') }}</p>
            </div>
            <div class="wizard__form-group">
              <label class="wizard__label">版本号 (可选)</label>
              <NInput v-model:value="store.scene.version" placeholder="1.0" size="small" />
            </div>
            <div class="wizard__form-group wizard__form-group--full">
              <label class="wizard__label">场景描述 (可选)</label>
              <NInput
                v-model:value="store.scene.description"
                type="textarea"
                placeholder="描述这个配置管道的用途..."
                :rows="3"
                size="small"
              />
            </div>
          </div>
          <template #footer>
            <NButton :class="{ 'btn-primary': true, 'pulse-cta': currentStep === 1 && store.canProceed(1) }" :disabled="!store.canProceed(1)" @click="completeStep(1)">下一步 ↓</NButton>
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
          :step="2"
        >
          <InputSourceList :pulse-cta="currentStep === 2" />
          <template #footer>
            <NButton size="small" @click="onGoBack(2)">← 上一步</NButton>
            <NButton :class="{ 'btn-primary': true, 'pulse-cta': currentStep === 2 && store.canProceed(2) }" :disabled="!store.canProceed(2)" @click="completeStep(2)">下一步 ↓</NButton>
            <p v-if="currentStep === 2 && store.stepValidation(2).length" class="wizard__validation-msg">{{ store.stepValidation(2).join('；') }}</p>
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
          :step="3"
        >
          <SqlEditorTab ref="sqlEditorRef" :pulse-cta="currentStep === 3 && !store.canProceed(3)" />
          <template #footer>
            <NButton size="small" @click="onGoBack(3)">← 上一步</NButton>
            <NButton :class="{ 'btn-primary': true, 'pulse-cta': currentStep === 3 && store.canProceed(3) }" :disabled="!store.canProceed(3)" @click="completeStep(3)">下一步 ↓</NButton>
            <p v-if="currentStep === 3 && store.stepValidation(3).length" class="wizard__validation-msg">{{ store.stepValidation(3).join('；') }}</p>
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
          :step="4"
        >
          <OutputConfigTab :pulse-cta="currentStep === 4" />
          <template #footer>
            <NButton size="small" @click="onGoBack(4)">← 上一步</NButton>
            <NButton :class="{ 'btn-primary': true, 'pulse-cta': currentStep === 4 && store.canProceed(4) }" :disabled="!store.canProceed(4)" @click="completeStep(4)">下一步 ↓</NButton>
            <p v-if="currentStep === 4 && store.stepValidation(4).length" class="wizard__validation-msg">{{ store.stepValidation(4).join('；') }}</p>
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
          :step="5"
        >
          <div style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;">
            <div class="cf-stat-card">
              <div class="cf-stat-card__label">输入源</div>
              <div class="cf-stat-card__value">{{ store.inputs.length }}</div>
              <div class="cf-stat-card__sub">{{ inputTypeSummary }}</div>
            </div>
            <div class="cf-stat-card">
              <div class="cf-stat-card__label">处理步骤</div>
              <div class="cf-stat-card__value">{{ store.processors.length }}</div>
              <div class="cf-stat-card__sub">{{ processorTypeSummary }}</div>
            </div>
            <div class="cf-stat-card">
              <div class="cf-stat-card__label">输出格式</div>
              <div class="cf-stat-card__value">{{ outputTypeLabel }}</div>
            </div>
          </div>

          <!-- Data Preview -->
          <div style="margin-bottom: 16px;">
            <div class="flex items-center justify-between mb-2">
              <label class="cf-label" style="margin-bottom: 0;">数据预览</label>
              <NButton size="small" :loading="dryRunLoading" @click="runDryRun">运行预览</NButton>
            </div>
            <div v-if="dryRunError" class="text-xs text-red-500 mb-2">{{ dryRunError }}</div>
            <DataPreviewTable
              v-if="previewColumns.length > 0"
              :columns="previewColumns"
              :rows="previewRows"
            />
            <p v-else-if="!dryRunLoading" class="text-xs text-slate-400">点击"运行预览"查看数据处理结果</p>
          </div>

          <YamlPreview ref="yamlPreviewRef" />
          <template #footer>
            <NButton size="small" @click="onGoBack(5)">← 上一步</NButton>
            <ExportActions :yaml="yamlPreviewRef?.yamlText || ''" />
          </template>
        </WizardStepCard>

        <div class="wizard__bottom-spacer" />
      </div>

      <!-- Guide Panel (right side tips) -->
      <GuidePanel :current-step="currentStep" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import { useConfigApi } from '../composables/useConfigApi'
import { useWizardApi } from '../composables/useWizardApi'
import { stateToSnakeCase } from '../utils/serialization'
import { NButton, NInput } from 'naive-ui'
import AppNavBar from '../components/common/AppNavBar.vue'
import WizardProgress from '../components/wizard/WizardProgress.vue'
import type { StepState } from '../components/wizard/WizardProgress.vue'
import WizardStepCard from '../components/wizard/WizardStepCard.vue'
import GuidePanel from '../components/wizard/GuidePanel.vue'
import InputSourceList from '../components/step2/InputSourceList.vue'
import SqlEditorTab from '../components/step3/SqlEditorTab.vue'
import OutputConfigTab from '../components/step3/OutputConfigTab.vue'
import YamlPreview from '../components/step4/YamlPreview.vue'
import ExportActions from '../components/step4/ExportActions.vue'
import DataPreviewTable from '../components/step4/DataPreviewTable.vue'

const store = useWizardStore()
const route = useRoute()
const { loadConfigState } = useConfigApi()
const { dryRun } = useWizardApi()

// Summary computed properties
const inputTypeSummary = computed(() => {
  const counts: Record<string, number> = {}
  for (const inp of store.inputs) {
    const label = inp.plugin === 'excel' ? 'Excel' : inp.plugin === 'csv' ? 'CSV' : inp.plugin === 'database' ? 'Database' : inp.plugin
    counts[label] = (counts[label] || 0) + 1
  }
  return Object.entries(counts).map(([k, v]) => v > 1 ? `${k}×${v}` : k).join(', ') || '未配置'
})
const processorTypeSummary = computed(() => {
  const counts: Record<string, number> = {}
  for (const proc of store.processors as Array<{plugin: string}>) {
    const label = proc.plugin === 'sql' ? 'SQL' : proc.plugin === 'python' ? 'Python' : proc.plugin
    counts[label] = (counts[label] || 0) + 1
  }
  return Object.entries(counts).map(([k, v]) => v > 1 ? `${k}×${v}` : k).join(', ') || '未配置'
})
const outputTypeLabel = computed(() => {
  const p = store.output?.plugin
  return p === 'excel' ? 'Excel' : p === 'csv' ? 'CSV' : p === 'database' ? 'Database' : '未配置'
})

// Local state
const currentStep = ref(1)

// Dry-run preview state
const dryRunLoading = ref(false)
const dryRunError = ref('')
const previewColumns = ref<string[]>([])
const previewRows = ref<string[][]>([])

async function runDryRun() {
  dryRunLoading.value = true
  dryRunError.value = ''
  try {
    const state = stateToSnakeCase(store.getWizardState())
    const result = await dryRun(state)
    if (result && result.tables && result.tables.length > 0) {
      const firstTable = result.tables[0]
      previewColumns.value = firstTable.columns
      previewRows.value = firstTable.rows
    } else {
      dryRunError.value = '预览未返回数据'
    }
  } catch (e: any) {
    dryRunError.value = e.message || '预览执行失败'
  } finally {
    dryRunLoading.value = false
  }
}

watch(() => store.inputs.length, (len) => {
  if (len === 0 && currentStep.value > 2) currentStep.value = 2
})

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
const progressSteps = computed<StepState[]>(() => [
  { label: '场景信息', status: stepStatus(1) },
  { label: '输入源', status: stepStatus(2) },
  { label: '处理步骤', status: stepStatus(3) },
  { label: '输出配置', status: stepStatus(4) },
  { label: '预览导出', status: stepStatus(5) },
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

function onGoBack(fromStep: number) {
  store.goBackToStep(fromStep)
  currentStep.value = fromStep - 1
  scrollToStep(fromStep - 1)
}

function scrollToStep(n: number) {
  if (n < 1 || n > 5) return
  manualScroll = true
  setTimeout(() => { manualScroll = false }, 1000)
  const el = stepRefs[n - 1]?.value
  if (el?.$el instanceof HTMLElement) {
    el.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  nextTick(() => {
    const target = document.querySelector(`[data-step="${n}"]`)
    if (target) {
      (target as HTMLElement).focus({ preventScroll: true })
    }
  })
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

/* === Main Area === */
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

.wizard__input {
  padding: 5px 8px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  background: var(--color-surface);
  color: var(--color-text);
  transition: border-color var(--transition-fast);
  font-family: var(--font-family);
}

.wizard__input:focus {
  border-color: var(--color-primary-lighter);
  outline: none;
}

.wizard__input::placeholder {
  color: var(--color-text-muted);
}

.wizard__textarea {
  padding: 5px 8px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  background: var(--color-surface);
  color: var(--color-text);
  transition: border-color var(--transition-fast);
  font-family: var(--font-family);
  resize: vertical;
  min-height: 60px;
}

.wizard__textarea:focus {
  border-color: var(--color-primary-lighter);
  outline: none;
}

.wizard__textarea::placeholder {
  color: var(--color-text-muted);
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
  .wizard__input {
    padding: 10px 12px;
    font-size: var(--font-size-base);
  }
  .wizard__textarea {
    padding: 10px 12px;
    font-size: var(--font-size-base);
  }
  .wizard__bottom-spacer {
    height: 100px;
  }
}
</style>
