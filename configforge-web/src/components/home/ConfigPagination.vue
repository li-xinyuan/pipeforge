<template>
  <div v-if="totalPages > 1" class="home__pagination">
    <NButton size="small" :disabled="currentPage <= 1" @click="emit('pageChange', currentPage - 1)">← 上一页</NButton>
    <span class="home__pagination-info">{{ currentPage }} / {{ totalPages }}</span>
    <NButton size="small" :disabled="currentPage >= totalPages" @click="emit('pageChange', currentPage + 1)">下一页 →</NButton>
    <span class="home__pagination-sep" />
    <NSelect :value="pageSize" :options="pageSizeOptions" size="small" class="home__page-size-select" @update:value="(val: number) => emit('pageSizeChange', val)" />
    <span class="home__pagination-sep" />
    <span class="home__pagination-jump">
      跳至
      <NInput v-model:value="jumpPage" size="small" class="home__jump-input" @keyup.enter="onJumpPage" />
      页
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NInput, NSelect } from 'naive-ui'

const props = defineProps<{
  currentPage: number
  totalPages: number
  pageSize: number
  pageSizeOptions: Array<{ label: string; value: number }>
}>()

const emit = defineEmits<{
  pageChange: [page: number]
  pageSizeChange: [size: number]
  jumpPage: [page: number]
}>()

const jumpPage = ref('')

function onJumpPage() {
  const page = parseInt(jumpPage.value, 10)
  if (!isNaN(page) && page >= 1 && page <= props.totalPages) {
    emit('jumpPage', page)
    jumpPage.value = ''
  }
}
</script>

<style scoped>
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
</style>
