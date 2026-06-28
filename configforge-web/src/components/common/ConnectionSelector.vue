<template>
  <!--
    ConnectionSelector — 数据库连接选择命名 widget（限制①第三阶段迁移）。

    自包含组件：NSelect + ⚙管理按钮 + 内嵌 ConnectionManager modal。
    挂载时自动加载连接列表；modal 关闭后重新加载（捕获用户新建/编辑的连接）。

    通过 schema 的 x-ui-widget: 'connection-selector' 引用。
  -->
  <div>
    <label class="cf-label"><span class="cf-required">*</span> 数据库连接</label>
    <div class="flex items-center gap-2">
      <NSelect
        :value="modelValue"
        :options="(resolvedOptions as never)"
        placeholder="-- 选择连接 --"
        size="small"
        class="flex-1"
        :disabled="disabled"
        @update:value="$emit('update:modelValue', $event)"
      />
      <NButton size="small" quaternary :disabled="disabled" @click="showManager = true">⚙ 管理</NButton>
    </div>
    <p v-if="resolvedOptions.length === 0" class="text-xs text-amber-600 dark:text-amber-400 mt-1">
      暂无连接，点击"管理"按钮新建数据库连接
    </p>

    <!-- 内嵌连接管理 modal -->
    <div v-if="showManager" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="closeManager">
      <div class="bg-[var(--color-surface)] rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-base font-semibold">管理数据库连接</h3>
          <button class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300" aria-label="关闭" @click="closeManager">✕</button>
        </div>
        <ConnectionManager />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NSelect, NButton } from 'naive-ui'
import ConnectionManager from './ConnectionManager.vue'
import { useConnections } from '../../composables/useConnections'
import type { SelectOption } from '../../composables/widgetRegistry'

defineProps<{
  modelValue: string
  disabled?: boolean
}>()

defineEmits<{
  'update:modelValue': [value: string]
}>()

const showManager = ref(false)
const { connectionOptions, loadConnectionOptions } = useConnections()

/** 防御性 normalize：确保 value 为 string。 */
const resolvedOptions = computed<SelectOption[]>(() =>
  connectionOptions.value.map((o) => ({ label: o.label, value: String(o.value) }))
)

onMounted(() => {
  loadConnectionOptions()
})

async function closeManager(): Promise<void> {
  showManager.value = false
  // 重新加载连接列表，捕获用户在 modal 中新建/编辑的连接
  await loadConnectionOptions()
}
</script>
