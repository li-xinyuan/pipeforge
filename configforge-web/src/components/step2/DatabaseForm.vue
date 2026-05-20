<template>
  <div class="space-y-3">
    <!-- Connection selector -->
    <div>
      <label class="block text-sm font-medium text-slate-900 mb-1">数据库连接</label>
      <NSelect
        v-model:value="selectedConnectionId"
        :options="connectionOptions"
        placeholder="选择已有连接..."
        @update:value="onConnectionSelected"
      />
      <p class="text-xs text-slate-400 mt-1">
        或前往
        <RouterLink to="/settings" class="text-blue-600 underline">设置页</RouterLink>
        管理连接
      </p>
    </div>

    <!-- Test connection + load tables -->
    <div v-if="selectedConnectionId" class="flex gap-2">
      <NButton size="small" :loading="testing" @click="onTestConnection">测试连通</NButton>
      <NButton size="small" :loading="loadingTables" @click="onLoadTables">加载表列表</NButton>
    </div>
    <p v-if="testResult" :class="testResult.ok ? 'text-green-600' : 'text-red-500'" class="text-xs">
      {{ testResult.ok ? '连接成功' : testResult.error }}
    </p>

    <!-- Query type toggle -->
    <div v-if="selectedConnectionId">
      <label class="block text-sm font-medium text-slate-900 mb-1">查询方式</label>
      <NRadioGroup v-model:value="queryType">
        <NRadio value="table">选择表</NRadio>
        <NRadio value="sql">自定义 SQL</NRadio>
      </NRadioGroup>
    </div>

    <!-- Table selector -->
    <div v-if="selectedConnectionId && queryType === 'table'">
      <label class="block text-sm font-medium text-slate-900 mb-1">选择表</label>
      <NSelect
        v-model:value="selectedTable"
        :options="tableOptions"
        placeholder="选择数据库表..."
        @update:value="emitUpdate"
      />
    </div>

    <!-- SQL editor -->
    <div v-if="selectedConnectionId && queryType === 'sql'">
      <label class="block text-sm font-medium text-slate-900 mb-1">SQL 查询</label>
      <NInput
        v-model:value="sqlQuery"
        type="textarea"
        placeholder="SELECT * FROM ..."
        :rows="3"
        @update:value="emitUpdate"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NSelect, NButton, NRadioGroup, NRadio, NInput } from 'naive-ui'
import { RouterLink } from 'vue-router'
import { useConnectionApi } from '../../composables/useWizardApi'
import type { InputSource, DbConnectionSummary } from '../../types/wizard'

const props = defineProps<{ input: InputSource; index: number }>()
const emit = defineEmits<{ update: [input: InputSource] }>()

const api = useConnectionApi()

const selectedConnectionId = ref(
  props.input.config.type === 'database' ? (props.input.config as any).connectionId || '' : ''
)
const queryType = ref<'table' | 'sql'>(
  props.input.config.type === 'database' ? (props.input.config as any).queryType || 'table' : 'table'
)
const selectedTable = ref('')
const sqlQuery = ref(
  props.input.config.type === 'database' ? (props.input.config as any).sql || '' : ''
)
const testing = ref(false)
const loadingTables = ref(false)
const testResult = ref<{ ok: boolean; error?: string } | null>(null)
const connections = ref<DbConnectionSummary[]>([])
const tableList = ref<string[]>([])

const connectionOptions = computed(() =>
  connections.value.map(c => ({ label: c.name, value: c.id }))
)

const tableOptions = computed(() =>
  tableList.value.map(t => ({ label: t, value: t }))
)

function emitUpdate() {
  const config = {
    type: 'database',
    connectionId: selectedConnectionId.value,
    queryType: queryType.value,
    tables: queryType.value === 'table' && selectedTable.value ? [selectedTable.value] : [],
    sql: queryType.value === 'sql' ? sqlQuery.value : '',
  }
  emit('update', { ...props.input, config } as InputSource)
}

onMounted(async () => {
  connections.value = await api.fetchConnections()
})

async function onConnectionSelected() {
  testResult.value = null
  tableList.value = []
  selectedTable.value = ''
  sqlQuery.value = ''
  emitUpdate()
}

async function onTestConnection() {
  testing.value = true
  testResult.value = await api.testConnection(selectedConnectionId.value)
  testing.value = false
}

async function onLoadTables() {
  loadingTables.value = true
  tableList.value = await api.fetchTables(selectedConnectionId.value)
  loadingTables.value = false
}
</script>
