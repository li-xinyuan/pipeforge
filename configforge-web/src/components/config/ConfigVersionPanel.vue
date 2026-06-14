<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold">版本历史</h3>
      <span class="text-xs text-slate-400 dark:text-slate-500">当前版本: v{{ currentVersion }}</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-xs text-slate-400 dark:text-slate-500 text-center py-4">加载中...</div>

    <!-- Empty -->
    <div v-else-if="!versions.length" class="text-xs text-slate-400 dark:text-slate-500 text-center py-4">
      暂无历史版本（首次保存后生成版本记录）
    </div>

    <!-- Version list -->
    <div v-else class="space-y-2 max-h-64 overflow-y-auto">
      <div
        v-for="v in versions"
        :key="v.version"
        class="border rounded-lg p-2 flex items-center gap-3"
        :class="selectedVersion === v.version ? 'border-teal-400 bg-teal-50' : 'border-slate-200 dark:border-slate-700'"
      >
        <div class="flex-1">
          <div class="flex items-center gap-2">
            <NTag size="tiny" :type="v.version === currentVersion ? 'success' : 'default'">
              v{{ v.version }}
            </NTag>
            <span class="text-xs text-slate-500 dark:text-slate-400">{{ v.scene_version }}</span>
            <span v-if="v.change_summary" class="text-xs text-slate-400 dark:text-slate-500">{{ v.change_summary }}</span>
          </div>
          <div class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
            {{ v.input_count }} 输入 · {{ v.processor_count }} 步骤 · {{ v.output_type || '-' }} · {{ v.created_at?.slice(0, 16) || '' }}
          </div>
        </div>
        <div class="flex items-center gap-1">
          <NButton size="tiny" quaternary @click="viewVersion(v.version)">查看</NButton>
          <NButton size="tiny" quaternary type="warning" @click="confirmRollback(v.version)">回滚</NButton>
        </div>
      </div>
    </div>

    <!-- Version detail preview -->
    <div v-if="versionDetail" class="border-t pt-3">
      <div class="flex items-center justify-between mb-2">
        <h4 class="text-xs font-semibold">v{{ selectedVersion }} 配置详情</h4>
        <NButton size="tiny" quaternary @click="versionDetail = null; selectedVersion = null">关闭</NButton>
      </div>
      <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3 max-h-48 overflow-y-auto text-xs space-y-1">
        <div><span class="text-slate-400 dark:text-slate-500">场景:</span> {{ versionDetail.scene?.name || '-' }}</div>
        <div><span class="text-slate-400 dark:text-slate-500">版本:</span> {{ versionDetail.scene?.version || '-' }}</div>
        <div><span class="text-slate-400 dark:text-slate-500">输入源:</span> {{ versionDetail.inputs?.length || 0 }} 个</div>
        <div v-for="(inp, i) in versionDetail.inputs" :key="i" class="ml-3 text-slate-500 dark:text-slate-400">
          {{ i + 1 }}. {{ inp.table || inp.name || '-' }} ({{ inp.plugin }})
        </div>
        <div><span class="text-slate-400 dark:text-slate-500">处理步骤:</span> {{ versionDetail.processors?.length || 0 }} 个</div>
        <div v-for="(proc, i) in versionDetail.processors" :key="i" class="ml-3 text-slate-500 dark:text-slate-400">
          {{ i + 1 }}. {{ proc.name || proc.plugin || '-' }} ({{ proc.plugin }})
        </div>
        <div><span class="text-slate-400 dark:text-slate-500">输出:</span> {{ versionDetail.output?.plugin || '-' }}</div>
      </div>
    </div>

    <!-- Diff section -->
    <div v-if="versions.length >= 2" class="border-t pt-3">
      <h4 class="text-xs font-semibold mb-2">版本对比</h4>
      <div class="flex items-center gap-2">
        <NSelect
          v-model:value="diffV1"
          :options="versionOptions"
          size="small"
          style="width: 110px"
          placeholder="v1"
        />
        <span class="text-xs text-slate-400 dark:text-slate-500">vs</span>
        <NSelect
          v-model:value="diffV2"
          :options="versionOptions"
          size="small"
          style="width: 110px"
          placeholder="v2"
        />
        <NButton size="tiny" :disabled="!diffV1 || !diffV2" @click="doDiff">对比</NButton>
      </div>

      <!-- Diff results -->
      <div v-if="diffResult" class="mt-2 max-h-48 overflow-y-auto">
        <div v-if="!diffResult.changes?.length" class="text-xs text-slate-400 dark:text-slate-500 text-center py-2">
          两个版本无差异
        </div>
        <div
          v-for="(change, i) in (diffResult.changes || [])"
          :key="i"
          class="text-xs py-1 border-b border-slate-100 dark:border-slate-700 last:border-0"
        >
          <NTag size="tiny" :type="change.type === 'added' ? 'success' : change.type === 'removed' ? 'error' : 'warning'">
            {{ change.type === 'added' ? '新增' : change.type === 'removed' ? '删除' : '修改' }}
          </NTag>
          <code class="ml-1 text-xs break-all">{{ change.path }}</code>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { NButton, NTag, NSelect, useDialog, useMessage } from 'naive-ui'

const props = defineProps<{
  configId: string
  currentVersion: number
}>()

const emit = defineEmits<{
  refreshed: []
}>()

const dialog = useDialog()
const message = useMessage()

interface VersionMeta {
  version: number
  scene_version: string
  change_summary: string
  created_at: string
  input_count: number
  processor_count: number
  output_type: string
}

const versions = ref<VersionMeta[]>([])
const loading = ref(false)
const selectedVersion = ref<number | null>(null)
const versionDetail = ref<any>(null)
const diffV1 = ref<number | null>(null)
const diffV2 = ref<number | null>(null)
const diffResult = ref<any>(null)

const versionOptions = computed(() =>
  versions.value.map(v => ({ label: `v${v.version}`, value: v.version }))
)

async function loadVersions() {
  loading.value = true
  try {
    const resp = await fetch(`/api/configs/${props.configId}/versions`)
    if (resp.ok) versions.value = await resp.json()
  } finally {
    loading.value = false
  }
}

async function viewVersion(version: number) {
  selectedVersion.value = version
  versionDetail.value = null
  try {
    const resp = await fetch(`/api/configs/${props.configId}/versions/${version}`)
    if (resp.ok) versionDetail.value = await resp.json()
  } catch {
    message.error('加载版本详情失败')
  }
}

async function doDiff() {
  if (!diffV1.value || !diffV2.value) return
  try {
    const resp = await fetch(`/api/configs/${props.configId}/diff?v1=${diffV1.value}&v2=${diffV2.value}`)
    if (resp.ok) diffResult.value = await resp.json()
  } catch {
    message.error('版本对比失败')
  }
}

function confirmRollback(version: number) {
  dialog.warning({
    title: '确认回滚',
    content: `确定要回滚到 v${version} 吗？当前配置将被保存为历史版本，v${version} 的内容将成为当前版本。`,
    positiveText: '回滚',
    negativeText: '取消',
    onPositiveClick: () => doRollback(version),
  })
}

async function doRollback(version: number) {
  try {
    const resp = await fetch(`/api/configs/${props.configId}/versions/${version}/rollback`, { method: 'POST' })
    if (resp.ok) {
      message.success(`已回滚到 v${version}`)
      await loadVersions()
      emit('refreshed')
    } else {
      message.error('回滚失败')
    }
  } catch {
    message.error('回滚请求失败')
  }
}

onMounted(loadVersions)
</script>
