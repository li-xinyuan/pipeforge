<template>
  <div class="market">
    <AppNavBar current-route="templates" />

    <section class="market__header">
      <div class="market__header-inner">
        <h1 class="market__title">模板市场</h1>
        <p class="market__subtitle">浏览和使用预置模板，快速创建数据管道配置</p>
        <div class="market__search">
          <NInput
            v-model:value="searchQuery"
            placeholder="搜索模板名称或描述..."
            clearable
            size="small"
            class="market__search-input"
            @update:value="onSearch"
          >
            <template #prefix>
              <span style="color: var(--color-text-muted);">🔍</span>
            </template>
          </NInput>
        </div>
      </div>
    </section>

    <!-- Category filter tabs -->
    <section class="market__filters">
      <div class="market__filters-inner">
        <button
          v-for="cat in categories"
          :key="cat.value"
          class="market__filter-tab"
          :class="{ 'market__filter-tab--active': activeCategory === cat.value }"
          @click="onCategoryChange(cat.value)"
        >
          <span class="market__filter-icon">{{ cat.icon }}</span>
          {{ cat.label }}
        </button>
      </div>
    </section>

    <!-- Template grid -->
    <section class="market__content">
      <div v-if="loading" class="market__skeleton">
        <div v-for="n in 6" :key="n" class="market__skeleton-card" />
      </div>

      <NAlert v-else-if="error" type="error" :title="error.message" />

      <div v-else-if="templates.length > 0" class="market__grid">
        <div
          v-for="tpl in templates"
          :key="tpl.id"
          class="market__card card-lift"
          @click="openPreview(tpl)"
        >
          <div class="market__card-header">
            <span class="market__card-icon">{{ categoryIcon(tpl.category) }}</span>
            <NTag v-if="tpl.isOfficial" size="small" :bordered="false" type="info" class="market__card-official">官方</NTag>
          </div>
          <h3 class="market__card-name">{{ tpl.name }}</h3>
          <p class="market__card-desc">{{ tpl.description }}</p>
          <div v-if="tpl.tags.length" class="market__card-tags">
            <NTag v-for="tag in tpl.tags.slice(0, 3)" :key="tag" size="small" :bordered="false" class="market__card-tag">{{ tag }}</NTag>
            <NTag v-if="tpl.tags.length > 3" size="small" :bordered="false" class="market__card-tag">+{{ tpl.tags.length - 3 }}</NTag>
          </div>
          <div class="market__card-footer">
            <span class="market__card-meta">{{ tpl.author }}</span>
            <span class="market__card-sep">·</span>
            <span class="market__card-meta">使用 {{ tpl.usageCount }} 次</span>
            <NButton size="small" type="primary" class="btn-primary market__card-btn" @click.stop="openPreview(tpl)">使用此模板</NButton>
          </div>
        </div>
      </div>

      <div v-else class="market__empty">
        <p class="market__empty-icon">📦</p>
        <p class="market__empty-text">暂无模板</p>
        <p class="market__empty-hint">当前分类下没有可用的模板</p>
      </div>
    </section>

    <!-- Preview modal -->
    <TemplatePreviewModal
      v-model:show="previewVisible"
      :template="previewTemplate"
      @close="onPreviewClose"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { NInput, NTag, NAlert, NButton } from 'naive-ui'
import AppNavBar from '../components/common/AppNavBar.vue'
import TemplatePreviewModal from '../components/template/TemplatePreviewModal.vue'
import type { Template } from '../types/wizard'
import { useTemplateApi } from '../composables/useTemplateApi'

const { listTemplates, loading, error } = useTemplateApi()

const templates = ref<Template[]>([])
const searchQuery = ref('')
const activeCategory = ref('')

const categories = [
  { label: '全部', value: '', icon: '📋' },
  { label: '销售', value: 'sales', icon: '📊' },
  { label: '财务', value: 'finance', icon: '💰' },
  { label: '人力', value: 'hr', icon: '👥' },
  { label: '运维', value: 'ops', icon: '🔧' },
  { label: '通用', value: 'general', icon: '📦' },
]

const previewVisible = ref(false)
const previewTemplate = ref<Template | null>(null)

function categoryIcon(category: string): string {
  const icons: Record<string, string> = {
    'sales': '📊',
    'finance': '💰',
    'hr': '👥',
    'ops': '🔧',
    'general': '📦',
  }
  return icons[category] || '📦'
}

async function loadTemplates() {
  const result = await listTemplates(activeCategory.value || undefined, searchQuery.value || undefined)
  templates.value = result.items
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    loadTemplates()
  }, 300)
}

function onCategoryChange(category: string) {
  activeCategory.value = category
  loadTemplates()
}

function openPreview(tpl: Template) {
  previewTemplate.value = tpl
  previewVisible.value = true
}

function onPreviewClose() {
  previewTemplate.value = null
}

onMounted(() => {
  loadTemplates()
})

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<style scoped>
.market {
  min-height: 100vh;
  background: var(--color-bg);
}

/* ───── Header ───── */
.market__header {
  padding: 48px 24px 32px;
  background: linear-gradient(180deg, var(--color-primary-bg) 0%, var(--color-bg) 100%);
}

.market__header-inner {
  max-width: 960px;
  margin: 0 auto;
  text-align: center;
}

.market__title {
  font-size: 32px;
  font-weight: 800;
  color: var(--color-text);
  margin: 0 0 8px;
  letter-spacing: -0.02em;
}

.market__subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 20px;
}

.market__search {
  max-width: 480px;
  margin: 0 auto;
}

.market__search-input {
  width: 100%;
}

/* ───── Category filters ───── */
.market__filters {
  padding: 0 24px;
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-surface);
}

.market__filters-inner {
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  gap: 4px;
  overflow-x: auto;
  padding: 8px 0;
}

.market__filter-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 16px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: none;
  font-family: inherit;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-fast);
}

.market__filter-tab:hover {
  color: var(--color-primary);
  background: var(--color-primary-bg);
}

.market__filter-tab--active {
  color: var(--color-primary);
  background: var(--color-primary-bg);
  border-color: var(--color-primary-border);
  font-weight: 600;
}

.market__filter-icon {
  font-size: 14px;
}

/* ───── Content grid ───── */
.market__content {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 24px 80px;
}

.market__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

/* ───── Card ───── */
.market__card {
  padding: 20px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
}

.market__card:hover {
  border-color: var(--color-primary-border);
}

.market__card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.market__card-icon {
  font-size: 28px;
}

.market__card-official {
  font-size: 10px;
}

.market__card-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 6px;
}

.market__card-desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0 0 10px;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.market__card-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.market__card-tag {
  font-size: 10px;
}

.market__card-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.market__card-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.market__card-sep {
  font-size: var(--font-size-xs);
  color: var(--color-border);
}

.market__card-btn {
  margin-left: auto;
}

/* ───── Empty state ───── */
.market__empty {
  text-align: center;
  padding: 60px 20px;
}

.market__empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.market__empty-text {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 4px;
}

.market__empty-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0;
}

/* ───── Skeleton ───── */
.market__skeleton {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.market__skeleton-card {
  height: 220px;
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

/* ───── Responsive: Tablet ───── */
@media (max-width: 1023px) {
  .market__grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .market__skeleton {
    grid-template-columns: repeat(2, 1fr);
  }
  .market__header {
    padding: 36px 20px 24px;
  }
  .market__title {
    font-size: 26px;
  }
}

/* ───── Responsive: Mobile ───── */
@media (max-width: 767px) {
  .market__grid {
    grid-template-columns: 1fr;
  }
  .market__skeleton {
    grid-template-columns: 1fr;
  }
  .market__header {
    padding: 28px 16px 20px;
  }
  .market__title {
    font-size: 22px;
  }
  .market__content {
    padding: 16px 16px 64px;
  }
  .market__filters-inner {
    gap: 2px;
  }
  .market__filter-tab {
    padding: 5px 10px;
    font-size: var(--font-size-xs);
  }
}
</style>
