<template>
  <NModal v-model:show="visible" preset="card" :title="template?.name || '模板详情'" style="max-width: 640px; width: 90vw" :trap-focus="true" :auto-focus="true">
    <div v-if="template" class="tpm">
      <!-- Header info -->
      <div class="tpm__header">
        <div class="tpm__header-top">
          <span class="tpm__icon">{{ categoryIcon(template.category) }}</span>
          <div class="tpm__header-info">
            <div class="tpm__title-row">
              <h3 class="tpm__name">{{ template.name }}</h3>
              <NTag v-if="template.isOfficial" size="small" :bordered="false" type="info" class="tpm__official">官方</NTag>
            </div>
            <p class="tpm__desc">{{ template.description }}</p>
          </div>
        </div>
        <div class="tpm__meta">
          <span class="tpm__meta-item">{{ template.author }}</span>
          <span class="tpm__meta-sep">·</span>
          <span class="tpm__meta-item">v{{ template.version }}</span>
          <span class="tpm__meta-sep">·</span>
          <span class="tpm__meta-item">使用 {{ template.usageCount }} 次</span>
          <span class="tpm__meta-sep">·</span>
          <span class="tpm__meta-item">{{ categoryLabel(template.category) }}</span>
        </div>
        <div v-if="template.tags.length" class="tpm__tags">
          <NTag v-for="tag in template.tags" :key="tag" size="small" :bordered="false" class="tpm__tag">{{ tag }}</NTag>
        </div>
      </div>

      <!-- Compatibility check -->
      <div class="tpm__section">
        <div class="tpm__section-header">
          <span class="tpm__section-title">兼容性检查</span>
          <NButton size="tiny" :loading="compatLoading" @click="runCompatCheck">检查</NButton>
        </div>
        <div v-if="compatResult" class="tpm__compat">
          <div v-if="compatResult.compatible" class="tpm__compat-ok">
            <span class="tpm__compat-icon">✓</span> 完全兼容
          </div>
          <div v-else class="tpm__compat-warn">
            <span class="tpm__compat-icon">⚠</span> 存在兼容性问题
          </div>
          <div v-if="compatResult.issues.length" class="tpm__compat-issues">
            <div v-for="(issue, i) in compatResult.issues" :key="i" class="tpm__compat-issue">
              <span class="tpm__compat-issue-req">{{ issue.requirement }}</span>
              <span class="tpm__compat-issue-status" :class="{ 'tpm__compat-issue-status--fail': issue.status !== 'ok' }">{{ issue.status }}</span>
              <span v-if="issue.suggestion" class="tpm__compat-issue-suggestion">{{ issue.suggestion }}</span>
            </div>
          </div>
        </div>
        <p v-else-if="!compatLoading" class="tpm__compat-hint">点击"检查"按钮验证模板与当前环境的兼容性</p>
      </div>

      <!-- Config preview -->
      <div class="tpm__section">
        <span class="tpm__section-title">配置预览</span>
        <div class="tpm__preview">
          <div class="tpm__preview-item">
            <span class="tpm__preview-label">输入源</span>
            <span class="tpm__preview-value">{{ inputsSummary }}</span>
          </div>
          <div class="tpm__preview-item">
            <span class="tpm__preview-label">处理步骤</span>
            <span class="tpm__preview-value">{{ processorsSummary }}</span>
          </div>
          <div class="tpm__preview-item">
            <span class="tpm__preview-label">输出</span>
            <span class="tpm__preview-value">{{ outputSummary }}</span>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="tpm__footer">
        <NButton @click="close">关闭</NButton>
        <NButton type="primary" class="btn-primary" :loading="instantiating" @click="onUseTemplate">使用此模板</NButton>
      </div>
    </template>
  </NModal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NModal, NButton, NTag, useMessage } from 'naive-ui'
import type { Template } from '../../types/wizard'
import { useTemplateApi } from '../../composables/useTemplateApi'
import { useWizardStore } from '../../stores/wizard'
import { snakeToCamel } from '../../utils/transform'

const props = defineProps<{
  template: Template | null
}>()

const emit = defineEmits<{ close: [] }>()

const visible = defineModel<boolean>('show', { required: true })
const router = useRouter()
const store = useWizardStore()
const message = useMessage()
const { checkCompatibility, instantiateTemplate } = useTemplateApi()

const compatLoading = ref(false)
const compatResult = ref<{ compatible: boolean; issues: Array<{ requirement: string; status: string; suggestion: string }> } | null>(null)
const instantiating = ref(false)

function close() {
  visible.value = false
  compatResult.value = null
  emit('close')
}

async function runCompatCheck() {
  if (!props.template) return
  compatLoading.value = true
  compatResult.value = null
  const result = await checkCompatibility(props.template.id)
  compatResult.value = result
  compatLoading.value = false
}

async function onUseTemplate() {
  if (!props.template) return
  instantiating.value = true
  const configState = await instantiateTemplate(props.template.id)
  if (configState) {
    store.resetAll()
    store.loadFromConfigState(configState, true)
    message.success('模板已加载，即将进入配置向导')
    visible.value = false
    router.push('/config/new?from_template=1')
  } else {
    message.error('模板实例化失败，请重试')
  }
  instantiating.value = false
}

function categoryIcon(category: string): string {
  const icons: Record<string, string> = {
    'sales': '📊',
    'finance': '💰',
    'hr': '👥',
    'ops': '🔧',
    'general': '📦',
  }
  return icons[category] || '📦'
}

function categoryLabel(category: string): string {
  const labels: Record<string, string> = {
    'sales': '销售',
    'finance': '财务',
    'hr': '人力',
    'ops': '运维',
    'general': '通用',
  }
  return labels[category] || category
}

const configState = computed(() => {
  if (!props.template?.configState) return null
  return snakeToCamel(props.template.configState) as Record<string, unknown>
})

const inputsSummary = computed(() => {
  const inputs = configState.value?.inputs as Array<{ plugin?: string; table?: string }> | undefined
  if (!inputs?.length) return '未配置'
  return inputs.map(i => i.plugin || 'unknown').join(', ')
})

const processorsSummary = computed(() => {
  const processors = configState.value?.processors as Array<{ plugin?: string; name?: string }> | undefined
  if (!processors?.length) return '未配置'
  return processors.map(p => p.name || p.plugin || 'unknown').join(', ')
})

const outputSummary = computed(() => {
  const output = configState.value?.output as { plugin?: string } | undefined
  if (!output?.plugin) return '未配置'
  return output.plugin
})
</script>

<style scoped>
.tpm__header {
  margin-bottom: 16px;
}

.tpm__header-top {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.tpm__icon {
  font-size: 28px;
  flex-shrink: 0;
}

.tpm__header-info {
  min-width: 0;
  flex: 1;
}

.tpm__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.tpm__name {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.tpm__official {
  font-size: 10px;
}

.tpm__desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.tpm__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.tpm__meta-item {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.tpm__meta-sep {
  font-size: var(--font-size-xs);
  color: var(--color-border);
}

.tpm__tags {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.tpm__tag {
  font-size: 11px;
}

.tpm__section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
}

.tpm__section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.tpm__section-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
}

.tpm__compat-ok {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-sm);
  color: var(--color-success);
  font-weight: 500;
}

.tpm__compat-warn {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-sm);
  color: var(--color-warning);
  font-weight: 500;
}

.tpm__compat-icon {
  font-size: 16px;
}

.tpm__compat-issues {
  margin-top: 8px;
}

.tpm__compat-issue {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  font-size: var(--font-size-xs);
  border-bottom: 1px solid var(--color-border-light);
}

.tpm__compat-issue:last-child {
  border-bottom: none;
}

.tpm__compat-issue-req {
  color: var(--color-text);
  font-weight: 500;
  min-width: 80px;
}

.tpm__compat-issue-status {
  color: var(--color-success);
  font-weight: 500;
}

.tpm__compat-issue-status--fail {
  color: var(--color-error);
}

.tpm__compat-issue-suggestion {
  color: var(--color-text-secondary);
  flex: 1;
}

.tpm__compat-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin: 0;
}

.tpm__preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tpm__preview-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tpm__preview-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  min-width: 60px;
  flex-shrink: 0;
}

.tpm__preview-value {
  font-size: var(--font-size-sm);
  color: var(--color-text);
}

.tpm__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
