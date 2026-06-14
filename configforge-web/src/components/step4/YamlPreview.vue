<template>
  <div>
    <div class="yaml-preview__toolbar">
      <NButton size="tiny" :type="isEditing ? 'primary' : 'default'" @click="toggleEdit">
        {{ isEditing ? '预览模式' : '编辑模式' }}
      </NButton>
      <NButton v-if="isEditing" size="tiny" type="primary" @click="saveEdit" :disabled="!!parseError">
        保存修改
      </NButton>
      <span v-if="parseError" class="yaml-preview__error">{{ parseError }}</span>
    </div>
    <CodeEditor
      :model-value="isEditing ? editText : (yamlText || '')"
      @update:model-value="onEditorChange"
      language="yaml"
      :read-only="!isEditing"
      min-height="300px"
      placeholder="YAML 配置内容..."
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi } from '../../composables/useWizardApi'
import { NButton, useMessage } from 'naive-ui'
import yaml from 'js-yaml'
import CodeEditor from '../common/CodeEditor.vue'

const store = useWizardStore()
const { generateYaml } = useWizardApi()
const message = useMessage()
const yamlText = ref('')
const loading = ref(false)
const apiError = ref('')
const isEditing = ref(false)
const editText = ref('')
const parseError = ref('')

async function loadYaml() {
  loading.value = true
  apiError.value = ''

  const data = await generateYaml(store.getWizardState())
  if (data) {
    yamlText.value = data.yaml
  } else {
    apiError.value = '无法生成 YAML'
  }
  loading.value = false
}

function toggleEdit() {
  if (!isEditing.value) {
    editText.value = yamlText.value
    parseError.value = ''
  }
  isEditing.value = !isEditing.value
}

function onEditorChange(value: string) {
  if (!isEditing.value) return
  editText.value = value
  try {
    yaml.load(value)
    parseError.value = ''
  } catch (e: unknown) {
    parseError.value = e instanceof Error ? e.message : 'YAML 语法错误'
  }
}

function saveEdit() {
  try {
    const parsed = yaml.load(editText.value)
    if (typeof parsed === 'object' && parsed !== null) {
      yamlText.value = editText.value
      message.success('YAML 配置已更新')
    }
  } catch (e: unknown) {
    message.error('YAML 格式错误，无法保存：' + (e instanceof Error ? e.message : ''))
  }
}

onMounted(() => {
  if (store.scene.name.trim()) loadYaml()
})

defineExpose({ loadYaml, yamlText })
</script>

<style scoped>
.yaml-preview__toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.yaml-preview__error {
  font-size: 12px;
  color: var(--color-error);
}
</style>
