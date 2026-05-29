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
          size="small"
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
      <textarea
        :value="pyProc.script"
        @input="$emit('update', { script: ($event.target as HTMLTextAreaElement).value })"
        rows="8"
        placeholder="def process(ctx):
    conn = ctx.db.connection
    conn.execute('CREATE TABLE result AS SELECT * FROM source')"
        style="width:100%;background:#1e293b;color:#e2e8f0;font-family:'JetBrains Mono',monospace;font-size:13px;line-height:1.6;padding:10px;border:1px solid #334155;border-radius:8px;resize:vertical;outline:none;"
      />
    </div>

    <!-- Quick templates -->
    <div class="flex flex-wrap gap-1">
      <span class="text-[10px] text-slate-400 mr-1 self-center">模板:</span>
      <NTag size="tiny" class="cursor-pointer" @click="applyTemplate(templates.clean)">数据清洗</NTag>
      <NTag size="tiny" class="cursor-pointer" @click="applyTemplate(templates.filter)">数据过滤</NTag>
      <NTag size="tiny" class="cursor-pointer" @click="applyTemplate(templates.aggregate)">数据聚合</NTag>
      <NTag size="tiny" class="cursor-pointer" @click="applyTemplate(templates.api)">API 调用</NTag>
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
  proc: Extract<ProcessorStep, { plugin: 'python' }>
  index: number
  availableTables: Array<{ label: string; value: string }>
}>()

const emit = defineEmits<{
  update: [partial: Partial<ProcessorStep>]
}>()

const pyProc = computed(() => {
  if (props.proc.plugin !== 'python') throw new Error('PythonProcessorContent received non-Python step')
  return props.proc
})

const store = useWizardStore()
const { dryRun: runDryRunApi, error: wizardApiError } = useWizardApi()

const templates = {
  clean: 'def process(ctx):\n    conn = ctx.db.connection\n    # 删除空行和无效数据\n    conn.execute("DELETE FROM source WHERE name IS NULL")\n    conn.execute("CREATE TABLE result AS SELECT * FROM source WHERE name IS NOT NULL")\n',
  filter: 'def process(ctx):\n    conn = ctx.db.connection\n    # 过滤符合条件的数据\n    conn.execute("CREATE TABLE result AS SELECT * FROM source WHERE date >= \'2024-01-01\'")\n',
  aggregate: 'def process(ctx):\n    conn = ctx.db.connection\n    # 按部门聚合统计\n    conn.execute("CREATE TABLE result AS SELECT dept, COUNT(*) AS cnt, AVG(salary) AS avg_salary FROM source GROUP BY dept")\n',
  api: 'def process(ctx):\n    from urllib.request import urlopen\n    import json\n    conn = ctx.db.connection\n    resp = urlopen("https://api.example.com/data")\n    data = json.loads(resp.read())\n    conn.execute("CREATE TABLE result (name TEXT, value REAL)")\n    for item in data:\n        conn.execute("INSERT INTO result VALUES (?, ?)", [item["name"], item["value"]])\n    conn.commit()\n',
}

const dryRunRunning = ref(false)
const dryRunResult = ref<{ table_name: string; columns: string[]; rows: string[][]; total_rows: number }[] | null>(null)
const dryRunError = ref('')
const dryRunVisible = ref(false)

function applyTemplate(template: string) {
  const tableName = store.inputs[0]?.table?.trim() || 'source'
  emit('update', { script: template.replace(/\bsource\b/g, tableName) })
}

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
