<template>
  <div class="wizard">
    <AppNavBar current-route="wizard" :badge="route.query.load ? '编辑配置' : '新配置'" />

    <!-- Main: steps area + Guide panel -->
    <div class="wizard__main">
      <!-- Scrollable steps -->
      <div ref="scrollEl" class="wizard__steps">
        <WizardProgress :steps="progressSteps" @step-click="scrollToStep" />

        <!-- Step 1: Scene Info -->
        <ErrorBoundary>
          <WizardStepCard
            ref="step1El"
            title="场景信息"
            description="告诉 ConfigForge 你想做什么"
            icon="🎨"
            icon-bg="#f0fdfa"
            :status="stepStatus(1)"
            :badge="stepBadge(1)"
            :step="1"
            :collapsed="isStepCollapsed(1)"
            :summary="stepSummary(1)"
            @header-click="onStepHeaderClick(1)"
          >
            <div class="wizard__form-grid">
              <div class="wizard__form-group">
                <label class="wizard__label">场景名称 <span class="wizard__required">*</span></label>
                <NInput v-model:value="store.scene.name" :class="{ 'pulse-cta-input': currentStep === 1 && !store.canProceed(1) }" placeholder="例如：销售报表生成" size="small" />
                <p v-if="currentStep === 1 && store.stepValidation(1).length" class="wizard__validation-msg">{{ store.stepValidation(1).join('；') }}</p>
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
        </ErrorBoundary>

        <!-- Step 2: Input Sources -->
        <ErrorBoundary>
          <WizardStepCard
            ref="step2El"
            title="输入源"
            description="添加数据文件作为管道的输入"
            icon="📂"
            icon-bg="#ccfbf1"
            :status="stepStatus(2)"
            :badge="stepBadge(2)"
            :step="2"
            :collapsed="isStepCollapsed(2)"
            :summary="stepSummary(2)"
            @header-click="onStepHeaderClick(2)"
          >
            <InputSourceList :pulse-cta="currentStep === 2" />
            <template #footer>
              <NButton @click="onGoBack(2)">← 上一步</NButton>
              <NButton :class="{ 'btn-primary': true, 'pulse-cta': currentStep === 2 && store.canProceed(2) }" :disabled="!store.canProceed(2)" @click="completeStep(2)">下一步 ↓</NButton>
              <p v-if="!store.canProceed(2)" class="wizard__validation-msg">{{ store.stepValidation(2).join('；') || '请先添加输入源并上传文件' }}</p>
            </template>
          </WizardStepCard>
        </ErrorBoundary>

        <!-- Step 3: SQL Processing -->
        <ErrorBoundary>
          <WizardStepCard
            ref="step3El"
            title="处理步骤"
            description="对输入数据进行加工和转换"
            icon="⚡"
            icon-bg="#fef3c7"
            :status="stepStatus(3)"
            :badge="stepBadge(3)"
            :step="3"
            :collapsed="isStepCollapsed(3)"
            :summary="stepSummary(3)"
            @header-click="onStepHeaderClick(3)"
          >
            <SqlEditorTab ref="sqlEditorRef" :pulse-cta="currentStep === 3 && !store.canProceed(3)" />
            <template #footer>
              <NButton @click="onGoBack(3)">← 上一步</NButton>
              <NButton :class="{ 'btn-primary': true, 'pulse-cta': currentStep === 3 && store.canProceed(3) }" :disabled="!store.canProceed(3)" @click="completeStep(3)">下一步 ↓</NButton>
              <p v-if="!store.canProceed(3)" class="wizard__validation-msg">{{ store.stepValidation(3).join('；') || '请先添加处理步骤' }}</p>
            </template>
          </WizardStepCard>
        </ErrorBoundary>

        <!-- Step 4: Output Config -->
        <ErrorBoundary>
          <WizardStepCard
            ref="step4El"
            title="输出配置"
            description="配置输出格式和列映射"
            icon="📤"
            icon-bg="#fef2f2"
            :status="stepStatus(4)"
            :badge="stepBadge(4)"
            :step="4"
            :collapsed="isStepCollapsed(4)"
            :summary="stepSummary(4)"
            @header-click="onStepHeaderClick(4)"
          >
            <OutputConfigTab :pulse-cta="currentStep === 4" />
            <template #footer>
              <NButton @click="onGoBack(4)">← 上一步</NButton>
              <NButton :class="{ 'btn-primary': true, 'pulse-cta': currentStep === 4 && store.canProceed(4) }" :disabled="!store.canProceed(4)" @click="completeStep(4)">下一步 ↓</NButton>
              <p v-if="!store.canProceed(4)" class="wizard__validation-msg">{{ store.stepValidation(4).join('；') || '请先完成输出配置' }}</p>
            </template>
          </WizardStepCard>
        </ErrorBoundary>

        <!-- Step 5: Preview & Export -->
        <ErrorBoundary>
          <WizardStepCard
            ref="step5El"
            title="预览与导出"
            description="查看 YAML 配置并导出"
            icon="🚀"
            icon-bg="#eff6ff"
            :status="stepStatus(5)"
            :badge="stepBadge(5)"
            :step="5"
            :collapsed="isStepCollapsed(5)"
            :summary="stepSummary(5)"
            @header-click="onStepHeaderClick(5)"
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
              <p v-if="previewColumns.length > 0" class="text-xs text-amber-500 mb-1">⚠ 预览基于样本数据，结果可能与实际执行不同</p>
              <DataPreviewTable
                v-if="previewColumns.length > 0"
                :columns="previewColumns"
                :rows="previewRows"
              />
              <p v-else-if="!dryRunLoading" class="text-xs text-slate-400">点击"运行预览"查看数据处理结果</p>
            </div>

            <YamlPreview ref="yamlPreviewRef" />

            <!-- AI Precheck -->
            <div style="margin-top: 16px;">
              <div class="flex items-center gap-2 mb-2">
                <AiTriggerButton label="AI 预检配置" :loading="precheckLoading" :disabled="precheckLoading" @click="runPrecheck" />
              </div>
              <div v-if="precheckResult" class="ai-precheck-result">
                <div class="ai-precheck-result__summary" :class="precheckSummaryClass">{{ precheckResult.summary }}</div>
                <div v-if="precheckResult.issues.length" class="ai-precheck-result__issues">
                  <div v-for="(issue, i) in precheckResult.issues" :key="i" class="ai-precheck-result__issue" :class="`ai-precheck-result__issue--${issue.severity}`">
                    <span class="ai-precheck-result__badge">{{ issue.severity === 'error' ? '错误' : issue.severity === 'warning' ? '警告' : '提示' }}</span>
                    <span class="ai-precheck-result__step">步骤 {{ issue.step }}</span>
                    <span class="ai-precheck-result__msg">{{ issue.message }}</span>
                  </div>
                </div>
              </div>
              <p v-if="precheckError" class="text-xs text-red-500 mt-1">{{ precheckError }}</p>
            </div>

            <!-- Notification Settings -->
            <div style="margin-top: 16px; border-top: 1px solid var(--color-border-light); padding-top: 12px;">
              <NotificationSettings />
            </div>
            <template #footer>
              <NButton @click="onGoBack(5)">← 上一步</NButton>
              <ExportActions ref="exportActionsRef" :yaml="yamlPreviewRef?.yamlText || ''" @goto-step="scrollToStep" />
              <NButton class="btn-secondary" @click="saveAsTemplateVisible = true">保存为模板</NButton>
            </template>
          </WizardStepCard>
        </ErrorBoundary>

        <div class="wizard__bottom-spacer" />
      </div>

      <!-- Guide Panel (right side tips) -->
      <GuidePanel :current-step="currentStep" />
    </div>

    <!-- Save As Template Modal -->
    <SaveAsTemplateModal v-model:show="saveAsTemplateVisible" />

    <!-- Mobile bottom step navigation -->
    <div class="wizard__mobile-nav">
      <button
        v-for="s in 5"
        :key="s"
        class="wizard__mobile-nav__step"
        :class="{ 'wizard__mobile-nav__step--active': currentStep === s, 'wizard__mobile-nav__step--done': currentStep > s }"
        @click="scrollToStep(s)"
      >
        <span class="wizard__mobile-nav__dot">{{ currentStep > s ? '✓' : s }}</span>
        <span class="wizard__mobile-nav__label">{{ stepLabels[s - 1] }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import { useRoute, onBeforeRouteLeave } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import { useConfigApi } from '../composables/useConfigApi'
import { useWizardApi, useAiApi } from '../composables/useWizardApi'
import { useKeyboard } from '../composables/useKeyboard'
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
import AiTriggerButton from '../components/common/AiTriggerButton.vue'
import NotificationSettings from '../components/step5/NotificationSettings.vue'
import SaveAsTemplateModal from '../components/template/SaveAsTemplateModal.vue'
import ErrorBoundary from '../components/common/ErrorBoundary.vue'

const store = useWizardStore()
const route = useRoute()
const { loadConfigState } = useConfigApi()
const { dryRun, error: wizardApiError } = useWizardApi()
const { suggesting: precheckLoading, aiError: _precheckAiError, askSuggestion } = useAiApi()

// AI Precheck state
interface PrecheckIssue {
  severity: 'error' | 'warning' | 'info'
  step: number
  message: string
}
const precheckResult = ref<{ issues: PrecheckIssue[]; summary: string } | null>(null)
const precheckError = ref('')

const precheckSummaryClass = computed(() => {
  if (!precheckResult.value) return ''
  const hasError = precheckResult.value.issues.some(i => i.severity === 'error')
  const hasWarning = precheckResult.value.issues.some(i => i.severity === 'warning')
  if (hasError) return 'ai-precheck-result__summary--error'
  if (hasWarning) return 'ai-precheck-result__summary--warning'
  return 'ai-precheck-result__summary--ok'
})

async function runPrecheck() {
  precheckError.value = ''
  precheckResult.value = null
  try {
    const yamlText = yamlPreviewRef.value?.yamlText || ''
    const content = await askSuggestion('precheck', {
      scene_name: store.scene.name,
      inputs: store.inputs.map(inp => ({
        table: inp.table,
        plugin: inp.plugin,
        fileId: inp.fileId ? '(已上传)' : '(未上传)',
      })),
      processors: store.processors.map(p => ({
        name: p.name,
        plugin: p.plugin,
        inputTables: p.inputTables || [],
        outputTables: p.outputTables,
        hasCode: p.plugin === 'sql' ? !!p.sql.trim() : !!p.script?.trim(),
      })),
      output: store.output ? {
        plugin: store.output.plugin,
        hasColumns: (store.output.config?.columns?.length || 0) > 0,
        sourceTable: store.output.config?.sourceTable || '',
      } : {},
      yaml: yamlText,
    })
    if (content) {
      try {
        const parsed = JSON.parse(content)
        precheckResult.value = {
          issues: Array.isArray(parsed.issues) ? parsed.issues : [],
          summary: parsed.summary || '预检完成',
        }
      } catch {
        precheckResult.value = { issues: [], summary: content }
      }
    }
  } catch (e) {
    precheckError.value = e instanceof Error ? e.message : '预检失败'
  }
}

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
const expandedStep = ref(1)
const saveAsTemplateVisible = ref(false)
const stepLabels = ['场景', '输入', '处理', '输出', '导出']

// Sync expandedStep with currentStep
watch(currentStep, (val) => {
  expandedStep.value = val
})

// Step summary computed
function stepSummary(n: number): string {
  switch (n) {
    case 1:
      return store.scene.name ? `场景：${store.scene.name}` : '未填写场景名称'
    case 2:
      return store.inputs.length > 0 ? `${store.inputs.length} 个输入源（${inputTypeSummary.value}）` : '未配置输入源'
    case 3:
      return store.processors.length > 0 ? `${store.processors.length} 个处理步骤（${processorTypeSummary.value}）` : '未配置处理步骤'
    case 4:
      return outputTypeLabel.value !== '未配置' ? `输出类型：${outputTypeLabel.value}` : '未配置输出'
    case 5:
      return '待执行'
    default:
      return ''
  }
}

function isStepCollapsed(n: number): boolean {
  // Current step is always expanded
  if (n === currentStep.value) return false
  // Allow one additional completed step to be expanded
  return expandedStep.value !== n
}

function onStepHeaderClick(n: number) {
  if (n < currentStep.value) {
    expandedStep.value = expandedStep.value === n ? currentStep.value : n
    if (expandedStep.value === n) {
      scrollToStep(n)
    }
  }
}

// Keyboard shortcuts
useKeyboard({
  'Ctrl+s': () => {
    exportActionsRef.value?.saveConfigHandler()
  },
  'Ctrl+Enter': () => {
    exportActionsRef.value?.downloadResult()
  },
  'Ctrl+1': () => scrollToStep(1),
  'Ctrl+2': () => scrollToStep(2),
  'Ctrl+3': () => scrollToStep(3),
  'Ctrl+4': () => scrollToStep(4),
  'Ctrl+5': () => scrollToStep(5),
  'Escape': () => {
    if (saveAsTemplateVisible.value) {
      saveAsTemplateVisible.value = false
    }
  },
})

// Dry-run preview state
const dryRunLoading = ref(false)
const dryRunError = ref('')
const previewColumns = ref<string[]>([])
const previewRows = ref<string[][]>([])

async function runDryRun() {
  dryRunLoading.value = true
  dryRunError.value = ''
  try {
    const result = await dryRun(store.getWizardState())
    if (result && result.tables && result.tables.length > 0) {
      const firstTable = result.tables[0]
      previewColumns.value = firstTable.columns
      previewRows.value = firstTable.rows
    } else if (wizardApiError.value) {
      dryRunError.value = wizardApiError.value.message || '预览执行失败'
    } else {
      dryRunError.value = '预览未返回数据'
    }
  } catch (e: unknown) {
    dryRunError.value = e instanceof Error ? e.message : '预览执行失败'
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
const exportActionsRef = ref<InstanceType<typeof ExportActions>>()

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
  nextTick(() => {
    const el = stepRefs[n - 1]?.value
    if (el?.$el instanceof HTMLElement) {
      el.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
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

// ── Navigation guard: warn on unsaved changes ──
function hasUnsavedChanges(): boolean {
  // If loading from config or template, no unsaved changes warning
  if (route.query.load || route.query.from_template) return false
  // If configId is set (editing existing config), no unsaved changes warning
  if (store.configId) return false
  // If store has meaningful data, consider it unsaved
  return store.scene.name.trim().length > 0
    || store.inputs.length > 0
    || store.processors.length > 0
    || store.output !== null
}

onBeforeRouteLeave((to) => {
  // Skip confirmation when navigating to login (logout action)
  if (to.path === '/login') return true
  if (hasUnsavedChanges()) {
    const confirmed = window.confirm('您有未保存的修改，确定要离开吗？')
    if (!confirmed) return false
  }
})

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (hasUnsavedChanges()) {
    e.preventDefault()
  }
}

onMounted(async () => {
  const loadId = route.query.load as string | undefined
  const fromTemplate = route.query.from_template as string | undefined
  if (loadId) {
    const state = await loadConfigState(loadId)
    if (state) {
      store.setConfigId(loadId)
      store.loadFromConfigState(state)
      currentStep.value = 5
      await nextTick()
      yamlPreviewRef.value?.loadYaml()
    } else {
      store.resetAll()
    }
  } else if (fromTemplate) {
    // Template data already loaded by TemplatePreviewModal, don't reset
    currentStep.value = store.currentStep
  } else {
    store.resetAll()
  }

  const prompt = route.query.prompt as string | undefined
  if (prompt) {
    store.scene.description = prompt
  }

  // Apply autofixes if present in query params
  const autofixParam = route.query.autofix as string | undefined
  const stepParam = route.query.step as string | undefined
  if (autofixParam && loadId) {
    try {
      const fixes = JSON.parse(decodeURIComponent(atob(autofixParam)))
      if (Array.isArray(fixes) && fixes.length > 0) {
        store.applyAutofixes(fixes)
        if (stepParam) {
          const targetStep = parseInt(stepParam, 10)
          if (targetStep >= 1 && targetStep <= 5) {
            currentStep.value = targetStep
          }
        }
      }
    } catch {
      // Invalid autofix param, ignore
    }
  }

  lastScrollY = window.scrollY
  window.addEventListener('scroll', onPageScroll, { passive: true })
  window.addEventListener('beforeunload', onBeforeUnload)

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
  window.removeEventListener('beforeunload', onBeforeUnload)
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
  gap: 0;
  padding-right: 12px;
}

/* === Scrollable Steps === */
.wizard__steps {
  flex: 1;
  overflow-y: auto;
  padding: 12px 0 0 0;
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

/* === Mobile bottom step nav (hidden on desktop) === */
.wizard__mobile-nav {
  display: none;
}

/* === AI Precheck Result === */
.ai-precheck-result {
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.ai-precheck-result__summary {
  padding: 10px 14px;
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.ai-precheck-result__summary--error {
  background: var(--color-error-bg);
  color: var(--color-error);
  border-bottom: 1px solid var(--color-error-border);
}

.ai-precheck-result__summary--warning {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border-bottom: 1px solid var(--color-warning-border);
}

.ai-precheck-result__summary--ok {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.ai-precheck-result__issues {
  padding: 8px 14px;
}

.ai-precheck-result__issue {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  font-size: var(--font-size-xs);
  border-bottom: 1px solid var(--color-border-light);
}

.ai-precheck-result__issue:last-child {
  border-bottom: none;
}

.ai-precheck-result__badge {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.ai-precheck-result__issue--error .ai-precheck-result__badge {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.ai-precheck-result__issue--warning .ai-precheck-result__badge {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.ai-precheck-result__issue--info .ai-precheck-result__badge {
  background: var(--color-info-bg);
  color: var(--color-info);
}

.ai-precheck-result__step {
  flex-shrink: 0;
  color: var(--color-text-muted);
  min-width: 42px;
}

.ai-precheck-result__msg {
  color: var(--color-text);
  line-height: 1.5;
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
  .wizard__main {
    flex-direction: column;
  }
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

  /* Mobile bottom step navigation */
  .wizard__mobile-nav {
    display: flex;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 100;
    background: var(--color-surface);
    border-top: 1px solid var(--color-border);
    padding: 6px 0 env(safe-area-inset-bottom, 6px);
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
  }
  .wizard__mobile-nav__step {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 4px 0;
    border: none;
    background: none;
    cursor: pointer;
    color: var(--color-text-muted);
    font-size: 10px;
    transition: color 0.2s;
  }
  .wizard__mobile-nav__step--active {
    color: var(--color-primary);
  }
  .wizard__mobile-nav__step--done {
    color: var(--color-success);
  }
  .wizard__mobile-nav__dot {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    border: 2px solid var(--color-border);
    background: var(--color-surface);
    transition: all 0.2s;
  }
  .wizard__mobile-nav__step--active .wizard__mobile-nav__dot {
    border-color: var(--color-primary);
    background: var(--color-primary);
    color: #fff;
  }
  .wizard__mobile-nav__step--done .wizard__mobile-nav__dot {
    border-color: var(--color-success);
    background: var(--color-success);
    color: #fff;
  }
  .wizard__mobile-nav__label {
    font-size: 10px;
    line-height: 1;
  }
}
</style>
