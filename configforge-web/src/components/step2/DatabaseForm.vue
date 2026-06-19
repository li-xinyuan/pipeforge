<template>
  <div class="cf-form-grid">
    <!-- Connection selector -->
    <div>
      <label class="cf-label">数据库连接 <span class="cf-required">*</span></label>
      <div class="flex items-center gap-2">
        <NSelect
          v-model:value="selectedConnectionId"
          :options="connectionOptions"
          placeholder="选择已有连接..."
          size="small"
          class="flex-1"
          @update:value="onConnectionSelected"
        />
        <NButton size="small" quaternary @click="showConnManager = true">⚙ 管理</NButton>
      </div>
      <p v-if="connections.length === 0" class="text-xs text-amber-600 dark:text-amber-400 mt-1">
        暂无连接，点击"管理"按钮新建数据库连接
      </p>
    </div>

    <!-- Test connection -->
    <div v-if="selectedConnectionId" class="flex items-end gap-2">
      <NButton size="small" :loading="testing" @click="onTestConnection">测试连通</NButton>
      <p v-if="testResult" :class="testResult.ok ? 'text-green-600' : 'text-red-500 dark:text-red-400'" class="text-xs">
        {{ testResult.ok ? '连接成功' : testResult.error }}
      </p>
    </div>

    <!-- Query type toggle -->
    <div v-if="selectedConnectionId">
      <label class="cf-label">查询方式</label>
      <NRadioGroup v-model:value="queryType">
        <NRadio value="table">选择表</NRadio>
        <NRadio value="sql">自定义 SQL</NRadio>
      </NRadioGroup>
    </div>

    <!-- Table selector -->
    <div v-if="selectedConnectionId && queryType === 'table'">
      <label class="cf-label">选择表</label>
      <NSelect
        v-model:value="selectedTable"
        :options="tableOptions"
        :loading="loadingTables"
        :placeholder="loadingTables ? '加载表列表中...' : '选择数据库表...'"
        size="small"
        @update:value="onTableSelected"
      />
      <p v-if="loadTablesError" class="text-xs text-red-500 dark:text-red-400 mt-1">{{ loadTablesError }}</p>
    </div>

    <!-- Column info -->
    <div v-if="selectedTable && queryType === 'table'">
      <label class="cf-label">
        列信息
        <NSpin v-if="loadingColumns" :size="12" class="ml-1" />
      </label>
      <div v-if="loadColumnsError" class="text-xs text-red-500 dark:text-red-400">{{ loadColumnsError }}</div>
      <div v-else-if="columnList.length > 0" class="flex flex-wrap gap-1.5">
        <NTag v-for="col in columnList" :key="col.name" size="small" :bordered="false" type="info">
          {{ col.name }} <span class="text-slate-400 dark:text-slate-500 ml-1">{{ col.type }}</span>
        </NTag>
      </div>
      <p v-else-if="!loadingColumns" class="text-xs" style="color: var(--color-text-muted);">暂无列信息</p>
    </div>

    <!-- SQL editor -->
    <div v-if="selectedConnectionId && queryType === 'sql'" class="cf-form-group--full">
      <label class="cf-label">SQL 查询</label>
      <NInput
        v-model:value="sqlQuery"
        type="textarea"
        placeholder="SELECT * FROM ..."
        :rows="3"
        size="small"
        @update:value="emitUpdate"
      />
    </div>
  </div>

  <!-- Inline connection manager modal -->
  <div v-if="showConnManager" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="closeConnManager">
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto p-5">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-base font-semibold">管理数据库连接</h3>
        <button class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300" @click="closeConnManager">✕</button>
      </div>
      <ConnectionManager />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NSelect, NButton, NRadioGroup, NRadio, NInput, NTag, NSpin } from 'naive-ui'
import { useConnectionApi } from '../../composables/useWizardApi'
import ConnectionManager from '../common/ConnectionManager.vue'
import type { InputSource, DatabaseInputConfig, DbConnectionSummary } from '../../types/wizard'

const props = defineProps<{ input: InputSource; index: number }>()
const emit = defineEmits<{ update: [input: InputSource] }>()

const api = useConnectionApi()

function getDbConfig(): DatabaseInputConfig | null {
  const cfg = props.input.config
  return cfg.type === 'database' ? cfg : null
}

const selectedConnectionId = ref(getDbConfig()?.connectionId || '')
const queryType = ref<'table' | 'sql'>(getDbConfig()?.queryType || 'table')
const selectedTable = ref('')
const sqlQuery = ref(getDbConfig()?.sql || '')
const testing = ref(false)
const loadingTables = ref(false)
const loadingColumns = ref(false)
const loadTablesError = ref<string | null>(null)
const loadColumnsError = ref<string | null>(null)
const testResult = ref<{ ok: boolean; error?: string } | null>(null)
const connections = ref<DbConnectionSummary[]>([])
const tableList = ref<string[]>([])
const columnList = ref<{ name: string; type: string }[]>([])
const showConnManager = ref(false)

async function closeConnManager() {
  showConnManager.value = false
  // Refresh connection list after closing
  connections.value = await api.fetchConnections()
}

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
  // If a connection was already selected (e.g. editing), auto-load tables
  if (selectedConnectionId.value) {
    await autoLoadTables()
    // Restore previously selected table
    const prevTables = getDbConfig()?.tables
    if (prevTables && prevTables.length > 0) {
      selectedTable.value = prevTables[0]
      // Auto-load columns for the previously selected table
      await autoLoadColumns()
    }
  }
})

async function autoLoadTables() {
  if (!selectedConnectionId.value) return
  loadingTables.value = true
  loadTablesError.value = null
  try {
    tableList.value = await api.fetchTables(selectedConnectionId.value)
  } catch (e: unknown) {
    loadTablesError.value = e instanceof Error ? e.message : '加载表列表失败'
    tableList.value = []
  } finally {
    loadingTables.value = false
  }
}

async function autoLoadColumns() {
  if (!selectedConnectionId.value || !selectedTable.value) return
  loadingColumns.value = true
  loadColumnsError.value = null
  try {
    columnList.value = await api.fetchColumns(selectedConnectionId.value, selectedTable.value)
  } catch (e: unknown) {
    loadColumnsError.value = e instanceof Error ? e.message : '加载列信息失败'
    columnList.value = []
  } finally {
    loadingColumns.value = false
  }
}

async function onTableSelected() {
  columnList.value = []
  loadColumnsError.value = null
  emitUpdate()
  await autoLoadColumns()
}

async function onConnectionSelected() {
  testResult.value = null
  tableList.value = []
  columnList.value = []
  selectedTable.value = ''
  sqlQuery.value = ''
  loadTablesError.value = null
  loadColumnsError.value = null
  emitUpdate()
  // Auto-load tables after connection is selected
  await autoLoadTables()
}

async function onTestConnection() {
  testing.value = true
  testResult.value = await api.testConnection(selectedConnectionId.value)
  testing.value = false
}

// When queryType changes to 'table' and tables haven't been loaded yet, auto-load
watch(queryType, async (newType) => {
  if (newType === 'table' && selectedConnectionId.value && tableList.value.length === 0) {
    await autoLoadTables()
  }
  selectedTable.value = ''
  columnList.value = []
  loadColumnsError.value = null
  emitUpdate()
})
</script>
