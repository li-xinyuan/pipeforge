import { ref, computed, type Ref } from 'vue'
import type { MessageApiInjection } from 'naive-ui/lib/message/src/MessageProvider'
import type { SavedConfig } from '../types/wizard'

interface UseBatchSelectOptions {
  configs: Ref<SavedConfig[]>
  deleteConfig: (id: string) => Promise<boolean>
  message: MessageApiInjection
  loadConfigList: () => void
}

export function useBatchSelect({ configs, deleteConfig, message, loadConfigList }: UseBatchSelectOptions) {
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

  return {
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
  }
}
