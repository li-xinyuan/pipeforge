<template>
  <div class="home">
    <AppNavBar current-route="home" />

    <AiStatusBanner />

    <!-- Hero: show when no configs OR user explicitly wants intro -->
    <Transition name="home-fade">
      <section v-if="!loading && (totalCount === 0 || showIntro)" class="home__hero">
        <div class="home__hero-inner">
          <div class="home__hero-badge">⚡ AI 驱动的数据流水线配置工具</div>
          <h1 class="home__hero-title">
            用自然语言描述需求<br>
            <span class="home__hero-gradient">AI 自动生成配置</span>
          </h1>
          <p class="home__hero-subtitle">
            5 步向导帮你把数据处理需求变成可运行的配置文件。支持 AI 辅助 SQL 生成与列映射，所有数据本地处理，不上传至外部服务。
          </p>
          <div class="home__hero-anim">
            <PipelineAnimation />
          </div>
          <div class="home__hero-actions">
            <NButton type="primary" size="large" class="btn-primary" @click="startNewConfig">
              ✏ 开始新配置
            </NButton>
            <NButton size="large" class="btn-secondary" @click="router.push('/guide')">
              📖 使用指南
            </NButton>
          </div>
          <div class="home__prompt-chips">
            <span class="home__prompt-label">试试这样说</span>
            <button class="home__prompt-chip" @click="startWithPrompt('把用户表的 ID、名称和邮箱导出到 CSV')">把用户表的 ID、名称和邮箱导出到 CSV</button>
            <button class="home__prompt-chip" @click="startWithPrompt('合并订单表和用户表，按城市统计订单金额')">合并订单表和用户表，按城市统计订单金额</button>
            <button class="home__prompt-chip" @click="startWithPrompt('从 API 获取天气数据，清洗后写入数据库')">从 API 获取天气数据，清洗后写入数据库</button>
          </div>
          <button v-if="totalCount > 0" class="home__hero-back" @click="showIntro = false">← 返回配置列表</button>
        </div>
      </section>
    </Transition>

    <!-- Compact toolbar when configs exist and not showing intro -->
    <Transition name="home-fade">
      <section v-if="!loading && totalCount > 0 && !showIntro" class="home__toolbar">
        <div class="home__toolbar-inner">
          <div class="home__toolbar-left">
            <span class="home__toolbar-brand">⚡ ConfigForge</span>
            <span class="home__toolbar-sep"></span>
            <button class="home__toolbar-intro-link" @click="showIntro = true">查看介绍</button>
          </div>
          <div class="home__toolbar-actions">
            <NButton type="primary" size="small" class="btn-primary" @click="startNewConfig">✏ 新建配置</NButton>
            <NButton size="small" class="btn-secondary" @click="router.push('/guide')">📖 指南</NButton>
          </div>
        </div>
      </section>
    </Transition>

    <!-- Config list section -->
    <section class="home__configs" :class="{ 'home__configs--full': totalCount > 0 }">
      <div class="home__configs-header">
        <div class="home__configs-header-left">
          <h2 class="home__configs-title">最近配置</h2>
          <NTag v-if="totalCount > 0" size="small" :bordered="false" class="home__configs-count">{{ totalCount }} 个配置</NTag>
        </div>
        <div v-if="totalCount > 0 || searchQuery" class="home__configs-header-right">
          <NInput
            v-model:value="searchQuery"
            placeholder="搜索配置名称..."
            aria-label="搜索配置名称"
            size="small"
            clearable
            class="home__search-input"
            @update:value="onSearch"
          >
            <template #prefix>
              <span style="color: var(--color-text-muted);">🔍</span>
            </template>
          </NInput>
          <NButton v-if="!batchMode" size="small" @click="enterBatchMode">批量管理</NButton>
          <NButton v-else size="small" @click="exitBatchMode">取消</NButton>
        </div>
      </div>

      <div v-if="loading" class="home__skeleton">
        <div v-for="n in 3" :key="n" class="home__skeleton-card" />
      </div>

      <NAlert v-else-if="error" type="error" :title="error" />

      <div v-else-if="configs.length > 0" class="home__config-list">
        <!-- Batch action bar -->
        <div v-if="batchMode" class="home__batch-bar">
          <NCheckbox :checked="isAllSelected" :indeterminate="isSomeSelected && !isAllSelected" @update:checked="toggleSelectAll">全选</NCheckbox>
          <span class="home__batch-count">已选 {{ selectedIds.size }} 项</span>
          <NButton size="small" type="error" :disabled="selectedIds.size === 0" :loading="batchDeleting" @click="onBatchDelete">删除选中</NButton>
        </div>

        <div v-for="cfg in configs" :key="cfg.id" class="home__config-card card-lift" :class="{ 'home__config-card--selected': batchMode && selectedIds.has(cfg.id) }">
          <NCheckbox v-if="batchMode" :checked="selectedIds.has(cfg.id)" @update:checked="toggleSelect(cfg.id)" class="home__config-card-check" />
          <div class="home__config-card-left">
            <span class="home__config-card-icon">📋</span>
            <div class="home__config-card-info">
              <router-link :to="batchMode ? '' : '/config/new?load=' + cfg.id" class="config-name-link" :class="{ 'config-name-link--disabled': batchMode }">{{ cfg.sceneName }}</router-link>
              <div class="home__config-card-meta">
                <span class="home__meta-item">{{ cfg.version }}</span>
                <span class="home__meta-sep">·</span>
                <span class="home__meta-item">{{ cfg.inputCount }} 个数据源</span>
                <span class="home__meta-sep">·</span>
                <span class="home__meta-item">{{ cfg.outputType }}</span>
                <span class="home__meta-sep">·</span>
                <span class="home__meta-item">{{ formatTime(cfg.updatedAt) }}</span>
              </div>
            </div>
          </div>
          <div v-if="!batchMode" class="home__config-card-right">
            <NButton v-if="cfg.inputCount > 0" size="small" secondary type="primary" @click.stop="openExecuteModal(cfg)">执行</NButton>
            <NDropdown trigger="click" :options="getMenuOptions(cfg)" @select="(key: string) => onMenuSelect(key, cfg)">
              <NButton text size="tiny" class="home__menu-btn" style="min-width: 44px; min-height: 44px;" aria-label="更多操作">···</NButton>
            </NDropdown>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="home__pagination">
          <NButton size="small" :disabled="currentPage <= 1" @click="onPageChange(currentPage - 1)">← 上一页</NButton>
          <span class="home__pagination-info">{{ currentPage }} / {{ totalPages }}</span>
          <NButton size="small" :disabled="currentPage >= totalPages" @click="onPageChange(currentPage + 1)">下一页 →</NButton>
          <span class="home__pagination-sep"></span>
          <NSelect v-model:value="pageSize" :options="pageSizeOptions" size="small" class="home__page-size-select" @update:value="onPageSizeChange" />
          <span class="home__pagination-sep"></span>
          <span class="home__pagination-jump">
            跳至
            <NInput v-model:value="jumpPage" size="small" class="home__jump-input" @keyup.enter="onJumpPage" />
            页
          </span>
        </div>
      </div>

      <div v-else style="text-align: center; padding: 40px 20px; color: var(--color-text-muted);">
        <p style="font-size: 48px; margin-bottom: 12px;">📋</p>
        <p v-if="searchQuery" style="font-size: var(--font-size-base); font-weight: 500; margin-bottom: 8px;">没有找到匹配的配置</p>
        <template v-else>
          <p style="font-size: var(--font-size-base); font-weight: 500; margin-bottom: 8px;">还没有配置</p>
          <p style="font-size: var(--font-size-sm);">点击上方按钮开始创建你的第一个数据管道配置</p>
        </template>
      </div>
    </section>

    <!-- 删除确认弹窗 -->
    <NModal v-model:show="deleteModalVisible" preset="card" title="确认删除" style="max-width: 400px" :trap-focus="true" :auto-focus="true">
      <p class="text-sm text-slate-600 dark:text-slate-300 mb-0">
        确定要删除配置 "<strong>{{ deletingConfig?.sceneName }}</strong>" 吗？此操作不可撤销。
      </p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <NButton @click="deleteModalVisible = false">取消</NButton>
          <NButton type="error" :loading="deleting" @click="onConfirmDelete">删除</NButton>
        </div>
      </template>
    </NModal>

    <!-- 批量删除确认弹窗 -->
    <NModal v-model:show="batchDeleteModalVisible" preset="card" title="确认批量删除" style="max-width: 400px" :trap-focus="true" :auto-focus="true">
      <p class="text-sm text-slate-600 dark:text-slate-300 mb-0">
        确定要删除选中的 <strong>{{ selectedIds.size }}</strong> 个配置吗？此操作不可撤销。
      </p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <NButton @click="batchDeleteModalVisible = false">取消</NButton>
          <NButton type="error" :loading="batchDeleting" @click="onConfirmBatchDelete">删除</NButton>
        </div>
      </template>
    </NModal>

    <!-- 执行弹窗 -->
    <ExecuteConfigModal
      :visible="executeModalVisible"
      :config="executingConfig"
      @close="executeModalVisible = false"
    />

    <!-- 版本历史弹窗 -->
    <NModal v-model:show="versionModalVisible" preset="card" title="版本历史" style="max-width: 520px" :trap-focus="true" :auto-focus="true">
      <ConfigVersionPanel
        v-if="versionModalConfigId"
        :config-id="versionModalConfigId"
        :current-version="0"
        @refreshed="onVersionRefreshed"
      />
      <template #footer>
        <NButton @click="versionModalVisible = false">关闭</NButton>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useConfigApi } from '../composables/useConfigApi'
import { useWizardStore } from '../stores/wizard'
import type { SavedConfig } from '../types/wizard'
import { NButton, NAlert, NModal, NTag, NDropdown, NInput, NCheckbox, NSelect, useMessage } from 'naive-ui'
import AppNavBar from '../components/common/AppNavBar.vue'
import ExecuteConfigModal from '../components/ExecuteConfigModal.vue'
import ConfigVersionPanel from '../components/config/ConfigVersionPanel.vue'
import AiStatusBanner from '../components/AiStatusBanner.vue'
import PipelineAnimation from '../components/PipelineAnimation.vue'

const router = useRouter()
const store = useWizardStore()
const message = useMessage()
const { listConfigs, deleteConfig, downloadConfigYaml } = useConfigApi()

const loading = ref(true)
const error = ref('')
const configs = ref<SavedConfig[]>([])
const totalCount = ref(0)
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = ref(10)
const pageSizeOptions = [
  { label: '10 条/页', value: 10 },
  { label: '20 条/页', value: 20 },
  { label: '50 条/页', value: 50 },
]
const jumpPage = ref('')
const searchQuery = ref('')
const showIntro = ref(false)

const deleteModalVisible = ref(false)
const deletingConfig = ref<SavedConfig | null>(null)
const deleting = ref(false)

const executeModalVisible = ref(false)
const executingConfig = ref<SavedConfig | null>(null)

const versionModalVisible = ref(false)
const versionModalConfigId = ref<string | null>(null)

// Batch mode
const batchMode = ref(false)
const selectedIds = ref<Set<string>>(new Set())
const batchDeleteModalVisible = ref(false)
const batchDeleting = ref(false)

const isAllSelected = computed(() => configs.value.length > 0 && configs.value.every(c => selectedIds.value.has(c.id)))
const isSomeSelected = computed(() => configs.value.some(c => selectedIds.value.has(c.id)))

function enterBatchMode() {
  batchMode.value = true
  selectedIds.value = new Set()
}

function exitBatchMode() {
  batchMode.value = false
  selectedIds.value = new Set()
}

function toggleSelect(id: string) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedIds.value = s
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(configs.value.map(c => c.id))
  }
}

function onBatchDelete() {
  batchDeleteModalVisible.value = true
}

async function onConfirmBatchDelete() {
  batchDeleting.value = true
  let okCount = 0
  for (const id of selectedIds.value) {
    const ok = await deleteConfig(id)
    if (ok) okCount++
  }
  batchDeleting.value = false
  batchDeleteModalVisible.value = false
  exitBatchMode()
  if (okCount > 0) {
    message.success(`已删除 ${okCount} 个配置`)
    loadConfigList()
  } else {
    message.error('删除失败')
  }
}

function startNewConfig() {
  store.resetAll()
  router.push('/config/new')
}

function startWithPrompt(prompt: string) {
  store.resetAll()
  router.push('/config/new?prompt=' + encodeURIComponent(prompt))
}

async function loadConfigList() {
  loading.value = true
  const result = await listConfigs(currentPage.value, pageSize.value, searchQuery.value)
  // If current page is empty but there are configs, go to last valid page
  if (result.items.length === 0 && result.total > 0 && currentPage.value > 1) {
    const newPage = Math.min(currentPage.value, result.totalPages)
    currentPage.value = newPage
    const retry = await listConfigs(newPage, pageSize.value, searchQuery.value)
    configs.value = retry.items
    totalCount.value = retry.total
    totalPages.value = retry.totalPages
  } else {
    configs.value = result.items
    totalCount.value = result.total
    totalPages.value = result.totalPages
  }
  loading.value = false
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    loadConfigList()
  }, 300)
}

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})

function onPageChange(page: number) {
  currentPage.value = page
  loadConfigList()
}

function onPageSizeChange(val: number) {
  pageSize.value = val
  currentPage.value = 1
  loadConfigList()
}

function onJumpPage() {
  const page = parseInt(jumpPage.value, 10)
  if (!isNaN(page) && page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    jumpPage.value = ''
    loadConfigList()
  }
}

onMounted(() => {
  loadConfigList()
})

async function onLoadConfig(id: string) {
  router.push('/config/new?load=' + id)
}

async function onDownloadYaml(id: string) {
  await downloadConfigYaml(id)
}

function promptDelete(cfg: SavedConfig) {
  deletingConfig.value = cfg
  deleteModalVisible.value = true
}

async function onConfirmDelete() {
  if (!deletingConfig.value) return
  deleting.value = true
  const ok = await deleteConfig(deletingConfig.value.id)
  if (ok) {
    message.success('已删除')
    deleteModalVisible.value = false
    deletingConfig.value = null
    loadConfigList()
  } else {
    message.error('删除失败')
  }
  deleting.value = false
}

function getMenuOptions(cfg: SavedConfig) {
  return [
    { label: '编辑', key: 'edit' },
    { label: '版本历史', key: 'versions' },
    { label: '下载 YAML', key: 'download' },
    { label: '删除', key: 'delete' },
  ]
}

function onMenuSelect(key: string, cfg: SavedConfig) {
  if (key === 'edit') onLoadConfig(cfg.id)
  else if (key === 'versions') openVersionModal(cfg.id)
  else if (key === 'download') onDownloadYaml(cfg.id)
  else if (key === 'delete') promptDelete(cfg)
}

function openExecuteModal(cfg: SavedConfig) {
  executingConfig.value = cfg
  executeModalVisible.value = true
}

function openVersionModal(configId: string) {
  versionModalConfigId.value = configId
  versionModalVisible.value = true
}

function onVersionRefreshed() {
  loadConfigList()
}

function formatTime(iso: string): string {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins} 分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} 天前`
  return iso.slice(0, 10)
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: var(--color-bg);
}

/* ───── hero (empty state) ───── */
.home__hero {
  padding: 64px 24px 56px;
  background: linear-gradient(180deg, var(--color-primary-bg) 0%, var(--color-bg) 100%);
}

.home__hero-inner {
  max-width: 640px;
  margin: 0 auto;
  text-align: center;
}

.home__hero-badge {
  display: inline-block;
  padding: 4px 16px;
  border-radius: 999px;
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  background: linear-gradient(135deg, var(--color-primary-bg), var(--color-primary-bg-light));
  border: 1px solid var(--color-primary-border);
  margin-bottom: 24px;
}

.home__hero-title {
  font-size: 36px;
  font-weight: 800;
  line-height: 1.3;
  color: var(--color-text);
  margin: 0 0 16px;
  letter-spacing: -0.03em;
}

.home__hero-gradient {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light), #0d9488);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.home__hero-subtitle {
  font-size: 15px;
  line-height: 1.7;
  color: var(--color-text-secondary);
  margin: 0 0 24px;
}

.home__hero-anim {
  margin-bottom: 28px;
}

.home__hero-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-bottom: 32px;
}

/* ───── toolbar (has configs) ───── */
.home__toolbar {
  padding: 16px 24px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border-light);
}

.home__toolbar-inner {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.home__toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.home__toolbar-brand {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-primary);
}

.home__toolbar-sep {
  width: 1px;
  height: 16px;
  background: var(--color-border-light);
}

.home__toolbar-intro-link {
  font-family: inherit;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  transition: color 0.2s;
}

.home__toolbar-intro-link:hover {
  color: var(--color-primary);
}

.home__toolbar-actions {
  display: flex;
  gap: 8px;
}

/* ───── hero back button ───── */
.home__hero-back {
  display: inline-block;
  margin-top: 24px;
  font-family: inherit;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 0;
  transition: color 0.2s;
}

.home__hero-back:hover {
  color: var(--color-primary);
}

/* ───── transition ───── */
.home-fade-enter-active,
.home-fade-leave-active {
  transition: opacity 0.25s ease;
}

.home-fade-enter-from,
.home-fade-leave-to {
  opacity: 0;
}

/* ───── prompt chips ───── */
.home__prompt-chips {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

.home__prompt-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.home__prompt-chip {
  display: inline-block;
  padding: 6px 14px;
  font-family: inherit;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.home__prompt-chip:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-primary-border);
}

/* ───── config list ───── */
.home__configs {
  max-width: 640px;
  margin: 0 auto;
  padding: 48px 24px 80px;
}

.home__configs--full {
  max-width: 800px;
  padding-top: 32px;
}

.home__configs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 12px;
}

.home__configs-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.home__configs-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  justify-content: flex-end;
}

.home__search-input {
  max-width: 200px;
}

.home__configs-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.home__configs-count {
  font-size: var(--font-size-xs);
}

.home__batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--color-primary-bg);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
  margin-bottom: 4px;
}

.home__batch-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  flex: 1;
}

.home__config-card--selected {
  border-color: var(--color-primary) !important;
  background: var(--color-primary-bg) !important;
}

.home__config-card-check {
  flex-shrink: 0;
}

.config-name-link--disabled {
  pointer-events: none;
  color: var(--color-text);
}

.home__config-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.home__pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
  flex-wrap: wrap;
}

.home__pagination-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  min-width: 60px;
  text-align: center;
}

.home__pagination-sep {
  width: 1px;
  height: 16px;
  background: var(--color-border-light);
}

.home__page-size-select {
  width: 110px;
}

.home__pagination-jump {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.home__jump-input {
  width: 52px;
  text-align: center;
}

/* ───── config card ───── */
.home__config-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.home__config-card:hover {
  border-color: var(--color-primary-border);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.home__config-card-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  flex: 1;
}

.home__config-card-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.home__config-card-info {
  min-width: 0;
}

.home__config-card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
  flex-wrap: wrap;
}

.home__meta-item {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.home__meta-sep {
  font-size: var(--font-size-xs);
  color: var(--color-border);
}

.home__config-card-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.home__menu-btn {
  font-size: 18px !important;
  color: var(--color-text-muted) !important;
  padding: 0 4px !important;
}

.home__menu-btn:hover {
  color: var(--color-text) !important;
}

/* ───── button overrides ───── */
:deep(.btn-secondary) {
  border: 1px solid var(--color-border-light) !important;
  background: var(--color-surface) !important;
  color: var(--color-text) !important;
  font-weight: 500 !important;
}

:deep(.btn-secondary:hover) {
  background: var(--color-surface-hover) !important;
}

/* ───── misc ───── */
.config-name-link {
  font-weight: 600;
  font-size: 15px;
  color: var(--color-primary);
  text-decoration: none;
}

.config-name-link:hover {
  text-decoration: underline;
}

/* ───── Responsive: Tablet ───── */
@media (max-width: 1023px) {
  .home__hero {
    padding: 48px 20px 44px;
  }
  .home__hero-title {
    font-size: 30px;
  }
  .home__hero-subtitle {
    font-size: 14px;
  }
  .home__configs {
    max-width: 100%;
    padding: 40px 20px 64px;
  }
}

/* ───── Responsive: Mobile ───── */
@media (max-width: 767px) {
  .home__hero {
    padding: 36px 16px 32px;
  }
  .home__hero-inner {
    max-width: 100%;
  }
  .home__hero-badge {
    font-size: 11px;
    padding: 3px 12px;
    margin-bottom: 16px;
  }
  .home__hero-title {
    font-size: 26px;
  }
  .home__hero-subtitle {
    font-size: 13px;
    line-height: 1.6;
    margin-bottom: 24px;
  }
  .home__hero-actions {
    flex-direction: column;
    gap: 8px;
  }
  .home__prompt-chips {
    gap: 6px;
  }
  .home__prompt-chip {
    font-size: 11px;
    padding: 5px 10px;
  }
  .home__configs {
    padding: 32px 16px 64px;
    max-width: 100%;
  }
  .home__config-card {
    padding: 12px 14px;
    border-radius: var(--radius-md);
  }
  .home__config-card-icon {
    font-size: 20px;
  }
  .home__config-card-meta {
    gap: 4px;
  }
  .home__meta-item {
    font-size: 10px;
  }
  .config-name-link {
    font-size: 14px;
  }
}

/* ───── Skeleton shimmer ───── */
.home__skeleton {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.home__skeleton-card {
  height: 64px;
  border-radius: 12px;
  background: linear-gradient(
    90deg,
    var(--color-surface-hover) 25%,
    var(--color-border-light) 50%,
    var(--color-surface-hover) 75%
  );
  background-size: 200% 100%;
  animation: cf-shimmer 1.5s infinite ease-in-out;
}

@keyframes cf-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
