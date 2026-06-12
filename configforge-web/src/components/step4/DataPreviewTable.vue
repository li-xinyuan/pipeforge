<template>
  <div class="data-preview-table">
    <div v-if="columns.length === 0 || rows.length === 0" class="text-center py-8 text-slate-400 text-sm">
      暂无预览数据
    </div>
    <template v-else>
      <div class="flex items-center gap-3 mb-2">
        <span class="text-xs text-slate-400">{{ columns.length }} 列 / {{ rows.length }} 行</span>
      </div>
      <NDataTable
        :columns="tableColumns"
        :data="tableData"
        :pagination="pagination"
        :bordered="true"
        :single-line="false"
        size="small"
        :max-height="420"
        virtual-scroll
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { NDataTable } from 'naive-ui'
import type { DataTableColumns, DataTableProps } from 'naive-ui'

export interface DryRunTableData {
  table_name: string
  columns: string[]
  rows: string[][]
  total_rows: number
}

const props = defineProps<{
  columns: string[]
  rows: string[][]
  tableName?: string
}>()

const pagination = computed(() => ({
  pageSize: 10,
  showSizeChanger: false,
}))

const tableColumns = computed<DataTableColumns<Record<string, string>>>(() =>
  props.columns.map((col) => ({
    key: col,
    title: col,
    sorter: (a: Record<string, string>, b: Record<string, string>) => {
      const va = a[col] ?? ''
      const vb = b[col] ?? ''
      const na = Number(va)
      const nb = Number(vb)
      if (!isNaN(na) && !isNaN(nb)) return na - nb
      return String(va).localeCompare(String(vb), 'zh-CN')
    },
    render: (row: Record<string, string>) => {
      const val = row[col]
      if (val == null || String(val).trim() === '') {
        return h('span', { class: 'text-slate-300 italic text-xs' }, 'null')
      }
      return String(val)
    },
    ellipsis: { tooltip: true },
    minWidth: 80,
  }))
)

const tableData = computed(() =>
  props.rows.map((row, ri) => {
    const obj: Record<string, string> = { _key: String(ri) }
    props.columns.forEach((col, ci) => {
      obj[col] = row[ci] ?? ''
    })
    return obj
  })
)
</script>
