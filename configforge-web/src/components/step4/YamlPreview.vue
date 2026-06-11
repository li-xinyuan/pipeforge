<template>
  <div>
    <!-- 顶部操作栏 -->
    <div v-if="yamlText" style="display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 8px;">
      <template v-if="!editing">
        <NButton size="small" @click="startEdit">编辑</NButton>
      </template>
      <template v-else>
        <NButton size="small" type="primary" @click="saveEdit">保存</NButton>
        <NButton size="small" @click="cancelEdit">取消</NButton>
      </template>
    </div>

    <!-- 编辑模式 -->
    <template v-if="editing">
      <NInput
        v-model:value="editText"
        type="textarea"
        :rows="20"
        font="monospace"
        placeholder="请输入 YAML 内容"
      />
      <NAlert v-if="parseError" type="error" :title="parseError" style="margin-top: 8px;" />
    </template>

    <!-- 只读模式 -->
    <template v-else>
      <NCode v-if="yamlText" :code="yamlText" language="yaml" word-wrap />
      <NSkeleton v-else-if="loading" text :repeat="8" />
      <NAlert v-else-if="apiError" type="error" :title="apiError" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { stateToSnakeCase } from '../../utils/serialization'
import { useWizardApi } from '../../composables/useWizardApi'
import { NCode, NSkeleton, NAlert, NButton, NInput } from 'naive-ui'
import yaml from 'js-yaml'

const store = useWizardStore()
const { generateYaml } = useWizardApi()
const yamlText = ref('')
const loading = ref(false)
const apiError = ref('')

// 编辑模式状态
const editing = ref(false)
const editText = ref('')
const parseError = ref('')

function startEdit() {
  editText.value = yamlText.value
  parseError.value = ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  parseError.value = ''
}

function saveEdit() {
  parseError.value = ''
  try {
    const parsed = yaml.load(editText.value) as Record<string, unknown>
    store.loadFromConfigState(parsed)
    yamlText.value = editText.value
    editing.value = false
  } catch {
    parseError.value = 'YAML 格式错误，请检查语法'
  }
}

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

onMounted(() => {
  if (store.scene.name.trim()) loadYaml()
})

defineExpose({ loadYaml, yamlText })
</script>
