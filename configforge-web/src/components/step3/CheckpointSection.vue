<template>
  <div class="checkpoint-section">
    <div class="checkpoint-section__toggle" @click="expanded = !expanded">
      <span class="checkpoint-section__arrow">{{ expanded ? '▼' : '▶' }}</span>
      <span class="checkpoint-section__label">数据检查 ({{ checkpoints.length }} 条规则)</span>
    </div>

    <div v-if="expanded" class="checkpoint-section__body">
      <div v-if="checkpoints.length === 0" class="text-xs text-slate-400 mb-3">
        暂无检查规则。添加规则后，管道执行时自动验证数据质量。
      </div>

      <div v-for="(rule, i) in checkpoints" :key="i" class="checkpoint-rule">
        <div class="checkpoint-rule__header">
          <span class="text-xs font-medium text-slate-600">规则 {{ i + 1 }}</span>
          <NButton text type="error" size="tiny" @click="removeRule(i)">删除</NButton>
        </div>
        <div class="checkpoint-rule__grid">
          <div class="checkpoint-rule__field">
            <label class="checkpoint-rule__label">检查表</label>
            <NInput
              :value="rule.table"
              @update:value="(v: string) => updateRule(i, { table: v })"
              size="small"
              placeholder="默认=当前输出表"
            />
          </div>
          <div class="checkpoint-rule__field">
            <label class="checkpoint-rule__label">最小行数</label>
            <NInput
              :value="rule.min != null ? String(rule.min) : ''"
              @update:value="(v: string) => updateRule(i, { min: v ? Number(v) : undefined })"
              size="small"
              placeholder="不限制"
            />
          </div>
          <div class="checkpoint-rule__field">
            <label class="checkpoint-rule__label">最大行数</label>
            <NInput
              :value="rule.max != null ? String(rule.max) : ''"
              @update:value="(v: string) => updateRule(i, { max: v ? Number(v) : undefined })"
              size="small"
              placeholder="不限制"
            />
          </div>
          <div class="checkpoint-rule__field">
            <label class="checkpoint-rule__label">处理方式</label>
            <NSelect
              :value="rule.on_failure"
              @update:value="(v: 'block' | 'warn') => updateRule(i, { on_failure: v })"
              size="small"
              :options="onFailureOptions"
            />
          </div>
        </div>
      </div>

      <NButton dashed size="small" block @click="addRule">+ 添加规则</NButton>

      <div class="checkpoint-ai mt-3">
        <div class="flex items-center gap-2">
          <NInput
            v-model:value="naturalLanguageInput"
            size="small"
            placeholder="用自然语言描述检查规则，例如：结果表至少要有100行"
          />
          <NButton size="small" :loading="aiTranslating" @click="translateNaturalLanguage" :disabled="!naturalLanguageInput.trim()">AI 翻译</NButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NInput, NSelect, NButton, useMessage } from 'naive-ui'
import { useWizardStore } from '../../stores/wizard'
import type { CheckRule } from '../../types/wizard'
import { useAiApi } from '../../composables/useWizardApi'

const props = defineProps<{
  checkpoints: CheckRule[]
  procIndex: number
}>()

const emit = defineEmits<{
  'update:checkpoints': [rules: CheckRule[]]
}>()

const store = useWizardStore()
const { getAiSettings } = useAiApi()
const message = useMessage()
const expanded = ref(false)
const naturalLanguageInput = ref('')
const aiTranslating = ref(false)

async function translateNaturalLanguage() {
  if (!naturalLanguageInput.value.trim()) return
  aiTranslating.value = true
  try {
    const resp = await fetch('/api/ai/translate-checkpoint', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        category: 'checkpoint',
        context: {
          user_input: naturalLanguageInput.value,
          available_tables: store.processors.flatMap(p => p.outputTables).filter(Boolean),
          current_output_table: store.processors[props.procIndex]?.outputTables?.[0] || '',
        },
      }),
    })
    if (!resp.ok) {
      const err = await resp.json()
      message.error(err.detail?.message || err.detail || 'AI 翻译失败')
      return
    }
    const rule = await resp.json()
    naturalLanguageInput.value = ''
    emit('update:checkpoints', [...props.checkpoints, { ...rule, on_failure: rule.on_failure || 'block' }])
    message.success('已添加检查规则')
  } catch {
    message.error('AI 翻译请求失败')
  } finally {
    aiTranslating.value = false
  }
}

const onFailureOptions = [
  { label: '阻断（不通过则停止）', value: 'block' },
  { label: '警告（不通过仅提示）', value: 'warn' },
]

function addRule() {
  const newRule: CheckRule = {
    type: 'row_count',
    table: '',
    on_failure: 'block',
  }
  emit('update:checkpoints', [...props.checkpoints, newRule])
}

function removeRule(i: number) {
  const updated = [...props.checkpoints]
  updated.splice(i, 1)
  emit('update:checkpoints', updated)
}

function updateRule(i: number, partial: Partial<CheckRule>) {
  const updated = props.checkpoints.map((r, idx) =>
    idx === i ? { ...r, ...partial } : r
  )
  emit('update:checkpoints', updated)
}
</script>

<style scoped>
.checkpoint-section {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--color-border-light);
}
.checkpoint-section__toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
  padding: 2px 0;
}
.checkpoint-section__arrow {
  font-size: 10px;
  color: var(--color-text-muted);
  width: 12px;
}
.checkpoint-section__label {
  font-size: 12px;
  color: var(--color-text-muted);
}
.checkpoint-section__body {
  margin-top: 8px;
}
.checkpoint-rule {
  background: var(--color-surface-alt, #f8fafc);
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 8px;
}
.checkpoint-rule__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.checkpoint-rule__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}
.checkpoint-rule__field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.checkpoint-rule__label {
  font-size: 11px;
  color: var(--color-text-muted);
}
</style>
