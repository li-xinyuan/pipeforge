<template>
  <div class="wizard">
    <!-- Top Nav -->
    <nav class="wizard__nav">
      <div class="wizard__nav-left">
        <div class="wizard__brand">
          <span class="wizard__logo">⚙️</span>
          <span class="wizard__brand-name">ConfigForge</span>
          <span class="wizard__brand-badge">新配置</span>
        </div>
      </div>
      <div class="wizard__nav-center">
        <router-link to="/" class="wizard__nav-link">我的配置</router-link>
        <router-link to="/settings" class="wizard__nav-link">设置</router-link>
      </div>
      <div class="wizard__nav-right">
        <label class="wizard__toggle-label">
          <span class="wizard__toggle-text">AI</span>
          <span class="wizard__toggle-switch">
            <input type="checkbox" v-model="aiPanelVisible" />
            <span class="wizard__toggle-slider"></span>
          </span>
        </label>
        <button
          class="wizard__theme-btn"
          @click="theme.toggleTheme()"
          :title="theme.isDark.value ? '亮色模式' : '暗色模式'"
        >
          {{ theme.isDark.value ? '☀️' : '🌙' }}
        </button>
      </div>
    </nav>

    <!-- Main: steps area + AI panel -->
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
              <input class="wizard__input" :class="{ 'pulse-cta-input': currentStep === 1 && !store.scene.name.trim() }" v-model="store.scene.name" placeholder="例如：销售报表生成" />
            </div>
            <div class="wizard__form-group">
              <label class="wizard__label">版本号</label>
              <input class="wizard__input" v-model="store.scene.version" placeholder="1.0" />
            </div>
            <div class="wizard__form-group wizard__form-group--full">
              <label class="wizard__label">场景描述</label>
              <textarea
                class="wizard__textarea"
                v-model="store.scene.description"
                placeholder="描述这个配置管道的用途..."
                rows="3"
              ></textarea>
            </div>
          </div>
          <AiInlineTip
            v-if="store.scene.name"
            message="完善场景信息后，后续步骤可以使用 AI 辅助生成 SQL 和列映射"
          />
          <template #footer>
            <span :class="{ 'pulse-cta': currentStep === 1 && store.scene.name.trim() }" style="display:inline-block;border-radius:8px;"><NButton class="btn-primary" :disabled="!store.scene.name.trim()" @click="completeStep(1)">保存并继续 ↓</NButton></span>
            <p v-if="currentStep === 1 && !store.scene.name.trim()" class="wizard__validation-msg">请输入场景名称</p>
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
          <AiInlineTip
            v-if="showStep2Tip"
            message="AI 已分析列结构，点击「AI 分析列」查看详情"
            show-action
            action-label="AI 分析列"
            @action="aiPanelVisible = true"
          />
          <template #footer>
            <span :class="{ 'pulse-cta': currentStep === 2 && store.inputs.length > 0 && store.inputs.every(inp => inp.fileId) }" style="display:inline-block;border-radius:8px;"><NButton class="btn-primary" :disabled="store.inputs.length === 0 || !store.inputs.every(inp => inp.fileId)" @click="completeStep(2)">保存并继续 ↓</NButton></span>
            <p v-if="currentStep === 2 && store.inputs.length === 0" class="wizard__validation-msg">至少需要添加 1 个输入源</p>
          </template>
        </WizardStepCard>

        <!-- Step 3: SQL Processing -->
        <WizardStepCard
          ref="step3El"
          title="SQL 处理"
          description="编写 SQL 查询处理输入数据"
          icon="⚡"
          icon-bg="#fef3c7"
          :status="stepStatus(3)"
          :badge="stepBadge(3)"
        >
          <SqlEditorTab ref="sqlEditorRef" :pulse-cta="currentStep === 3 && store.processors.some(p => !p.sql.trim() || !p.outputTables.length)" />
          <AiInlineTip
            v-if="showStep3Tip"
            message="描述你的查询需求，AI 帮你生成 SQL"
            show-action
            action-label="AI 生成 SQL"
            @action="aiPanelVisible = true"
          />
          <template #footer>
            <span :class="{ 'pulse-cta': currentStep === 3 && store.processors.length > 0 && store.processors.every(p => p.sql.trim() && p.outputTables.length) }" style="display:inline-block;border-radius:8px;"><NButton class="btn-primary" :disabled="!store.processors.length || store.processors.some(p => !p.sql.trim() || !p.outputTables.length)" @click="completeStep(3)">保存并继续 ↓</NButton></span>
            <p v-if="currentStep === 3 && store.processors.some(p => !p.sql.trim() || !p.outputTables.length)" class="wizard__validation-msg">
              {{ store.processors.some(p => !p.sql.trim()) ? '请输入 SQL 查询' : '请输入输出表名' }}
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
          <OutputConfigTab />
          <AiInlineTip
            v-if="showStep4Tip"
            message="AI 可自动推断列映射关系"
            show-action
            action-label="AI 自动映射"
            @action="aiPanelVisible = true"
          />
          <template #footer>
            <span :class="{ 'pulse-cta': currentStep === 4 && store.output?.config?.columns?.length }" style="display:inline-block;border-radius:8px;"><NButton class="btn-primary" :disabled="!store.output?.config?.columns?.length" @click="completeStep(4)">保存并继续 ↓</NButton></span>
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
          <AiInlineTip
            v-if="showStep5Tip"
            message="配置就绪，可以下载或执行"
          />
          <template #footer>
            <ExportActions :yaml="yamlPreviewRef?.yamlText || ''" />
          </template>
        </WizardStepCard>

        <div class="wizard__bottom-spacer" />
      </div>

      <!-- AI Panel -->
      <AiChatPanel
        :visible="aiPanelVisible"
        :messages="aiMessages"
        :quick-actions="aiQuickActions"
        :mode="aiMode"
        :loading="suggesting"
        @send="onAiSend"
        @quick-action="onAiQuickAction"
        @toggle="aiPanelVisible = false"
        @orchestrate-confirm="onOrchestrateConfirm"
        @orchestrate-regenerate="onOrchestrateRegenerate"
      />

      <!-- FAB for AI panel on tablet/mobile -->
      <button
        v-if="!aiPanelVisible && breakpoint !== 'desktop'"
        class="wizard__ai-fab"
        aria-label="打开 AI 助手"
        @click="aiPanelVisible = true"
      >⚡</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import { useConfigApi } from '../composables/useConfigApi'
import { useTheme } from '../composables/useTheme'
import { useBreakpoint } from '../composables/useBreakpoint'
import { NButton } from 'naive-ui'
import WizardProgress from '../components/wizard/WizardProgress.vue'
import type { StepState } from '../components/wizard/WizardProgress.vue'
import WizardStepCard from '../components/wizard/WizardStepCard.vue'
import AiChatPanel from '../components/wizard/AiChatPanel.vue'
import type { ChatMessage } from '../types/wizard'
import AiInlineTip from '../components/wizard/AiInlineTip.vue'
import InputSourceList from '../components/step2/InputSourceList.vue'
import SqlEditorTab from '../components/step3/SqlEditorTab.vue'
import OutputConfigTab from '../components/step3/OutputConfigTab.vue'
import YamlPreview from '../components/step4/YamlPreview.vue'
import ExportActions from '../components/step4/ExportActions.vue'
import { useAiApi } from '../composables/useWizardApi'

const store = useWizardStore()
const theme = useTheme()
const { breakpoint } = useBreakpoint()
const router = useRouter()
const route = useRoute()
const { loadConfigState } = useConfigApi()
const { askSuggestion, askOrchestrate, suggesting } = useAiApi()

const aiMode = computed(() => {
  if (breakpoint.value === 'mobile') return 'fullscreen'
  if (breakpoint.value === 'tablet') return 'overlay'
  return 'sidebar'
})

// Local state
const currentStep = ref(1)

watch(() => store.inputs.length, (len) => {
  if (len === 0 && currentStep.value > 2) currentStep.value = 2
})

const aiPanelVisible = ref(false)
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

// AI inline tip visibility
const showStep2Tip = computed(() =>
  store.inputs.some(inp => inp.fileId && store.uploadedFiles[inp.fileId]?.columns?.length)
)

const showStep3Tip = computed(() =>
  store.inputs.length > 0 && store.processors.every(p => !p.sql.trim())
)

const showStep4Tip = computed(() =>
  store.processors.some(p => !!p.sql.trim()) && !store.output?.config?.columns?.length
)

const showStep5Tip = ref(false)

// AI messages
const aiMessages = ref<ChatMessage[]>([
  { role: 'ai', content: '你好！我是 ConfigForge AI 助手。我可以帮你分析数据列、生成 SQL、自动映射列，以及生成场景描述。' },
])
const orchestrateMode = ref(false)

const aiQuickActions = computed(() => {
  const actions = ['生成场景描述', 'AI 分析列', 'AI 生成 SQL', 'AI 自动映射']
  if (store.inputs.length > 0) {
    actions.unshift('AI 编排步骤链')
  }
  return actions
})

// Step status helpers
function stepStatus(n: number): 'completed' | 'active' | 'locked' {
  if (n < currentStep.value) return 'completed'
  if (n === currentStep.value) return 'active'
  return 'locked'
}

function stepBadge(n: number): string {
  if (n < currentStep.value) return '✓ 已完成'
  if (n === currentStep.value) return '⟳ 当前步骤'
  return '🔒 待解锁'
}

// Progress steps for WizardProgress
const progressSteps = computed<StepState[]>(() => [
  { label: '场景信息', status: stepStatus(1) },
  { label: '输入源', status: stepStatus(2) },
  { label: 'SQL 处理', status: stepStatus(3) },
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
        showStep5Tip.value = true
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

// AI handlers
function onFileReady(fileId: string) {
  aiMessages.value.push({
    role: 'ai',
    content: `检测到文件上传。我可以帮你分析数据列结构，需要的话请点击快捷操作「AI 分析列」。`,
  })
}

async function onAiSend(text: string) {
  aiMessages.value.push({ role: 'user', content: text })

  if (orchestrateMode.value || text.includes('编排') || text.includes('步骤链')) {
    orchestrateMode.value = false
    await doOrchestrate(text)
    return
  }

  const context: Record<string, any> = {
    currentStep: currentStep.value,
    naturalLanguage: text,
  }
  if (store.scene.name) {
    context.sceneName = store.scene.name
    context.sceneDescription = store.scene.description
  }
  if (store.inputs.length > 0) {
    context.inputs = store.inputs.map(inp => {
      const meta = store.uploadedFiles[inp.fileId]
      return {
        plugin: inp.plugin,
        table: inp.table,
        paramKey: inp.paramKey,
        columns: meta?.columns || [],
        config: inp.config,
      }
    })
  }
  if (store.processors.length > 0) {
    context.processorsSql = store.processors.map(p => p.sql).filter(Boolean)
    context.outputTables = store.processors.flatMap(p => p.outputTables).filter(Boolean)
    context.processorSql = store.processors[0]?.sql || ''
    context.outputTable = store.processors[0]?.outputTables[0] || ''
  }

  const result = await askSuggestion('chat', context)
  if (result) {
    try {
      const parsed = JSON.parse(result)
      if (parsed.sql) {
        if (store.processors.length > 0) {
          const targetIndex = sqlEditorRef.value?.expandedIndex ?? store.processors.length - 1
          const proc = { ...store.processors[targetIndex], sql: parsed.sql }
          if (parsed.outputTable) {
            proc.outputTables = [parsed.outputTable]
          }
          store.updateProcessor(targetIndex, proc)
        }
        aiMessages.value.push({
          role: 'ai',
          content: parsed.explanation || '已生成 SQL 并填入处理步骤。',
          code: parsed.sql,
        })
      } else if (parsed.raw) {
        aiMessages.value.push({ role: 'ai', content: parsed.raw })
      } else {
        aiMessages.value.push({ role: 'ai', content: JSON.stringify(parsed, null, 2) })
      }
    } catch {
      aiMessages.value.push({ role: 'ai', content: result })
    }
  } else {
    aiMessages.value.push({
      role: 'ai',
      content: '请求失败。确认 AI 已在设置页配置，且后端服务正在运行。',
    })
  }
}

async function onAiQuickAction(action: string) {
  aiMessages.value.push({ role: 'user', content: action })

  if (action === 'AI 编排步骤链') {
    onOrchestrateAction()
    return
  }

  if (action === 'AI 分析列') {
    const filesWithColumns = store.inputs.filter(inp => inp.fileId && store.uploadedFiles[inp.fileId]?.columns)
    if (filesWithColumns.length === 0) {
      aiMessages.value.push({ role: 'ai', content: '请先在步骤 2 上传数据文件，我才能分析列结构。' })
      return
    }
    const result = await askSuggestion('columns', {
      inputs: filesWithColumns.map(inp => {
        const meta = store.uploadedFiles[inp.fileId]!
        const rows = meta.sampleRows || []
        return {
          name: inp.table,
          table: inp.table,
          columns: meta.columns,
          sampleRows: rows.slice(0, 5),
        }
      }),
    })
    if (result) {
      aiMessages.value.push({ role: 'ai', content: result })
    } else {
      aiMessages.value.push({ role: 'ai', content: 'AI 分析失败。请确认 AI 设置正确且后端服务正在运行。' })
    }
  } else if (action === 'AI 生成 SQL') {
    aiMessages.value.push({
      role: 'ai',
      content: '请在下方输入框用自然语言描述你想要的查询，例如："查询每个部门有多少员工，按人数降序"。我会帮你生成对应的 SQL。',
    })
  } else if (action === 'AI 自动映射') {
    const sourceCols: string[] = []
    for (const inp of store.inputs) {
      const meta = store.uploadedFiles[inp.fileId]
      if (meta?.columns) sourceCols.push(...meta.columns)
    }
    const targetCols = (store.output?.config?.columns || []).map(c => c.target)
    if (targetCols.length === 0) {
      aiMessages.value.push({ role: 'ai', content: '请先在步骤 4 上传模板文件或添加列映射的目标列。' })
      return
    }
    const result = await askSuggestion('mapping', { sourceColumns: sourceCols, targetColumns: targetCols })
    if (result) {
      try {
        const parsed = JSON.parse(result)
        if (parsed.mappings) {
          store.output!.config.columns = parsed.mappings
          aiMessages.value.push({ role: 'ai', content: '已自动完成列映射，请检查步骤 4 的映射结果。' })
        } else {
          aiMessages.value.push({ role: 'ai', content: result })
        }
      } catch {
        aiMessages.value.push({ role: 'ai', content: result })
      }
    } else {
      aiMessages.value.push({ role: 'ai', content: 'AI 映射失败。请确认 AI 设置正确且后端服务正在运行。' })
    }
  } else if (action === '生成场景描述') {
    const result = await askSuggestion('scene', {
      name: store.scene.name,
      description: store.scene.description,
    })
    if (result) {
      try {
        const parsed = JSON.parse(result)
        if (parsed.description) {
          store.scene.description = parsed.description
          aiMessages.value.push({ role: 'ai', content: '已生成场景描述并填入步骤 1。' })
        } else {
          aiMessages.value.push({ role: 'ai', content: result })
        }
      } catch {
        aiMessages.value.push({ role: 'ai', content: result })
      }
    } else {
      aiMessages.value.push({ role: 'ai', content: 'AI 请求失败。请确认 AI 设置正确且后端服务正在运行。' })
    }
  }
}

// Orchestrate handlers
function onOrchestrateAction() {
  if (store.inputs.length === 0) {
    aiMessages.value.push({ role: 'ai', content: '请先在 Step 2 添加输入源并上传文件。' })
    return
  }
  orchestrateMode.value = true
  aiMessages.value.push({ role: 'ai', content: '请用中文描述你想要的最终报表，例如："统计各部门本月的出勤率，包含部门名称、应出勤天数、实际出勤天数"' })
}

async function doOrchestrate(naturalLanguage: string) {
  // Progressive loading feedback
  const statuses = ['分析输入源结构...', '识别数据依赖关系...', '规划处理步骤链...', '生成 SQL 查询...']
  let statusIdx = 0
  const loadingIdx = aiMessages.value.push({ role: 'ai', content: statuses[0] }) - 1
  const statusTimer = setInterval(() => {
    statusIdx = (statusIdx + 1) % statuses.length
    aiMessages.value[loadingIdx] = { role: 'ai', content: statuses[statusIdx] }
  }, 2000)
  const inputsContext = store.inputs
    .filter(inp => inp.fileId)
    .map(inp => {
      const meta = store.uploadedFiles[inp.fileId]
      return { table: inp.table, columns: meta?.columns || [] }
    })
    .filter(inp => inp.table)

  if (inputsContext.length === 0) {
    clearInterval(statusTimer)
    aiMessages.value.splice(loadingIdx, 1)
    aiMessages.value.push({ role: 'ai', content: '没有检测到已上传的输入源，请先在步骤 2 上传文件并确认列信息。' })
    return
  }

  const context = {
    inputs: inputsContext,
    outputColumns: (store.output?.config?.columns || []).map(c => c.target),
    naturalLanguage,
  }
  const result = await askOrchestrate(context)
  clearInterval(statusTimer)
  aiMessages.value.splice(loadingIdx, 1)
  if (result && result.steps.length > 0) {
    aiMessages.value.push({ role: 'ai', content: '', orchestration: result })
  } else if (result?.parse_error) {
    aiMessages.value.push({ role: 'ai', content: 'AI 返回格式异常，请重试。原始响应：' + (result.raw || '').slice(0, 500) })
  } else if (result) {
    aiMessages.value.push({ role: 'ai', content: result.explanation || 'AI 无法根据当前信息规划处理链，请补充更多细节后重试。' })
  } else {
    aiMessages.value.push({ role: 'ai', content: 'AI 请求失败，请确认 AI 设置正确且后端服务正在运行，然后重试。' })
  }
}

function onOrchestrateConfirm(result: any) {
  const processors = result.steps.map((s: any, i: number) => {
    let inputTables = s.input_tables || []
    if (i === 0 && inputTables.length === 0) {
      inputTables = store.inputs.map(inp => inp.table).filter(Boolean)
    }
    return {
      name: s.name || `步骤 ${i + 1}`,
      plugin: 'sql' as const,
      sql: s.sql || '',
      inputTables,
      outputTables: s.output_tables || [],
    }
  })
  store.setProcessors(processors)
  aiMessages.value.push({ role: 'ai', content: '已将处理链填入 Step 3，请检查每步的 SQL 和表名。' })
  aiPanelVisible.value = false
}

function onOrchestrateRegenerate() {
  orchestrateMode.value = true
  aiMessages.value.push({ role: 'ai', content: '请重新描述你的需求，我会重新规划处理链。' })
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
      showStep5Tip.value = true
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

/* === Top Nav === */
.wizard__nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 54px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--color-primary-border);
  z-index: 100;
}

[data-theme="dark"] .wizard__nav {
  background: rgba(10, 28, 20, 0.78);
}

.wizard__nav-left {
  display: flex;
  align-items: center;
}

.wizard__brand {
  display: flex;
  align-items: center;
  gap: 6px;
}

.wizard__logo {
  font-size: 18px;
}

.wizard__brand-name {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text);
}

.wizard__brand-badge {
  font-size: var(--font-size-xs);
  padding: 1px 7px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  border: 1px solid var(--color-primary-border);
  font-weight: 500;
}

.wizard__nav-center {
  display: flex;
  align-items: center;
  gap: 4px;
}

.wizard__nav-link {
  padding: 4px 12px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  text-decoration: none;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast), color var(--transition-fast);
}

.wizard__nav-link:hover {
  background: var(--color-surface-hover);
  color: var(--color-text);
}

.wizard__nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* === Toggle Switch === */
.wizard__toggle-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.wizard__toggle-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.wizard__toggle-switch {
  position: relative;
  display: inline-block;
  width: 38px;
  height: 20px;
}

.wizard__toggle-switch input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.wizard__toggle-slider {
  position: absolute;
  inset: 0;
  background: var(--color-border);
  border-radius: 999px;
  transition: background var(--transition-fast);
  cursor: pointer;
}

.wizard__toggle-slider::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: #fff;
  border-radius: 50%;
  transition: transform var(--transition-fast);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
}

.wizard__toggle-switch input:checked + .wizard__toggle-slider {
  background: var(--color-primary);
}

.wizard__toggle-switch input:checked + .wizard__toggle-slider::after {
  transform: translateX(18px);
}

.wizard__theme-btn {
  background: none;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  cursor: pointer;
  transition: background var(--transition-fast);
  padding: 0;
}

.wizard__theme-btn:hover {
  background: var(--color-surface-hover);
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

/* === Deep: Naive UI Button Override === */
:deep(.btn-primary) {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light)) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 700 !important;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  box-shadow: var(--shadow-button) !important;
  border-radius: var(--radius-sm) !important;
}

:deep(.btn-primary:hover) {
  opacity: 0.92;
}

:deep(.btn-primary:disabled) {
  opacity: 0.45 !important;
  cursor: not-allowed !important;
}

/* ─── AI FAB ─── */
.wizard__ai-fab {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  color: #fff;
  border: none;
  font-size: 20px;
  cursor: pointer;
  z-index: 150;
  box-shadow: var(--shadow-button);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.wizard__ai-fab:hover {
  transform: scale(1.08);
  box-shadow: 0 4px 16px rgba(13, 148, 136, 0.35);
}

/* ─── Step card entrance animation ─── */
:deep(.wizard-step-card--entering) {
  animation: cf-slide-up 0.4s ease-out;
}

/* ─── Responsive: Tablet ─── */
@media (max-width: 1023px) {
  .wizard__nav {
    padding: 0 12px;
    height: 50px;
  }
  .wizard__nav-link {
    padding: 4px 8px;
  }
  .wizard__steps {
    padding: 12px 14px 0;
  }
  .wizard__brand-name {
    font-size: var(--font-size-base);
  }
}

/* ─── Responsive: Mobile ─── */
@media (max-width: 767px) {
  .wizard__nav {
    padding: 0 10px;
    height: 48px;
  }
  .wizard__nav-center {
    display: none;
  }
  .wizard__brand-name {
    display: none;
  }
  .wizard__brand-badge {
    font-size: 10px;
    padding: 1px 5px;
  }
  .wizard__steps {
    padding: 8px 10px 0;
  }
  .wizard__nav-right {
    gap: 8px;
  }
  .wizard__toggle-text {
    font-size: 11px;
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
  .wizard__ai-fab {
    bottom: 16px;
    right: 16px;
    width: 44px;
    height: 44px;
    font-size: 18px;
  }
}
</style>
