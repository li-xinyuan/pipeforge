<template>
  <div>
    <AppNavBar current-route="history" />
    <div class="max-w-4xl mx-auto px-4 py-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold">执行历史</h2>
        <NButton size="small" @click="refresh">刷新</NButton>
      </div>

      <div v-if="loading" class="text-sm text-slate-400 text-center py-12">加载中...</div>

      <div v-else-if="!executions.length" class="text-sm text-slate-400 text-center py-12">
        暂无执行记录
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="exec in executions"
          :key="exec.id"
          class="border border-slate-200 rounded-lg p-3 flex items-center gap-3"
        >
          <NTag size="small" :type="exec.status === 'success' ? 'success' : 'error'">
            {{ exec.status === 'success' ? '成功' : '失败' }}
          </NTag>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium truncate">{{ exec.scene_name || '未命名' }}</div>
            <div class="text-xs text-slate-400">
              {{ exec.started_at?.slice(0, 16) || '' }} · {{ exec.duration_ms }}ms
              <span v-if="exec.config_id !== 'adhoc'"> · 配置 {{ exec.config_id?.slice(0, 8) }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1">
            <NButton size="tiny" quaternary @click="showDetail(exec)">详情</NButton>
            <NButton
              v-if="exec.output_file_name"
              size="tiny"
              quaternary
              type="primary"
              @click="downloadOutput(exec.id)"
            >
              下载
            </NButton>
            <NButton size="tiny" quaternary type="error" @click="confirmDelete(exec)">删除</NButton>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="total > pageSize" class="flex items-center justify-between mt-4">
        <span class="text-xs text-slate-400">共 {{ total }} 条</span>
        <NPagination
          v-model:page="currentPage"
          :page-count="Math.ceil(total / pageSize)"
          :page-size="pageSize"
          size="small"
          @update:page="refresh"
        />
      </div>

      <!-- Detail modal -->
      <NModal v-model:show="detailVisible" preset="card" title="执行详情" style="max-width: 560px">
        <div v-if="detailRecord" class="p-4 space-y-3 max-w-lg">
          <div class="grid grid-cols-2 gap-2 text-sm">
            <div class="text-slate-400">执行 ID</div>
            <div class="font-mono">{{ detailRecord.id }}</div>
            <div class="text-slate-400">场景名称</div>
            <div>{{ detailRecord.scene_name }}</div>
            <div class="text-slate-400">状态</div>
            <div>
              <NTag size="tiny" :type="detailRecord.status === 'success' ? 'success' : 'error'">
                {{ detailRecord.status === 'success' ? '成功' : '失败' }}
              </NTag>
            </div>
            <div class="text-slate-400">耗时</div>
            <div>{{ detailRecord.duration_ms }}ms</div>
            <div class="text-slate-400">输出类型</div>
            <div>{{ detailRecord.output_type || '-' }}</div>
            <div class="text-slate-400">输入源</div>
            <div>{{ detailRecord.inputs_summary?.length || 0 }} 个</div>
            <div class="text-slate-400">处理步骤</div>
            <div>{{ detailRecord.processors_summary?.length || 0 }} 个</div>
          </div>
          <div v-if="detailRecord.error_message" class="bg-red-50 border border-red-200 rounded p-2 text-sm text-red-700">
            {{ detailRecord.error_message }}
          </div>
        </div>
      </NModal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NTag, NModal, NPagination, useDialog, useMessage } from 'naive-ui'
import AppNavBar from '../components/common/AppNavBar.vue'

const dialog = useDialog()
const message = useMessage()

interface ExecutionSummary {
  id: string
  config_id: string
  config_version: number | null
  scene_name: string
  status: 'success' | 'failed'
  started_at: string
  finished_at: string
  duration_ms: number
  inputs_summary: Array<{ name: string; plugin: string }>
  processors_summary: Array<{ plugin: string; name: string }>
  output_type: string
  checks_summary: Array<{ type: string; passed: boolean; message: string }>
  error_message: string | null
  output_file_name: string | null
}

const executions = ref<ExecutionSummary[]>([])
const loading = ref(false)
const detailVisible = ref(false)
const detailRecord = ref<ExecutionSummary | null>(null)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

async function refresh() {
  loading.value = true
  try {
    const resp = await fetch(`/api/executions?page=${currentPage.value}&page_size=${pageSize.value}`)
    if (resp.ok) {
      const data = await resp.json()
      executions.value = Array.isArray(data) ? data : (data.items || [])
      total.value = data.total || executions.value.length
    }
  } finally {
    loading.value = false
  }
}

function showDetail(exec: ExecutionSummary) {
  detailRecord.value = exec
  detailVisible.value = true
}

function downloadOutput(execId: string) {
  window.open(`/api/executions/${execId}/download`, '_blank')
}

function confirmDelete(exec: ExecutionSummary) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除此执行记录吗？输出文件也将被删除。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      const resp = await fetch(`/api/executions/${exec.id}`, { method: 'DELETE' })
      if (resp.ok) {
        message.success('已删除')
        await refresh()
      } else {
        message.error('删除失败')
      }
    },
  })
}

onMounted(refresh)
</script>
