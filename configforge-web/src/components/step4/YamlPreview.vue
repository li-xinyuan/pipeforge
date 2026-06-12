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
    <div v-if="isEditing">
      <NInput
        v-model:value="editText"
        type="textarea"
        :rows="20"
        font="monospace"
        placeholder="YAML 配置内容..."
        @update:value="onEditChange"
      />
    </div>
    <div v-else>
      <NCode v-if="yamlText" :code="yamlText" language="yaml" word-wrap />
      <NSkeleton v-else-if="loading" text :repeat="8" />
      <NAlert v-else-if="apiError" type="error" :title="apiError" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { stateToSnakeCase } from '../../utils/serialization'
import { useWizardApi } from '../../composables/useWizardApi'
import { NCode, NSkeleton, NAlert, NInput, NButton, useMessage } from 'naive-ui'
import yaml from 'js-yaml'

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

  const state = stateToSnakeCase(store.getWizardState())
  const data = await generateYaml(state)
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

function onEditChange(value: string) {
  editText.value = value
  try {
    yaml.load(value)
    parseError.value = ''
  } catch (e: any) {
    parseError.value = e.message || 'YAML 语法错误'
  }
}

function saveEdit() {
  try {
    const parsed = yaml.load(editText.value)
    if (typeof parsed === 'object' && parsed !== null) {
      yamlText.value = editText.value
      message.success('YAML 配置已更新')
    }
  } catch (e: any) {
    message.error('YAML 格式错误，无法保存：' + (e.message || ''))
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
