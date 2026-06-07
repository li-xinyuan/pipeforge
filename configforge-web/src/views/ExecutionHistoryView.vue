<template>
  <div>
    <AppNavBar current-route="history" />
    <div class="max-w-4xl mx-auto px-4 py-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold">执行历史</h2>
        <div class="flex items-center gap-3">
          <NInput
            v-model:value="searchQuery"
            size="small"
            placeholder="搜索场景名称..."
            clearable
            style="width: 200px"
            @update:value="onSearchChange"
          />
          <NButton size="small" @click="refresh">刷新</NButton>
        </div>
      </div>

      <div v-if="loading" class="text-sm text-slate-400 text-center py-12">加载中...</div>

      <div v-else-if="!executions.items.length" class="text-center py-16">
        <p class="text-4xl mb-4">📜</p>
        <p class="text-base font-medium text-slate-600 mb-2">暂无执行记录</p>
        <p class="text-sm text-slate-400">
          创建配置并执行后，执行记录将显示在这里
        </p>
        <NButton size="small" class="mt-4" @click="router.push('/')">前往我的配置</NButton>
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="exec in executions.items"
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
      <div v-if="executions.total_pages > 1" class="flex items-center justify-center gap-4 mt-5">
        <NButton size="small" :disabled="executions.page <= 1" @click="goToPage(executions.page - 1)">← 上一页</NButton>
        <span class="text-sm text-slate-400">第 {{ executions.page }}/{{ executions.total_pages }} 页</span>
        <NButton size="small" :disabled="executions.page >= executions.total_pages" @click="goToPage(executions.page + 1)">下一页 →</NButton>
      </div>

      <!-- Detail modal -->
      <NModal v-model:show="detailVisible" title="执行详情">
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
import { useRouter } from 'vue-router'
import { NButton, NInput, NTag, NModal, useDialog, useMessage } from 'naive-ui'
import AppNavBar from '../components/common/AppNavBar.vue'

const router = useRouter()
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

interface PaginatedExecutions {
  items: ExecutionSummary[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

const executions = ref<PaginatedExecutions>({ items: [], total: 0, page: 1, page_size: 10, total_pages: 1 })
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
let searchTimer: ReturnType<typeof setTimeout> | null = null
const detailVisible = ref(false)
const detailRecord = ref<ExecutionSummary | null>(null)

async function refresh() {
  loading.value = true
  try {
    const query = new URLSearchParams()
    if (searchQuery.value) query.set('search', searchQuery.value)
    query.set('page', String(currentPage.value))
    query.set('page_size', '10')
    const qs = query.toString()
    const resp = await fetch('/api/executions' + (qs ? '?' + qs : ''))
    if (resp.ok) executions.value = await resp.json()
  } finally {
    loading.value = false
  }
}

function goToPage(page: number) {
  currentPage.value = page
  refresh()
}

function onSearchChange() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    refresh()
  }, 300)
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
