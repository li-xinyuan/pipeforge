<template>
  <div class="home">
    <AppNavBar current-route="home" />

    <AiStatusBanner />

    <!-- Toolbar -->
    <section class="home__toolbar">
      <div class="home__toolbar-inner">
        <div class="home__toolbar-actions">
          <NButton v-if="authStore.canEdit" type="primary" size="small" class="btn-primary" @click="startNewConfig">✏ 新建配置</NButton>
          <NButton size="small" class="btn-secondary" @click="router.push('/templates')">📦 模板市场</NButton>
          <NButton size="small" class="btn-secondary" @click="router.push('/guide')">📖 指南</NButton>
        </div>
      </div>
    </section>

    <!-- Config list section -->
    <section class="home__configs">
      <div class="home__configs-header">
        <div class="home__configs-header-left">
          <h2 class="home__configs-title">最近配置</h2>
          <NTag v-if="totalCount > 0" size="small" :bordered="false" class="home__configs-count">{{ totalCount }} 个配置</NTag>
        </div>
        <ConfigToolbar
          v-if="totalCount > 0 || searchQuery"
          :search-query="searchQuery"
          :batch-mode="batchMode"
          @update:search-query="searchQuery = $event"
          @search="onSearch"
          @enter-batch-mode="enterBatchMode"
          @exit-batch-mode="exitBatchMode"
        />
      </div>

      <ConfigListSection
        :loading="loading"
        :error="error"
        :configs="configs"
        :batch-mode="batchMode"
        :selected-ids="selectedIds"
        :is-all-selected="isAllSelected"
        :is-some-selected="isSomeSelected"
        :can-edit="authStore.canEdit"
        :search-query="searchQuery"
        :batch-deleting="batchDeleting"
        :current-page="currentPage"
        :total-pages="totalPages"
        :page-size="pageSize"
        :page-size-options="pageSizeOptions"
        @toggle-select="toggleSelect"
        @toggle-select-all="toggleSelectAll"
        @execute="openExecuteModal"
        @menu-select="onMenuSelect"
        @batch-delete="onBatchDelete"
        @page-change="onPageChange"
        @page-size-change="onPageSizeChange"
        @jump-page="onJumpPage"
      />
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
      @goto-step="onGotoStep"
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
import { useAuthStore } from '../stores/auth'
import type { SavedConfig } from '../types/wizard'
import { NButton, NModal, NTag, useMessage } from 'naive-ui'
import AppNavBar from '../components/common/AppNavBar.vue'
import ExecuteConfigModal from '../components/ExecuteConfigModal.vue'
import ConfigVersionPanel from '../components/config/ConfigVersionPanel.vue'
import AiStatusBanner from '../components/AiStatusBanner.vue'
import ConfigToolbar from '../components/home/ConfigToolbar.vue'
import ConfigListSection from '../components/home/ConfigListSection.vue'

const router = useRouter()
const store = useWizardStore()
const authStore = useAuthStore()
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
const searchQuery = ref('')
const _showIntro = ref(false)

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

function onJumpPage(page: number) {
  currentPage.value = page
  loadConfigList()
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

function onGotoStep(step: number, fixes?: { step: number; field: string; old: string; new: string; reason: string }[]) {
  const cfgId = executingConfig.value?.id
  if (cfgId) {
    const query: Record<string, string> = { load: cfgId, step: String(step) }
    if (fixes) {
      query.autofix = btoa(encodeURIComponent(JSON.stringify(fixes)))
    }
    router.push({ path: '/config/new', query })
  }
}

function openVersionModal(configId: string) {
  versionModalConfigId.value = configId
  versionModalVisible.value = true
}

function onVersionRefreshed() {
  loadConfigList()
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
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light), var(--color-primary));
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

.home__configs-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.home__configs-count {
  font-size: var(--font-size-xs);
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
  .home__toolbar-inner {
    flex-wrap: wrap;
    gap: 8px;
  }
  .home__configs-header {
    flex-wrap: wrap;
    gap: 8px;
  }
}
</style>
