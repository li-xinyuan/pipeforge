<template>
  <template v-if="store.output?.plugin === 'database'">
    <!-- Connection selector -->
    <div>
      <label class="cf-label"><span class="cf-required">*</span> 数据库连接</label>
      <div class="flex items-center gap-2">
        <NSelect
          v-model:value="dbConfig.connectionId"
          :options="connectionOptions"
          placeholder="-- 选择连接 --"
          size="small"
          class="flex-1"
          @update:value="onConnectionSelected"
        />
        <NButton size="small" quaternary @click="$emit('open-conn-manager')">⚙ 管理</NButton>
      </div>
      <p v-if="connectionOptions.length === 0" class="text-xs text-amber-600 dark:text-amber-400 mt-1">
        暂无连接，点击"管理"按钮新建数据库连接
      </p>
    </div>
    <!-- Target table name -->
    <div>
      <label class="cf-label"><span class="cf-required">*</span> 目标表名</label>
      <NInput v-model:value="dbConfig.targetTable" placeholder="例如：report_data" size="small" />
    </div>
    <!-- Write mode -->
    <div>
      <label class="cf-label">写入模式</label>
      <NSelect
        v-model:value="dbConfig.writeMode"
        :options="writeModeOptions"
        size="small"
      />
    </div>
    <!-- Batch size -->
    <div>
      <label class="cf-label">批量大小</label>
      <NInputNumber v-model:value="dbConfig.batchSize" :min="1" :max="10000" size="small" />
    </div>
    <!-- Create table if not exists -->
    <div>
      <NCheckbox v-model:checked="dbConfig.createTableIfNotExists" size="small">自动建表</NCheckbox>
    </div>
    <!-- Primary key columns -->
    <div v-if="dbConfig.writeMode === 'upsert'">
      <label class="cf-label">主键列</label>
      <NSelect
        v-model:value="dbConfig.primaryKeyColumns"
        :options="primaryKeyOptions"
        multiple
        placeholder="选择主键列"
        size="small"
      />
    </div>
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { useConnections } from '../../composables/useConnections'
import type { DatabaseOutputConfig, ColumnMappingItem } from '../../types/wizard'
import { NInput, NButton, NSelect, NCheckbox, NInputNumber } from 'naive-ui'

const store = useWizardStore()

defineEmits<{
  'open-conn-manager': []
}>()

const dbConfig = computed(() => store.output!.config as DatabaseOutputConfig)

const { connectionOptions } = useConnections()

const writeModeOptions = [
  { label: '追加 (INSERT)', value: 'append' },
  { label: '替换 (DROP+CREATE+INSERT)', value: 'replace' },
  { label: '更新插入 (UPSERT)', value: 'upsert' },
]

const primaryKeyOptions = computed(() => {
  return (store.output!.config as DatabaseOutputConfig).columns
    .filter((c: ColumnMappingItem) => c.source)
    .map((c: ColumnMappingItem) => ({ label: c.target || c.source, value: c.target || c.source }))
})

function onConnectionSelected(connId: string) {
  dbConfig.value.connectionId = connId
}
</script>
