<template>
  <div class="home">
    <AppNavBar current-route="home" />

    <AiStatusBanner />

    <!-- Hero section — dual entry -->
    <section class="home__hero">
      <div class="home__hero-inner">
        <div class="home__hero-badge">⚡ AI 驱动 · 你说需求，AI 填配置</div>
        <h1 class="home__hero-title">
          描述你的数据处理需求<br>
          <span class="home__hero-gradient">Forge 帮你自动生成配置</span>
        </h1>
        <p class="home__hero-subtitle">
          用自然语言告诉我你想做什么<br>进入向导后，我会一步步引导你完成配置
        </p>

        <!-- AI 可用：输入框 + 引导按钮 -->
        <template v-if="showAiEntry">
          <div class="home__prompt-input-wrap">
            <input
              class="home__prompt-input"
              v-model="promptText"
              placeholder="例如：把订单表和用户表关联，按城市统计订单金额，导出 Excel"
              @keydown.enter="startAiGuide"
            />
            <button class="home__prompt-mic" @click="onVoicePlaceholder" title="语音输入（下版本支持）">🎤</button>
          </div>
          <button class="home__cta" @click="startAiGuide">✨ AI 引导配置</button>

          <div class="home__prompt-chips" v-if="showAiEntry">
            <span class="home__prompt-label">试试这样说</span>
            <button class="home__prompt-chip" @click="startWithPrompt('导出用户表到CSV', '把用户表的ID、名称和邮箱导出到CSV')">导出用户表到 CSV</button>
            <button class="home__prompt-chip" @click="startWithPrompt('合并并统计订单', '合并订单表和用户表，按城市统计订单金额')">合并并统计订单</button>
            <button class="home__prompt-chip" @click="startWithPrompt('月度销售汇总', '从数据库读取销售数据，按月份汇总写入数据库')">月度销售汇总</button>
          </div>
        </template>

        <!-- AI 不可用：灰掉输入框 + 引导到设置 -->
        <template v-else>
          <div class="home__prompt-input-wrap">
            <input
              class="home__prompt-input home__prompt-input--disabled"
              disabled
              placeholder="需先配置 AI 才能使用智能引导"
            />
          </div>
          <button class="home__cta home__cta--secondary" @click="router.push('/settings')">前往设置 →</button>
        </template>

        <!-- 手动创建入口始终可见 -->
        <a class="home__manual-link" @click.prevent="startManualCreate">或 手动创建 →</a>
      </div>
    </section>

    <!-- Config list section -->
    <section class="home__configs">
      <div class="home__configs-header">
        <h2 class="home__configs-title">最近配置</h2>
        <div class="home__configs-header-right">
          <NInput
            v-model:value="searchQuery"
            size="small"
            placeholder="搜索配置..."
            clearable
            class="home__search-input"
            @update:value="onSearchChange"
          />
          <NTag v-if="totalCount" size="small" :bordered="false" class="home__configs-count">{{ totalCount }} 个配置</NTag>
        </div>
      </div>

      <div v-if="loading" class="home__skeleton">
        <div v-for="n in 3" :key="n" class="home__skeleton-card" />
      </div>

      <NAlert v-else-if="error" type="error" :title="error" />

      <div v-else-if="configs.items.length > 0" class="home__config-list">
        <div v-for="cfg in configs.items" :key="cfg.id" class="home__config-card card-lift">
          <div class="home__config-card-left">
            <span class="home__config-card-icon">📋</span>
            <div class="home__config-card-info">
              <router-link :to="'/config/new?load=' + cfg.id" class="config-name-link">{{ cfg.sceneName }}</router-link>
              <div class="home__config-card-meta">
                <span class="home__meta-item">{{ cfg.version }}</span>
                <span class="home__meta-sep">·</span>
                <span class="home__meta-item">{{ cfg.inputCount }} 个输入源</span>
                <span class="home__meta-sep">·</span>
                <span class="home__meta-item">{{ cfg.outputType }}</span>
                <span class="home__meta-sep">·</span>
                <span class="home__meta-item">{{ formatTime(cfg.updatedAt) }}</span>
              </div>
            </div>
          </div>
          <div class="home__config-card-right">
            <NButton v-if="cfg.inputCount > 0" size="small" secondary type="primary" @click.stop="openExecuteModal(cfg)">执行</NButton>
            <NDropdown trigger="click" :options="getMenuOptions(cfg)" @select="(key: string) => onMenuSelect(key, cfg)">
              <NButton text size="tiny" class="home__menu-btn" style="min-width: 44px; min-height: 44px;">···</NButton>
            </NDropdown>
          </div>
        </div>
      </div>

      <div v-else style="text-align: center; padding: 40px 20px; color: var(--color-text-muted);">
        <p style="font-size: 48px; margin-bottom: 12px;">📋</p>
        <p style="font-size: var(--font-size-base); font-weight: 500; margin-bottom: 8px;">还没有配置</p>
        <p style="font-size: var(--font-size-sm);">点击上方按钮开始创建你的第一个数据管道配置</p>
      </div>

      <!-- Pagination — outside the v-if chain so it shows alongside the list -->
      <div v-if="configs.total_pages > 1" class="home__pagination">
        <NButton size="small" :disabled="configs.page <= 1" @click="goToPage(configs.page - 1)">← 上一页</NButton>
        <span class="home__pagination-info">第 {{ configs.page }}/{{ configs.total_pages }} 页</span>
        <NButton size="small" :disabled="configs.page >= configs.total_pages" @click="goToPage(configs.page + 1)">下一页 →</NButton>
      </div>
    </section>

    <!-- 删除确认弹窗 -->
    <NModal v-model:show="deleteModalVisible" preset="card" title="确认删除" style="max-width: 400px">
      <p class="text-sm text-slate-600 mb-0">
        确定要删除配置 "<strong>{{ deletingConfig?.sceneName }}</strong>" 吗？此操作不可撤销。
      </p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <NButton @click="deleteModalVisible = false">取消</NButton>
          <NButton type="error" :loading="deleting" @click="onConfirmDelete">删除</NButton>
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
    <NModal v-model:show="versionModalVisible" preset="card" title="版本历史" style="max-width: 520px">
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useConfigApi, type PaginatedResponse } from '../composables/useConfigApi'
import { useWizardStore } from '../stores/wizard'
import type { SavedConfig } from '../types/wizard'
import { NButton, NInput, NAlert, NModal, NTag, NDropdown, useMessage } from 'naive-ui'
import { useAiStatus } from '../composables/useAiStatus'
import AppNavBar from '../components/common/AppNavBar.vue'
import ExecuteConfigModal from '../components/ExecuteConfigModal.vue'
import ConfigVersionPanel from '../components/config/ConfigVersionPanel.vue'
import AiStatusBanner from '../components/AiStatusBanner.vue'
import PipelineAnimation from '../components/PipelineAnimation.vue'

const router = useRouter()
const store = useWizardStore()
const message = useMessage()
const { listConfigs, deleteConfig, downloadConfigYaml } = useConfigApi()

const { aiConfigured, checkStatus: checkAiStatus } = useAiStatus()
const promptText = ref('')
const showAiEntry = computed(() => aiConfigured.value !== false)
const loading = ref(true)
const error = ref('')
const configs = ref<PaginatedResponse<SavedConfig>>({ items: [], total: 0, page: 1, page_size: 10, total_pages: 1 })
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
let searchTimer: ReturnType<typeof setTimeout> | null = null

const totalCount = ref(0)

const deleteModalVisible = ref(false)
const deletingConfig = ref<SavedConfig | null>(null)
const deleting = ref(false)

const executeModalVisible = ref(false)
const executingConfig = ref<SavedConfig | null>(null)

const versionModalVisible = ref(false)
const versionModalConfigId = ref<string | null>(null)

function startAiGuide() {
  if (!promptText.value.trim()) return
  store.resetAll()
  try { localStorage.removeItem('wizard_state_v2') } catch {}
  store.scene.name = promptText.value.trim()
  router.push('/config/new?guide=' + encodeURIComponent(promptText.value.trim()))
}

function startWithPrompt(name: string, description?: string) {
  store.resetAll()
  try { localStorage.removeItem('wizard_state_v2') } catch {}
  store.scene.name = name
  if (description) store.scene.description = description
  router.push('/config/new?guide=' + encodeURIComponent(description || name))
}

function startManualCreate() {
  store.resetAll()
  if (promptText.value.trim()) {
    store.scene.name = promptText.value.trim()
  }
  router.push('/config/new')
}

function onVoicePlaceholder() {
  message.info('语音输入即将在下一版本支持')
}

async function fetchConfigs() {
  loading.value = true
  const result = await listConfigs({
    search: searchQuery.value || undefined,
    page: currentPage.value,
    pageSize: pageSize.value,
  })
  configs.value = result
  totalCount.value = result.total
  loading.value = false
}

onMounted(() => { checkAiStatus(); fetchConfigs() })

function goToPage(page: number) {
  currentPage.value = page
  fetchConfigs()
}

function onSearchChange() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    fetchConfigs()
  }, 300)
}

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
    configs.value.items = configs.value.items.filter(c => c.id !== deletingConfig.value!.id)
    totalCount.value = Math.max(0, totalCount.value - 1)
    deleteModalVisible.value = false
    deletingConfig.value = null
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
  // Reload config list after rollback to reflect updated version info
  listConfigs({ page: currentPage.value, pageSize: pageSize.value }).then(data => {
    configs.value = data
    totalCount.value = data.total
  })
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

/* ───── hero ───── */
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

.home__configs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 12px;
}
.home__configs-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.home__search-input {
  width: 200px;
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

.home__config-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
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

/* ───── pagination ───── */
.home__pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
}
.home__pagination-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
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

/* ───── Dual entry hero ───── */
.home__prompt-input-wrap {
  position: relative;
  max-width: 520px;
  margin: 0 auto 14px;
}
.home__prompt-input {
  width: 100%;
  padding: 14px 48px 14px 16px;
  border-radius: 12px;
  border: 2px solid var(--color-border-light);
  background: var(--color-surface);
  font-size: 15px;
  color: var(--color-text);
  outline: none;
  font-family: inherit;
  transition: border-color 0.2s;
}
.home__prompt-input:focus { border-color: var(--color-primary); }
.home__prompt-input--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.home__prompt-mic {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 36px; height: 36px;
  border-radius: 50%;
  border: none;
  background: transparent;
  font-size: 18px;
  cursor: pointer;
  color: var(--color-text-muted);
}
.home__prompt-mic:hover { background: var(--color-surface-hover); }
.home__cta {
  padding: 12px 40px;
  border-radius: 12px;
  border: none;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  color: #fff;
  margin-bottom: 14px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.home__cta:hover { transform: translateY(-2px); box-shadow: 0 6px 24px rgba(13,148,136,0.3); }
.home__cta--secondary {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border-light);
}
.home__cta--secondary:hover { transform: none; box-shadow: none; background: var(--color-surface-hover); }
.home__manual-link {
  display: inline-block;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  text-decoration: none;
  padding: 4px 0;
  cursor: pointer;
}
.home__manual-link:hover { color: var(--color-primary); }

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
