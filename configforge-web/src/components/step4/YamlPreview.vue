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

  const state = {
    current_step: store.currentStep,
    scene: {
      name: store.scene.name,
      description: store.scene.description,
      version: store.scene.version,
    },
    inputs: store.inputs.map(inp => ({
      name: inp.table,
      plugin: inp.plugin,
      table: inp.table,
      param_key: inp.paramKey,
      file_id: inp.fileId,
      config: inp.config.type === 'csv'
        ? { type: 'csv', delimiter: (inp.config as any).delimiter, encoding: (inp.config as any).encoding, has_header: (inp.config as any).hasHeader }
        : { type: inp.config.type, sheet: (inp.config as any).sheet },
    })),
    processor: {
      plugin: store.processor.plugin,
      sql: store.processor.sql,
      output_tables: [store.processor.outputTable],
    },
    output: store.output ? {
      plugin: store.output.plugin,
      config: store.output.config.type === 'csv'
        ? {
            type: 'csv',
            source_table: (store.output.config as any).sourceTable,
            output_dir: (store.output.config as any).outputDir,
            filename: (store.output.config as any).filename,
            delimiter: (store.output.config as any).delimiter,
            encoding: (store.output.config as any).encoding,
            columns: store.output.config.columns.map(c => ({ source: c.source, target: c.target })),
          }
        : {
            type: store.output.config.type,
            template: (store.output.config as any).template,
            sheet: (store.output.config as any).sheet,
            output_dir: (store.output.config as any).outputDir,
            source_table: (store.output.config as any).sourceTable,
            filename: (store.output.config as any).filename,
            columns: store.output.config.columns.map(c => ({ source: c.source, target: c.target })),
          },
    } : null,
    uploaded_files: {},
  }

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
