<template>
  <div class="bg-slate-800 rounded-lg p-5 overflow-x-auto font-mono text-sm leading-relaxed">
    <pre v-if="yamlText" class="text-slate-200"><code>{{ yamlText }}</code></pre>
    <p v-else-if="loading" class="text-slate-400">生成中...</p>
    <p v-else-if="apiError" class="text-red-400">{{ apiError }}</p>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi } from '../../composables/useWizardApi'

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
      name: inp.name,
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
      output_tables: store.processor.outputTables,
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

onMounted(loadYaml)

defineExpose({ loadYaml })
</script>
