<template>
  <div>
    <NCode v-if="yamlText" :code="yamlText" language="yaml" word-wrap />
    <NSkeleton v-else-if="loading" text :repeat="8" />
    <NAlert v-else-if="apiError" type="error" :title="apiError" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { stateToSnakeCase } from '../../utils/serialization'
import { useWizardApi } from '../../composables/useWizardApi'
import { NCode, NSkeleton, NAlert } from 'naive-ui'

const store = useWizardStore()
const { generateYaml } = useWizardApi()
const yamlText = ref('')
const loading = ref(false)
const apiError = ref('')

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
