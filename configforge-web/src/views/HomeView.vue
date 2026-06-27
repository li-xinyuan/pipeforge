<template>
  <div class="home">
    <AppNavBar current-route="home" />

    <AiStatusBanner />

    <!-- Toolbar -->
    <section class="home__toolbar">
      <div class="home__toolbar-inner">
        <div class="home__toolbar-actions">
          <NButton v-if="authStore.canEdit" type="primary" size="small" class="btn-primary" @click="startNewConfig">{{ t('home.newConfig') }}</NButton>
          <NButton v-if="authStore.canEdit" size="small" class="btn-secondary" @click="triggerImport">{{ t('home.importConfig') }}</NButton>
          <NButton size="small" class="btn-secondary" @click="router.push('/templates')">{{ t('home.templates') }}</NButton>
          <NButton size="small" class="btn-secondary" @click="router.push('/guide')">{{ t('home.guide') }}</NButton>
          <input
            ref="importFileInput"
            type="file"
            accept=".yaml,.yml,.json"
            style="display: none"
            @change="onImportFileSelected"
          />
        </div>
      </div>
    </section>

    <!-- Config list section -->
    <section class="home__configs">
      <div class="home__configs-header">
        <div class="home__configs-header-left">
          <h2 class="home__configs-title">{{ t('home.recentConfigs') }}</h2>
          <NTag v-if="totalCount > 0" size="small" :bordered="false" class="home__configs-count">{{ t('home.configCount', { count: totalCount }) }}</NTag>
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
    <NModal v-model:show="deleteModalVisible" preset="card" :title="t('home.confirmDeleteTitle')" style="max-width: 400px" :trap-focus="true" :auto-focus="true">
      <p class="text-sm text-slate-600 dark:text-slate-300 mb-0">
        {{ t('home.confirmDeleteBody', { name: deletingConfig?.sceneName }) }}
      </p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <NButton @click="deleteModalVisible = false">{{ t('common.cancel') }}</NButton>
          <NButton type="error" :loading="deleting" @click="onConfirmDelete">{{ t('common.delete') }}</NButton>
        </div>
      </template>
    </NModal>

    <!-- 批量删除确认弹窗 -->
    <NModal v-model:show="batchDeleteModalVisible" preset="card" :title="t('home.confirmBatchDeleteTitle')" style="max-width: 400px" :trap-focus="true" :auto-focus="true">
      <p class="text-sm text-slate-600 dark:text-slate-300 mb-0">
        {{ t('home.confirmBatchDeleteBody', { count: selectedIds.size }) }}
      </p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <NButton @click="batchDeleteModalVisible = false">{{ t('common.cancel') }}</NButton>
          <NButton type="error" :loading="batchDeleting" @click="onConfirmBatchDelete">{{ t('common.delete') }}</NButton>
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
    <NModal v-model:show="versionModalVisible" preset="card" :title="t('home.versionHistoryTitle')" style="max-width: 520px" :trap-focus="true" :auto-focus="true">
      <ConfigVersionPanel
        v-if="versionModalConfigId"
        :config-id="versionModalConfigId"
        :current-version="0"
        @refreshed="onVersionRefreshed"
      />
      <template #footer>
        <NButton @click="versionModalVisible = false">{{ t('common.close') }}</NButton>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useConfigApi } from '../composables/useConfigApi'
import { useBatchSelect } from '../composables/useBatchSelect'
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
const { t } = useI18n()
const { listConfigs, deleteConfig, downloadConfigYaml, exportConfig, importConfig } = useConfigApi()

const loading = ref(true)
const error = ref('')
const configs = ref<SavedConfig[]>([])
const totalCount = ref(0)
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = ref(10)
const pageSizeOptions = computed(() => [
  { label: t('home.pageSize.10'), value: 10 },
  { label: t('home.pageSize.20'), value: 20 },
  { label: t('home.pageSize.50'), value: 50 },
])
const searchQuery = ref('')
const _showIntro = ref(false)

const deleteModalVisible = ref(false)
const deletingConfig = ref<SavedConfig | null>(null)
const deleting = ref(false)

const executeModalVisible = ref(false)
const executingConfig = ref<SavedConfig | null>(null)

const versionModalVisible = ref(false)
const versionModalConfigId = ref<string | null>(null)

const importFileInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)

const {
  batchMode,
  selectedIds,
  batchDeleteModalVisible,
  batchDeleting,
  isAllSelected,
  isSomeSelected,
  enterBatchMode,
  exitBatchMode,
  toggleSelect,
  toggleSelectAll,
  onBatchDelete,
  onConfirmBatchDelete,
} = useBatchSelect({
  configs: configs,
  deleteConfig,
  message,
  loadConfigList,
})

function startNewConfig() {
  store.resetAll()
  router.push('/config/new')
}

async function loadConfigList() {
  loading.value = true
  const result = await listConfigs(currentPage.value, pageSize.value, searchQuery.value)
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
    message.success(t('home.deleted'))
    deleteModalVisible.value = false
    deletingConfig.value = null
    loadConfigList()
  } else {
    message.error(t('home.deleteFailed'))
  }
  deleting.value = false
}

function onMenuSelect(key: string, cfg: SavedConfig) {
  if (key === 'edit') onLoadConfig(cfg.id)
  else if (key === 'versions') openVersionModal(cfg.id)
  else if (key === 'download') onDownloadYaml(cfg.id)
  else if (key === 'export_yaml') onExportConfig(cfg.id, 'yaml')
  else if (key === 'export_json') onExportConfig(cfg.id, 'json')
  else if (key === 'delete') promptDelete(cfg)
}

async function onExportConfig(id: string, format: 'yaml' | 'json') {
  await exportConfig(id, format)
  message.success(t('home.exportedAs', { format: format.toUpperCase() }))
}

function triggerImport() {
  importFileInput.value?.click()
}

async function onImportFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  importing.value = true
  try {
    const result = await importConfig(file)
    if (result) {
      message.success(t('home.importedConfig', { name: result.sceneName }))
      await loadConfigList()
    }
  } finally {
    importing.value = false
    // Reset input so the same file can be selected again
    input.value = ''
  }
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

/* ───── toolbar ───── */
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

.home__toolbar-actions {
  display: flex;
  gap: 8px;
}

/* ───── config list ───── */
.home__configs {
  max-width: 640px;
  margin: 0 auto;
  padding: 48px 24px 80px;
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
  .home__configs {
    max-width: 100%;
    padding: 40px 20px 64px;
  }
}

/* ───── Responsive: Mobile ───── */
@media (max-width: 767px) {
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
