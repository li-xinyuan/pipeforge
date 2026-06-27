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
      <div v-if="diffResult" class="mt-2 max-h-72 overflow-y-auto">
        <div v-if="totalDiffCount === 0" class="text-xs text-slate-400 dark:text-slate-500 text-center py-2">
          两个版本无差异
        </div>

        <!-- Diff tree grouped by top-level path -->
        <div v-else class="space-y-1">
          <div
            v-for="group in diffGroups"
            :key="group.name"
            class="border rounded border-slate-200 dark:border-slate-700"
          >
            <!-- Group header -->
            <div
              class="flex items-center gap-1.5 px-2 py-1.5 cursor-pointer select-none hover:bg-slate-50 dark:hover:bg-slate-700/50"
              @click="toggleGroup(group.name)"
            >
              <span class="text-xs transition-transform" :class="expandedGroups[group.name] ? 'rotate-90' : ''">&#9654;</span>
              <span class="text-xs font-medium">{{ group.name }}</span>
              <span class="text-xs text-slate-400 dark:text-slate-500">
                ({{ group.items.length }})
              </span>
              <span v-if="group.addedCount" class="text-xs text-emerald-600 dark:text-emerald-400 ml-1">+{{ group.addedCount }}</span>
              <span v-if="group.removedCount" class="text-xs text-red-500 dark:text-red-400 ml-1">-{{ group.removedCount }}</span>
              <span v-if="group.modifiedCount" class="text-xs text-amber-600 dark:text-amber-400 ml-1">~{{ group.modifiedCount }}</span>
            </div>

            <!-- Group items -->
            <div v-if="expandedGroups[group.name]" class="px-2 pb-2 space-y-0.5">
              <!-- Added items -->
              <div
                v-for="(item, i) in group.added"
                :key="'a' + i"
                class="text-xs py-1 px-2 rounded bg-emerald-50 dark:bg-emerald-900/20 border-l-2 border-emerald-400"
              >
                <NTag size="tiny" type="success">新增</NTag>
                <code class="ml-1 break-all">{{ item.path }}</code>
                <div v-if="item.value !== null && item.value !== undefined" class="ml-10 mt-0.5 text-emerald-700 dark:text-emerald-300">
                  <span class="text-slate-400 dark:text-slate-500">值: </span>
                  <span class="break-all">{{ formatValue(item.value) }}</span>
                </div>
              </div>

              <!-- Removed items -->
              <div
                v-for="(item, i) in group.removed"
                :key="'r' + i"
                class="text-xs py-1 px-2 rounded bg-red-50 dark:bg-red-900/20 border-l-2 border-red-400"
              >
                <NTag size="tiny" type="error">删除</NTag>
                <code class="ml-1 break-all line-through text-red-600 dark:text-red-400">{{ item.path }}</code>
                <div v-if="item.value !== null && item.value !== undefined" class="ml-10 mt-0.5 text-red-600 dark:text-red-400 line-through">
                  <span class="text-slate-400 dark:text-slate-500 no-underline">值: </span>
                  <span class="break-all">{{ formatValue(item.value) }}</span>
                </div>
              </div>

              <!-- Modified items -->
              <div
                v-for="(item, i) in group.modified"
                :key="'m' + i"
                class="text-xs py-1 px-2 rounded bg-amber-50 dark:bg-amber-900/20 border-l-2 border-amber-400"
              >
                <NTag size="tiny" type="warning">修改</NTag>
                <code class="ml-1 break-all">{{ item.path }}</code>
                <div class="ml-10 mt-0.5 flex items-center gap-1 flex-wrap">
                  <span class="text-red-500 dark:text-red-400 line-through break-all">{{ formatValue(item.old) }}</span>
                  <span class="text-slate-400 dark:text-slate-500">&rarr;</span>
                  <span class="text-emerald-600 dark:text-emerald-400 break-all">{{ formatValue(item.new) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue'
import { NButton, NTag, NSelect, useDialog, useMessage } from 'naive-ui'
import { useApi, type VersionMeta, type DiffResult } from '../../composables/useApi'

const props = defineProps<{
  configId: string
  currentVersion: number
}>()

const emit = defineEmits<{
  refreshed: []
}>()

const dialog = useDialog()
const message = useMessage()
const { getConfigVersions, getConfigVersionDetail, getConfigDiff, rollbackConfig } = useApi()

interface VersionDetail {
  scene?: { name?: string; version?: string }
  inputs?: Array<{ table?: string; name?: string; plugin: string }>
  processors?: Array<{ name?: string; plugin: string }>
  output?: { plugin?: string }
}

const versions = ref<VersionMeta[]>([])
const loading = ref(false)
const selectedVersion = ref<number | null>(null)
const versionDetail = ref<VersionDetail | null>(null)
const diffV1 = ref<number | null>(null)
const diffV2 = ref<number | null>(null)
const diffResult = ref<DiffResult | null>(null)
const expandedGroups = reactive<Record<string, boolean>>({})

const versionOptions = computed(() =>
  versions.value.map(v => ({ label: `v${v.version}`, value: v.version }))
)

interface DiffGroup {
  name: string
  added: Array<{ path: string; value: unknown }>
  removed: Array<{ path: string; value: unknown }>
  modified: Array<{ path: string; old: unknown; new: unknown }>
  items: Array<{ path: string; type: 'added' | 'removed' | 'modified' }>
  addedCount: number
  removedCount: number
  modifiedCount: number
}

const diffGroups = computed<DiffGroup[]>(() => {
  if (!diffResult.value) return []
  const map = new Map<string, DiffGroup>()

  const getGroup = (path: string): DiffGroup => {
    const topKey = path.split('.')[0].split('[')[0] || path
    if (!map.has(topKey)) {
      map.set(topKey, {
        name: topKey,
        added: [],
        removed: [],
        modified: [],
        items: [],
        addedCount: 0,
        removedCount: 0,
        modifiedCount: 0,
      })
    }
    return map.get(topKey)!
  }

  for (const item of diffResult.value.added || []) {
    const g = getGroup(item.path)
    g.added.push(item)
    g.items.push({ path: item.path, type: 'added' })
    g.addedCount++
  }
  for (const item of diffResult.value.removed || []) {
    const g = getGroup(item.path)
    g.removed.push(item)
    g.items.push({ path: item.path, type: 'removed' })
    g.removedCount++
  }
  for (const item of diffResult.value.modified || []) {
    const g = getGroup(item.path)
    g.modified.push(item)
    g.items.push({ path: item.path, type: 'modified' })
    g.modifiedCount++
  }

  return Array.from(map.values())
})

const totalDiffCount = computed(() => {
  if (!diffResult.value) return 0
  return (diffResult.value.added?.length || 0)
    + (diffResult.value.removed?.length || 0)
    + (diffResult.value.modified?.length || 0)
})

function toggleGroup(name: string) {
  expandedGroups[name] = !expandedGroups[name]
}

function formatValue(val: unknown): string {
  if (val === null) return 'null'
  if (val === undefined) return 'undefined'
  if (typeof val === 'object') {
    try {
      return JSON.stringify(val, null, 2)
    } catch {
      return String(val)
    }
  }
  return String(val)
}

async function loadVersions() {
  loading.value = true
  try {
    const data = await getConfigVersions(props.configId)
    if (data) versions.value = data
  } finally {
    loading.value = false
  }
}

async function viewVersion(version: number) {
  selectedVersion.value = version
  versionDetail.value = null
  try {
    const data = await getConfigVersionDetail(props.configId, version)
    if (data) versionDetail.value = data
  } catch {
    message.error('加载版本详情失败')
  }
}

async function doDiff() {
  if (!diffV1.value || !diffV2.value) return
  try {
    const data = await getConfigDiff(props.configId, diffV1.value, diffV2.value)
    if (data) {
      diffResult.value = data
      // Auto-expand all groups
      for (const key of Object.keys(expandedGroups)) {
        delete expandedGroups[key]
      }
      for (const group of diffGroups.value) {
        expandedGroups[group.name] = true
      }
    }
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
    const result = await rollbackConfig(props.configId, version)
    if (result) {
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
