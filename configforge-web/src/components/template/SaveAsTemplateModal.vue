<template>
  <NModal v-model:show="visible" preset="card" title="保存为模板" style="max-width: 560px; width: 90vw" :trap-focus="true" :auto-focus="true">
    <div class="stm">
      <div class="stm__form">
        <div class="stm__field">
          <label class="stm__label">模板名称 <span class="stm__required">*</span></label>
          <NInput v-model:value="form.name" placeholder="例如：销售日报生成模板" size="small" />
        </div>
        <div class="stm__field">
          <label class="stm__label">描述</label>
          <NInput v-model:value="form.description" type="textarea" placeholder="描述模板的用途和适用场景..." :rows="3" size="small" />
        </div>
        <div class="stm__row">
          <div class="stm__field stm__field--flex">
            <label class="stm__label">分类 <span class="stm__required">*</span></label>
            <NSelect v-model:value="form.category" :options="categoryOptions" placeholder="选择分类" size="small" />
          </div>
          <div class="stm__field stm__field--flex">
            <label class="stm__label">作者</label>
            <NInput v-model:value="form.author" placeholder="你的名字" size="small" />
          </div>
        </div>
        <div class="stm__field">
          <label class="stm__label">标签</label>
          <NInput v-model:value="tagsInput" placeholder="用逗号分隔，例如：日报,销售,自动化" size="small" @blur="parseTags" />
        </div>
      </div>

      <!-- Preview of what will be saved -->
      <div class="stm__preview">
        <span class="stm__preview-title">将保存以下配置</span>
        <div class="stm__preview-items">
          <div class="stm__preview-item">
            <span class="stm__preview-label">输入源</span>
            <span class="stm__preview-value">{{ inputsSummary }}</span>
          </div>
          <div class="stm__preview-item">
            <span class="stm__preview-label">处理步骤</span>
            <span class="stm__preview-value">{{ processorsSummary }}</span>
          </div>
          <div class="stm__preview-item">
            <span class="stm__preview-label">输出</span>
            <span class="stm__preview-value">{{ outputSummary }}</span>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="stm__footer">
        <NButton @click="visible = false">取消</NButton>
        <NButton type="primary" class="btn-primary" :loading="saving" :disabled="!form.name.trim() || !form.category" @click="onSave">保存为模板</NButton>
      </div>
    </template>
  </NModal>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { NModal, NButton, NInput, NSelect, useMessage } from 'naive-ui'
import { useTemplateApi } from '../../composables/useTemplateApi'
import { useWizardStore } from '../../stores/wizard'
import { stateToSnakeCase } from '../../utils/serialization'

const visible = defineModel<boolean>('show', { required: true })

const emit = defineEmits<{ saved: [] }>()

const store = useWizardStore()
const message = useMessage()
const { createTemplate } = useTemplateApi()

const saving = ref(false)
const tagsInput = ref('')

const form = reactive({
  name: '',
  description: '',
  category: '',
  author: '',
  tags: [] as string[],
})

const categoryOptions = [
  { label: '销售', value: 'sales' },
  { label: '财务', value: 'finance' },
  { label: '人力', value: 'hr' },
  { label: '运维', value: 'ops' },
  { label: '通用', value: 'general' },
]

function parseTags() {
  form.tags = tagsInput.value
    .split(/[,，]/)
    .map(t => t.trim())
    .filter(Boolean)
}

const inputsSummary = computed(() => {
  const inputs = store.inputs
  if (!inputs.length) return '未配置'
  return inputs.map(i => i.plugin).join(', ')
})

const processorsSummary = computed(() => {
  const processors = store.processors
  if (!processors.length) return '未配置'
  return processors.map(p => p.name || p.plugin).join(', ')
})

const outputSummary = computed(() => {
  const output = store.output
  if (!output?.plugin) return '未配置'
  return output.plugin
})

async function onSave() {
  if (!form.name.trim() || !form.category) return
  parseTags()
  saving.value = true
  const configState = stateToSnakeCase(store.getWizardState())
  const result = await createTemplate({
    name: form.name.trim(),
    description: form.description,
    category: form.category,
    tags: form.tags,
    configState: configState as unknown as Record<string, unknown>,
    author: form.author.trim(),
  })
  saving.value = false
  if (result) {
    message.success('模板保存成功')
    visible.value = false
    // Reset form
    form.name = ''
    form.description = ''
    form.category = ''
    form.author = ''
    form.tags = []
    tagsInput.value = ''
    emit('saved')
  } else {
    message.error('模板保存失败，请重试')
  }
}
</script>

<style scoped>
.stm__form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stm__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stm__field--flex {
  flex: 1;
}

.stm__row {
  display: flex;
  gap: 12px;
}

.stm__label {
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--color-text);
}

.stm__required {
  color: var(--color-error);
}

.stm__preview {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
}

.stm__preview-title {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-secondary);
  display: block;
  margin-bottom: 8px;
}

.stm__preview-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stm__preview-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stm__preview-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  min-width: 60px;
  flex-shrink: 0;
}

.stm__preview-value {
  font-size: var(--font-size-sm);
  color: var(--color-text);
}

.stm__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 767px) {
  .stm__row {
    flex-direction: column;
  }
}
</style>
