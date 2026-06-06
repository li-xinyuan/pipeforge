<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300">数据库连接</h3>
      <NButton size="tiny" @click="startCreate">
        {{ showForm && !editingId ? '取消' : '+ 新建连接' }}
      </NButton>
    </div>

    <!-- Connection list -->
    <div v-if="connections.length === 0 && !showForm" class="text-center py-6">
      <p class="text-2xl mb-2">🔌</p>
      <p class="text-sm text-slate-500 dark:text-slate-400 mb-2">暂无连接配置</p>
      <p class="text-xs text-slate-400 dark:text-slate-500">点击上方"新建连接"配置数据库连接</p>
    </div>

    <div v-for="conn in connections" :key="conn.id" class="flex items-center justify-between py-2 px-3 bg-slate-50 dark:bg-slate-800 rounded border border-transparent hover:border-slate-300 dark:hover:border-slate-600 transition-colors text-sm">
      <div>
        <span class="font-medium">{{ conn.name }}</span>
        <span class="text-xs text-slate-400 dark:text-slate-500 ml-2">{{ conn.dbType }} · {{ conn.host }}:{{ conn.port }} · {{ conn.database }}</span>
        <span v-if="!conn.verified" class="text-orange-500 dark:text-orange-400 ml-1">⚠</span>
        <span v-else class="text-green-500 dark:text-green-400 ml-1">✓</span>
      </div>
      <div class="flex gap-1">
        <NButton text size="tiny" @click="startEdit(conn)">编辑</NButton>
        <NButton text size="tiny" @click="onTest(conn.id)">测试</NButton>
        <NButton text size="tiny" type="error" @click="onDelete(conn.id)">删除</NButton>
      </div>
    </div>

    <!-- Add / Edit form -->
    <div v-if="showForm" class="space-y-2 p-3 border border-slate-200 dark:border-slate-700 rounded">
      <p class="text-xs font-medium text-slate-500 dark:text-slate-400">{{ editingId ? '编辑连接' : '新建连接' }}</p>
      <div>
        <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">连接名称</label>
        <NInput v-model:value="form.name" size="small" placeholder="连接名称" />
      </div>
      <div>
        <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">数据库类型</label>
        <NSelect v-model:value="form.dbType" size="small" :options="dbTypeOptions" placeholder="数据库类型" :disabled="!!editingId" />
      </div>
      <template v-if="form.dbType === 'sqlite'">
        <div>
          <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">文件路径</label>
          <NInput v-model:value="form.filePath" size="small" placeholder="文件路径（如 /data/report.db）" />
        </div>
      </template>
      <template v-else>
        <div>
          <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">主机</label>
          <NInput v-model:value="form.host" size="small" placeholder="主机" />
        </div>
        <div class="flex gap-2">
          <div style="flex:1">
            <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">端口</label>
            <NInputNumber v-model:value="form.port" size="small" placeholder="端口" :min="1" :max="65535" style="width:100%" />
          </div>
          <div style="flex:2">
            <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">数据库名</label>
            <NInput v-model:value="form.database" size="small" placeholder="数据库名" />
          </div>
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">用户名</label>
          <NInput v-model:value="form.username" size="small" placeholder="用户名" />
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">密码</label>
          <NInput v-model:value="form.password" size="small" type="password" :placeholder="editingId ? '留空则不修改密码' : '密码'" />
        </div>
      </template>
      <div class="flex gap-2">
        <NButton size="small" type="primary" :loading="saving" @click="onSave">
          {{ editingId ? '保存修改' : '保存' }}
        </NButton>
        <NButton v-if="!editingId" size="small" @click="onSaveAndTest" :loading="saving">保存并测试</NButton>
        <NButton v-if="editingId" size="small" :loading="saving" @click="onSaveAndTestEdit">保存并测试</NButton>
        <NButton v-if="editingId" size="small" @click="cancelEdit">取消</NButton>
      </div>
      <p v-if="errorMsg" class="text-xs text-red-500 dark:text-red-400 mt-1">{{ errorMsg }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { NButton, NInput, NSelect, NInputNumber, useMessage } from 'naive-ui'
import { useConnectionApi } from '../../composables/useWizardApi'
import type { DbConnectionSummary } from '../../types/wizard'

const message = useMessage()
const api = useConnectionApi()

const connections = ref<DbConnectionSummary[]>([])
const showForm = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)
const errorMsg = ref<string | null>(null)

const dbTypeOptions = [
  { label: 'SQLite', value: 'sqlite' },
  { label: 'MySQL', value: 'mysql' },
  { label: 'PostgreSQL', value: 'postgresql' },
]

const emptyForm = () => ({
  name: '',
  dbType: 'mysql' as string,
  host: 'localhost',
  port: 3306,
  database: '',
  username: 'root',
  password: '',
  filePath: '',
})

const form = reactive(emptyForm())

async function refresh() {
  connections.value = await api.fetchConnections()
}

onMounted(refresh)

function startCreate() {
  if (showForm.value && !editingId.value) {
    showForm.value = false
    return
  }
  editingId.value = null
  Object.assign(form, emptyForm())
  errorMsg.value = null
  showForm.value = true
}

function startEdit(conn: DbConnectionSummary) {
  editingId.value = conn.id
  errorMsg.value = null
  form.name = conn.name
  form.dbType = conn.dbType
  if (conn.dbType === 'sqlite') {
    form.filePath = conn.host
  } else {
    form.host = conn.host
    form.port = conn.port || 3306
    form.database = conn.database || ''
    form.username = conn.username || ''
    form.password = ''
  }
  showForm.value = true
}

async function onSaveAndTestEdit() {
  saving.value = true
  errorMsg.value = null

  const data: Record<string, any> = { name: form.name }
  if (form.dbType === 'sqlite') {
    data.file_path = form.filePath
  } else {
    data.host = form.host
    data.port = form.port
    data.database = form.database
    data.username = form.username
    if (form.password) data.password = form.password
  }
  const result = await api.updateConnection(editingId.value!, data)
  if (!result) {
    errorMsg.value = api.connectionError.value || '更新失败'
    saving.value = false
    return
  }
  const testResult = await api.testConnection(editingId.value!)
  if (testResult.ok) {
    message.success('连接已更新并验证成功')
    cancelEdit()
    await refresh()
  } else {
    message.warning(`连接已更新但验证失败: ${testResult.error}`)
  }
  saving.value = false
}

function cancelEdit() {
  editingId.value = null
  Object.assign(form, emptyForm())
  showForm.value = false
}

async function onSave() {
  saving.value = true
  errorMsg.value = null

  if (editingId.value) {
    const data: Record<string, any> = { name: form.name }
    if (form.dbType === 'sqlite') {
      data.file_path = form.filePath
    } else {
      data.host = form.host
      data.port = form.port
      data.database = form.database
      data.username = form.username
      if (form.password) data.password = form.password
    }
    const result = await api.updateConnection(editingId.value, data)
    if (result) {
      message.success('连接已更新')
      cancelEdit()
      await refresh()
    } else {
      errorMsg.value = api.connectionError.value || '更新失败'
    }
  } else {
    const result = await api.createConnection({ ...form })
    if (result) {
      message.success('连接已保存')
      Object.assign(form, emptyForm())
      showForm.value = false
      await refresh()
    } else {
      errorMsg.value = api.connectionError.value || '保存失败'
    }
  }
  saving.value = false
}

async function onSaveAndTest() {
  saving.value = true
  errorMsg.value = null
  const result = await api.createConnection({ ...form })
  if (!result) {
    errorMsg.value = api.connectionError.value || '保存失败'
    saving.value = false
    return
  }
  const testResult = await api.testConnection(result.id)
  if (testResult.ok) {
    message.success('连接已保存并验证成功')
  } else {
    message.warning(`连接已保存但验证失败: ${testResult.error}`)
  }
  Object.assign(form, emptyForm())
  showForm.value = false
  await refresh()
  saving.value = false
}

async function onTest(id: string) {
  const result = await api.testConnection(id)
  if (result.ok) {
    message.success('连接成功')
    await refresh()
  } else {
    message.error(`连接失败: ${result.error}`)
  }
}

async function onDelete(id: string) {
  const ok = await api.deleteConnection(id)
  if (ok) {
    message.success('连接已删除')
    if (editingId.value === id) cancelEdit()
    await refresh()
  } else {
    message.error(api.connectionError.value || '删除失败')
  }
}
</script>
