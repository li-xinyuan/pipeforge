<template>
  <div>
    <AppNavBar current-route="history" />
    <div class="max-w-4xl mx-auto px-4 py-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold">执行历史</h2>
        <NButton size="small" @click="refresh">刷新</NButton>
      </div>

      <NTabs v-model:value="activeTab" type="line" size="small">
        <NTab name="records">执行记录</NTab>
        <NTab name="trends">诊断趋势</NTab>
      </NTabs>

      <!-- Tab: Execution Records -->
      <div v-if="activeTab === 'records'" class="mt-4">
        <div v-if="loading" class="text-sm text-slate-400 dark:text-slate-500 text-center py-12">加载中...</div>

        <div v-else-if="!executions.length" class="text-sm text-slate-400 dark:text-slate-500 text-center py-12">
          暂无执行记录
        </div>

        <div v-else class="space-y-2">
          <div
            v-for="exec in executions"
            :key="exec.id"
            class="border border-slate-200 dark:border-slate-700 rounded-lg p-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3"
          >
            <NTag size="small" :type="exec.status === 'success' ? 'success' : 'error'">
              {{ exec.status === 'success' ? '成功' : '失败' }}
            </NTag>
            <NTag v-if="exec.diagnosis?.cause" size="small" type="warning">AI 诊断</NTag>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium truncate">{{ exec.scene_name || '未命名' }}</div>
              <div class="text-xs text-slate-400 dark:text-slate-500">
                {{ exec.started_at?.slice(0, 16) || '' }} · {{ exec.duration_ms }}ms
                <span v-if="exec.config_id !== 'adhoc'"> · 配置 {{ exec.config_id?.slice(0, 8) }}</span>
              </div>
            </div>
            <div class="flex items-center gap-1 flex-shrink-0">
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
          <span class="text-xs text-slate-400 dark:text-slate-500">共 {{ total }} 条</span>
          <NPagination
            v-model:page="currentPage"
            :page-count="Math.ceil(total / pageSize)"
            :page-size="pageSize"
            size="small"
            @update:page="refresh"
          />
        </div>
      </div>

      <!-- Tab: Diagnosis Trends -->
      <div v-if="activeTab === 'trends'" class="mt-4">
        <div v-if="loading" class="text-sm text-slate-400 dark:text-slate-500 text-center py-12">加载中...</div>

        <div v-else-if="!trendData.length" class="text-sm text-slate-400 dark:text-slate-500 text-center py-12">
          暂无诊断数据
        </div>

        <div v-else class="space-y-6">
          <!-- Summary cards -->
          <div class="grid grid-cols-3 gap-3">
            <div class="border border-slate-200 dark:border-slate-700 rounded-lg p-3 text-center">
              <div class="text-2xl font-bold text-red-500">{{ failedCount }}</div>
              <div class="text-xs text-slate-400 dark:text-slate-500">失败次数</div>
            </div>
            <div class="border border-slate-200 dark:border-slate-700 rounded-lg p-3 text-center">
              <div class="text-2xl font-bold text-amber-500">{{ diagnosedCount }}</div>
              <div class="text-xs text-slate-400 dark:text-slate-500">已诊断</div>
            </div>
            <div class="border border-slate-200 dark:border-slate-700 rounded-lg p-3 text-center">
              <div class="text-2xl font-bold text-teal-500">{{ diagnosisRate }}%</div>
              <div class="text-xs text-slate-400 dark:text-slate-500">诊断覆盖率</div>
            </div>
          </div>

          <!-- Cause distribution -->
          <div>
            <h3 class="text-sm font-medium mb-3">失败原因分布</h3>
            <div class="space-y-2">
              <div v-for="item in trendData" :key="item.cause" class="flex items-center gap-3">
                <span class="text-xs text-slate-600 dark:text-slate-400 w-48 flex-shrink-0 truncate" :title="item.cause">{{ item.cause }}</span>
                <div class="flex-1 h-5 bg-slate-100 dark:bg-slate-800 rounded overflow-hidden">
                  <div
                    class="h-full rounded"
                    :class="item.severity === 'error' ? 'bg-red-400' : 'bg-amber-400'"
                    :style="{ width: item.pct + '%' }"
                  />
                </div>
                <span class="text-xs font-medium w-12 text-right">{{ item.count }} 次</span>
              </div>
            </div>
          </div>

          <!-- Recent failures timeline -->
          <div>
            <h3 class="text-sm font-medium mb-3">近期失败记录</h3>
            <div class="space-y-1">
              <div
                v-for="exec in recentFailures"
                :key="exec.id"
                class="flex items-center gap-2 text-xs py-1 border-b border-slate-100 dark:border-slate-800"
              >
                <span class="text-slate-400 dark:text-slate-500 w-28 flex-shrink-0">{{ exec.started_at?.slice(0, 16) }}</span>
                <span class="truncate flex-1">{{ exec.scene_name || '未命名' }}</span>
                <span v-if="exec.diagnosis?.cause" class="text-amber-600 dark:text-amber-400 truncate max-w-48">{{ exec.diagnosis.cause }}</span>
                <span v-else class="text-slate-400">未诊断</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Detail modal -->
      <NModal v-model:show="detailVisible" preset="card" title="执行详情" style="max-width: 560px" :trap-focus="true" :auto-focus="true">
        <div v-if="detailRecord" class="p-4 space-y-3 max-w-lg">
          <div class="grid grid-cols-2 gap-2 text-sm">
            <div class="text-slate-400 dark:text-slate-500">执行 ID</div>
            <div class="font-mono">{{ detailRecord.id }}</div>
            <div class="text-slate-400 dark:text-slate-500">场景名称</div>
            <div>{{ detailRecord.scene_name }}</div>
            <div class="text-slate-400 dark:text-slate-500">状态</div>
            <div>
              <NTag size="tiny" :type="detailRecord.status === 'success' ? 'success' : 'error'">
                {{ detailRecord.status === 'success' ? '成功' : '失败' }}
              </NTag>
            </div>
            <div class="text-slate-400 dark:text-slate-500">耗时</div>
            <div>{{ detailRecord.duration_ms }}ms</div>
            <div class="text-slate-400 dark:text-slate-500">输出类型</div>
            <div>{{ detailRecord.output_type || '-' }}</div>
            <div class="text-slate-400 dark:text-slate-500">输入源</div>
            <div>{{ detailRecord.inputs_summary?.length || 0 }} 个</div>
            <div class="text-slate-400 dark:text-slate-500">处理步骤</div>
            <div>{{ detailRecord.processors_summary?.length || 0 }} 个</div>
          </div>
          <div v-if="detailRecord.error_message" class="bg-red-50 dark:bg-red-900/30 border border-red-200 rounded p-2 text-sm text-red-700 dark:text-red-300">
            {{ detailRecord.error_message }}
          </div>
          <DiagnosisPanel
            v-if="detailRecord.diagnosis?.cause"
            :diagnosis="detailRecord.diagnosis"
            :hide-autofix="true"
          />
        </div>
      </NModal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NButton, NTag, NModal, NPagination, NTabs, NTab, useDialog, useMessage } from 'naive-ui'
import AppNavBar from '../components/common/AppNavBar.vue'
import DiagnosisPanel from '../components/common/DiagnosisPanel.vue'

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
  diagnosis?: {
    cause: string
    suggestions: string[]
    severity: 'error' | 'warning'
    step?: number
  } | null
}

const executions = ref<ExecutionSummary[]>([])
const loading = ref(false)
const detailVisible = ref(false)
const detailRecord = ref<ExecutionSummary | null>(null)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const activeTab = ref('records')

// ── Diagnosis trend computed data ──
const failedExecs = computed(() => executions.value.filter(e => e.status === 'failed'))
const failedCount = computed(() => failedExecs.value.length)
const diagnosedCount = computed(() => failedExecs.value.filter(e => e.diagnosis?.cause).length)
const diagnosisRate = computed(() => {
  if (failedCount.value === 0) return 0
  return Math.round((diagnosedCount.value / failedCount.value) * 100)
})

interface TrendItem {
  cause: string
  count: number
  severity: string
  pct: number
}

const trendData = computed<TrendItem[]>(() => {
  const causeMap = new Map<string, { count: number; severity: string }>()
  for (const exec of failedExecs.value) {
    const cause = exec.diagnosis?.cause || '未知原因'
    const sev = exec.diagnosis?.severity || 'error'
    const existing = causeMap.get(cause)
    if (existing) {
      existing.count++
    } else {
      causeMap.set(cause, { count: 1, severity: sev })
    }
  }
  const items = Array.from(causeMap.entries()).map(([cause, data]) => ({
    cause,
    count: data.count,
    severity: data.severity,
    pct: 0,
  }))
  items.sort((a, b) => b.count - a.count)
  const maxCount = items.length > 0 ? items[0].count : 1
  for (const item of items) {
    item.pct = Math.round((item.count / maxCount) * 100)
  }
  return items
})

const recentFailures = computed(() =>
  failedExecs.value.slice(0, 10)
)

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
