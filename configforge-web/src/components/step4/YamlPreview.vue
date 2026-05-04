<template>
  <div class="bg-slate-800 rounded-lg p-5 overflow-x-auto font-mono text-sm leading-relaxed">
    <pre class="text-slate-200"><span class="text-slate-500"># {{ store.scene.name }} v{{ store.scene.version }}</span>
<span class="text-blue-300">scene</span>:
  <span class="text-blue-300">name</span>: <span class="text-green-300">{{ store.scene.name }}</span>
  <span class="text-blue-300">version</span>: <span class="text-green-300">"{{ store.scene.version }}"</span>
  <span class="text-blue-300">description</span>: <span class="text-green-300">{{ store.scene.description }}</span>

<span class="text-blue-300">inputs</span>:
<span v-for="(inp, i) in store.inputs" :key="i">  - <span class="text-blue-300">name</span>: <span class="text-green-300">{{ inp.name }}</span>
    <span class="text-blue-300">plugin</span>: <span class="text-green-300">{{ inp.plugin }}</span>
    <span class="text-blue-300">table</span>: <span class="text-green-300">{{ inp.table }}</span>
    <span class="text-blue-300">param_key</span>: <span class="text-green-300">{{ inp.paramKey }}</span>
    <span class="text-blue-300">config</span>:
      <span class="text-blue-300">sheet</span>: <span class="text-green-300">{{ inp.config.sheet }}</span>
</span>
<span class="text-blue-300">processors</span>:
  - <span class="text-blue-300">name</span>: <span class="text-green-300">{{ store.scene.name }}处理</span>
    <span class="text-blue-300">plugin</span>: <span class="text-green-300">sql</span>
    <span class="text-blue-300">output_tables</span>:
      - <span class="text-green-300">{{ store.processor.outputTables.join(', ') }}</span>
    <span class="text-blue-300">config</span>:
      <span class="text-blue-300">sql</span>: <span class="text-green-300">|</span>
<span class="text-green-300">        {{ store.processor.sql }}</span>

<span class="text-blue-300">output</span>:
  <span class="text-blue-300">plugin</span>: <span class="text-green-300">excel</span>
  <span class="text-blue-300">config</span>:
    <span class="text-blue-300">template</span>: <span class="text-green-300">templates/{{ store.scene.name }}_template.xlsx</span>
    <span class="text-blue-300">source_table</span>: <span class="text-green-300">{{ store.output?.config.sourceTable }}</span>
    <span class="text-blue-300">sheet</span>: <span class="text-green-300">{{ store.output?.config.sheet }}</span>
    <span class="text-blue-300">output_dir</span>: <span class="text-green-300">{{ store.output?.config.outputDir }}</span>
    <span class="text-blue-300">filename</span>: <span class="text-green-300">{{ store.output?.config.filename }}</span>
    <span class="text-blue-300">columns</span>:
      <span v-for="c in store.output?.config.columns" :key="c.source">  - <span class="text-blue-300">source</span>: <span class="text-green-300">{{ c.source }}</span>
          <span class="text-blue-300">target</span>: <span class="text-green-300">{{ c.target }}</span>
      </span></pre>
  </div>
</template>
<script setup lang="ts">
import { useWizardStore } from '../../stores/wizard'
const store = useWizardStore()
</script>
