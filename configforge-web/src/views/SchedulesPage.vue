<template>
  <div>
    <AppNavBar current-route="schedules" />
    <div class="max-w-4xl mx-auto px-4 py-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold">定时任务</h2>
        <NButton type="primary" size="small" @click="showAddModal = true">新建定时任务</NButton>
      </div>

      <div v-if="loading" class="text-sm text-slate-400 dark:text-slate-500 text-center py-12">加载中...</div>

      <div v-else-if="!schedules.length" class="text-sm text-slate-400 dark:text-slate-500 text-center py-12">
        暂无定时任务，点击上方按钮创建
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="s in schedules"
          :key="s.id"
          class="border border-slate-200 dark:border-slate-700 rounded-lg p-4"
        >
          <div class="flex items-center justify-between flex-wrap gap-2">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-sm font-medium">{{ s.config_name || '未知配置' }}</span>
                <NTag size="small" :type="s.enabled ? 'success' : 'default'">
                  {{ s.enabled ? '已启用' : '已禁用' }}
                </NTag>
                <NTag v-if="s.last_run_status" size="small" :type="s.last_run_status === 'success' ? 'success' : 'error'">
                  上次: {{ s.last_run_status === 'success' ? '成功' : '失败' }}
                </NTag>
              </div>
              <div class="text-xs text-slate-400 dark:text-slate-500 space-y-0.5">
                <div>Cron: <code class="bg-slate-100 dark:bg-slate-700 px-1 rounded">{{ s.cron_expression }}</code></div>
                <div v-if="s.description" class="text-slate-500 dark:text-slate-400">{{ s.description }}</div>
                <div v-if="s.next_run_time">下次运行: {{ formatTime(s.next_run_time) }}</div>
                <div v-if="s.last_run_at">上次运行: {{ formatTime(s.last_run_at) }}</div>
              </div>
            </div>
            <div class="flex items-center gap-1 ml-0 sm:ml-4 flex-shrink-0">
              <NButton size="tiny" quaternary @click="openEditModal(s)">编辑</NButton>
              <NButton size="tiny" quaternary :type="s.enabled ? 'warning' : 'success'" @click="onToggle(s)">
                {{ s.enabled ? '禁用' : '启用' }}
              </NButton>
              <NButton size="tiny" quaternary type="error" @click="confirmDelete(s)">删除</NButton>
            </div>
          </div>
        </div>
      </div>

      <!-- Add schedule modal -->
      <NModal v-model:show="showAddModal" preset="card" title="新建定时任务" style="max-width: 440px" :trap-focus="true" :auto-focus="true">
        <div class="space-y-4">
          <div>
            <div class="text-sm font-medium mb-1">选择配置</div>
            <NSelect
              v-model:value="addForm.config_id"
              :options="configOptions"
              placeholder="请选择一个配置"
            />
          </div>
          <div>
            <div class="text-sm font-medium mb-1">Cron 表达式</div>
            <NInput v-model:value="addForm.cron_expression" placeholder="0 8 * * *（每天 8:00）" />
            <div class="text-xs text-slate-400 dark:text-slate-500 mt-1">格式: 分 时 日 月 周，例如 0 8 * * *</div>
          </div>
          <div>
            <div class="text-sm font-medium mb-1">描述</div>
            <NInput v-model:value="addForm.description" placeholder="可选，描述此定时任务" />
          </div>
        </div>
        <template #footer>
          <div class="flex gap-2 justify-end">
            <NButton @click="showAddModal = false">取消</NButton>
            <NButton type="primary" :loading="submitting" @click="onAddSchedule">创建</NButton>
          </div>
        </template>
      </NModal>

      <!-- Edit schedule modal -->
      <NModal v-model:show="showEditModal" preset="card" title="编辑定时任务" style="max-width: 440px" :trap-focus="true" :auto-focus="true">
        <div v-if="editingSchedule" class="space-y-4">
          <div>
            <div class="text-sm font-medium mb-1">配置</div>
            <div class="text-sm text-slate-500 dark:text-slate-400">{{ editingSchedule.config_name }}</div>
          </div>
          <div>
            <div class="text-sm font-medium mb-1">Cron 表达式</div>
            <NInput v-model:value="editForm.cron_expression" />
            <div class="text-xs text-slate-400 mt-1">格式: 分 时 日 月 周</div>
          </div>
          <div>
            <div class="text-sm font-medium mb-1">描述</div>
            <NInput v-model:value="editForm.description" />
          </div>
        </div>
        <template #footer>
          <div class="flex gap-2 justify-end">
            <NButton @click="showEditModal = false">取消</NButton>
            <NButton type="primary" :loading="submitting" @click="onUpdateSchedule">保存</NButton>
          </div>
        </template>
      </NModal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NTag, NModal, NSelect, NInput, useDialog, useMessage } from 'naive-ui'
import AppNavBar from '../components/common/AppNavBar.vue'

const dialog = useDialog()
const message = useMessage()

interface ScheduleItem {
  id: string
  config_id: string
  config_name: string
  cron_expression: string
  enabled: boolean
  description: string
  created_at: string
  last_run_at: string | null
  last_run_status: string | null
  next_run_time: string | null
}

interface ConfigOption {
  label: string
  value: string
  hasFileInput?: boolean
}

const schedules = ref<ScheduleItem[]>([])
const configOptions = ref<ConfigOption[]>([])
const loading = ref(false)
const submitting = ref(false)

const showAddModal = ref(false)
const addForm = ref({ config_id: '', cron_expression: '', description: '' })

const showEditModal = ref(false)
const editingSchedule = ref<ScheduleItem | null>(null)
const editForm = ref({ cron_expression: '', description: '' })

async function refresh() {
  loading.value = true
  try {
    const [schedResp, configResp] = await Promise.all([
      fetch('/api/schedules'),
      fetch('/api/configs?page_size=100'),
    ])
    if (schedResp.ok) schedules.value = await schedResp.json()
    if (configResp.ok) {
      const data = await configResp.json()
      configOptions.value = (data.items || []).map((c: Record<string, unknown>) => ({
        label: (c.scene_name || '未命名') as string,
        value: c.id as string,
        hasFileInput: ((c.inputs || []) as Record<string, unknown>[]).some((inp) => inp.plugin !== 'database'),
      }))
    }
  } finally {
    loading.value = false
  }
}

function openEditModal(s: ScheduleItem) {
  editingSchedule.value = s
  editForm.value = { cron_expression: s.cron_expression, description: s.description }
  showEditModal.value = true
}

async function onAddSchedule() {
  if (!addForm.value.config_id) {
    message.warning('请选择配置')
    return
  }
  if (!addForm.value.cron_expression.trim()) {
    message.warning('请输入 Cron 表达式')
    return
  }
  // Check if selected config has file-based inputs (Excel/CSV)
  const selectedConfig = configOptions.value.find(c => c.value === addForm.value.config_id)
  if (selectedConfig?.hasFileInput) {
    dialog.warning({
      title: '该配置包含文件输入源',
      content: '此配置包含 Excel/CSV 文件输入源，定时任务执行时无法自动上传文件，会导致执行失败。仅建议为纯数据库输入源的配置创建定时任务。是否仍要继续？',
      positiveText: '仍然创建',
      negativeText: '取消',
      onPositiveClick: () => doAddSchedule(),
    })
    return
  }
  await doAddSchedule()
}

async function doAddSchedule() {
  submitting.value = true
  try {
    const resp = await fetch('/api/schedules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(addForm.value),
    })
    if (resp.ok) {
      message.success('定时任务已创建')
      showAddModal.value = false
      addForm.value = { config_id: '', cron_expression: '', description: '' }
      await refresh()
    } else {
      const err = await resp.json()
      message.error(err.detail || '创建失败')
    }
  } finally {
    submitting.value = false
  }
}

async function onUpdateSchedule() {
  if (!editingSchedule.value) return
  submitting.value = true
  try {
    const resp = await fetch(`/api/schedules/${editingSchedule.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editForm.value),
    })
    if (resp.ok) {
      message.success('已更新')
      showEditModal.value = false
      await refresh()
    } else {
      const err = await resp.json()
      message.error(err.detail || '更新失败')
    }
  } finally {
    submitting.value = false
  }
}

async function onToggle(s: ScheduleItem) {
  const resp = await fetch(`/api/schedules/${s.id}/toggle`, { method: 'POST' })
  if (resp.ok) {
    message.success(s.enabled ? '已禁用' : '已启用')
    await refresh()
  } else {
    message.error('操作失败')
  }
}

function confirmDelete(s: ScheduleItem) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除此定时任务吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      const resp = await fetch(`/api/schedules/${s.id}`, { method: 'DELETE' })
      if (resp.ok) {
        message.success('已删除')
        await refresh()
      } else {
        message.error('删除失败')
      }
    },
  })
}

function formatTime(iso: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

onMounted(refresh)
</script>
