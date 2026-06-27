<template>
  <!--
    DatabaseOutputForm — database 输出配置表单（限制①第三阶段迁移）。

    迁移策略：
    - connectionId/targetTable/writeMode/batchSize/createTableIfNotExists 迁入 SchemaForm，
      connectionId 通过 connection-selector 命名 widget 渲染（自包含 modal）。
    - primaryKeyColumns 保留为自定义 UI：选项来自 columns，需 reactive 更新
      （SchemaForm 的 async loader 仅挂载时加载一次，不满足 reactivity），用 skipFields 跳过。
    - writeMode === 'upsert' 时显示 primaryKeyColumns（条件显隐由自定义 v-if 处理）。
  -->
  <template v-if="store.output?.plugin === 'database' && dbOutputSchema">
    <SchemaForm
      class="cf-form-group--full"
      grid
      :model-value="store.output.config as unknown as Record<string, unknown>"
      :schema="dbOutputSchema"
      :skip-fields="['columns', 'sourceTable', 'primaryKeyColumns']"
      @update:model-value="onSchemaUpdate"
    />
    <!-- Primary key columns (upsert only, reactive options from columns) -->
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
import { computed, onMounted } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { usePluginSchema } from '../../composables/usePluginSchema'
import { registerWidget } from '../../composables/widgetRegistry'
import SchemaForm from '../common/SchemaForm.vue'
import ConnectionSelector from '../common/ConnectionSelector.vue'
import type { DatabaseOutputConfig, ColumnMappingItem } from '../../types/wizard'
import { NSelect } from 'naive-ui'

const store = useWizardStore()

// 注册 connection-selector 命名 widget（database output 的 connectionId 字段引用）
registerWidget('connection-selector', ConnectionSelector)

const { getSchema, load } = usePluginSchema()
const dbOutputSchema = computed(() => getSchema('database', 'output'))

onMounted(() => {
  load()
})

const dbConfig = computed(() => store.output!.config as DatabaseOutputConfig)

const primaryKeyOptions = computed(() => {
  return (store.output!.config as DatabaseOutputConfig).columns
    .filter((c: ColumnMappingItem) => c.source)
    .map((c: ColumnMappingItem) => ({ label: c.target || c.source, value: c.target || c.source }))
})

/** SchemaForm update:modelValue 回调：可变更新，保留 config 对象引用。 */
function onSchemaUpdate(updated: Record<string, unknown>): void {
  Object.assign(store.output!.config, updated)
}
</script>
