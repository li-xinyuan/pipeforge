<template>
  <div class="space-y-3">
    <!-- Step name + Input tables in one row -->
    <div class="grid grid-cols-2 gap-3">
      <div>
        <label class="block text-xs font-medium text-slate-500 mb-1">步骤名称</label>
        <NInput
          :value="proc.name"
          @update:value="(v: string) => $emit('update', { name: v })"
          size="small"
          placeholder="例如：数据清洗"
        />
      </div>
      <div>
        <label class="block text-xs font-medium text-slate-500 mb-1">输入表</label>
        <NSelect
          :value="proc.inputTables"
          :options="availableTables"
          multiple
          size="tiny"
          placeholder="选择输入表（可选）"
          @update:value="(v: string[]) => $emit('update', { inputTables: v })"
        />
      </div>
    </div>

    <!-- Output table -->
    <div>
      <label class="block text-sm font-medium text-slate-900 mb-1">
        <span class="text-red-500">*</span> 输出表名
      </label>
      <NInput
        :value="proc.outputTables[0] || ''"
        @update:value="(v: string) => $emit('update', { outputTables: [v] })"
        size="small"
        placeholder="例如：clean_data"
      />
    </div>

    <!-- Python script textarea -->
    <div>
      <label class="block text-sm font-medium text-slate-900 mb-1">
        <span class="text-red-500">*</span> Python 脚本
      </label>
      <NInput
        :value="pyProc.script"
        @update:value="(v: string) => $emit('update', { script: v })"
        type="textarea"
        :autosize="{ minRows: 6, maxRows: 20 }"
        placeholder="def process(ctx):&#10;    conn = ctx.db.connection&#10;    conn.execute('CREATE TABLE result AS SELECT * FROM source')"
        class="font-mono text-sm"
      />
    </div>

    <!-- Preview execution -->
    <div class="flex gap-2 items-center flex-wrap">
      <NButton v-if="!dryRunVisible || !dryRunResult" size="tiny" type="info" :loading="dryRunRunning" :disabled="!pyProc.script.trim()" @click="runPreview">▶ 预览结果</NButton>
      <NButton v-else size="tiny" type="info" @click="dryRunVisible = false">收起结果</NButton>
    </div>

    <p v-if="dryRunError" class="text-xs text-red-500">{{ dryRunError }}</p>

    <div v-if="dryRunResult && dryRunVisible" class="space-y-2 mt-2">
      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-400">共 {{ dryRunResult.length }} 个表</span>
      </div>
      <div v-for="table in dryRunResult" :key="table.table_name" class="border border-slate-200 rounded p-2">
        <div class="flex items-center gap-2 mb-2">
          <NTag size="tiny" :bordered="false" type="info">{{ table.table_name }}</NTag>
          <span class="text-xs text-slate-400">{{ table.columns.length }} 列 / {{ table.total_rows }} 行</span>
        </div>
        <ColumnPreview :columns="table.columns" :rows="table.rows" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, NTag, NInput, NSelect } from 'naive-ui'
import ColumnPreview from '../step2/ColumnPreview.vue'
import type { ProcessorStep } from '../../types/wizard'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi } from '../../composables/useWizardApi'

const props = defineProps<{
  proc: ProcessorStep
  index: number
  availableTables: Array<{ label: string; value: string }>
}>()

defineEmits<{
  update: [partial: Partial<ProcessorStep>]
}>()

const pyProc = computed(() => {
  if (props.proc.plugin !== 'python') throw new Error('PythonProcessorContent received non-Python step')
  return props.proc
})

const store = useWizardStore()
const { dryRun: runDryRunApi, error: wizardApiError } = useWizardApi()

const dryRunRunning = ref(false)
const dryRunResult = ref<{ table_name: string; columns: string[]; rows: string[][]; total_rows: number }[] | null>(null)
const dryRunError = ref('')
const dryRunVisible = ref(false)

async function runPreview() {
  dryRunError.value = ''
  dryRunResult.value = null
  if (!pyProc.value.script.trim()) {
    dryRunError.value = '请先输入 Python 脚本'
    return
  }
  dryRunRunning.value = true
  const result = await runDryRunApi(store.$state)
  if (result?.tables?.length) {
    const inputTables = new Set(store.inputs.map(inp => inp.table).filter(Boolean))
    const outputTables = result.tables.filter(t => !inputTables.has(t.table_name))
    dryRunResult.value = outputTables.length ? outputTables : result.tables
    dryRunVisible.value = true
  } else {
    const apiMsg = wizardApiError.value?.message || ''
    dryRunError.value = apiMsg ? `预览执行失败: ${apiMsg}` : '预览执行失败，请检查输入配置'
  }
  dryRunRunning.value = false
}
</script>
