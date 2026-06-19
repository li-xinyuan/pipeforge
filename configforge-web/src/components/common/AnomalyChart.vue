<template>
  <div v-if="anomalies.length" class="anomaly-chart">
    <p class="anomaly-chart__label">数据质量概览</p>
    <div class="anomaly-chart__bars">
      <div
        v-for="item in chartData"
        :key="item.column"
        class="anomaly-chart__row"
      >
        <span class="anomaly-chart__col-name" :title="item.column">{{ item.column }}</span>
        <div class="anomaly-chart__bar-track">
          <div
            class="anomaly-chart__bar-fill"
            :class="item.barClass"
            :style="{ width: item.pct + '%' }"
          />
        </div>
        <span class="anomaly-chart__pct" :class="item.barClass">{{ item.pctText }}</span>
        <span v-if="item.anomaly" class="anomaly-chart__tag" :class="'anomaly-chart__tag--' + item.anomaly.severity">
          {{ item.anomaly.label }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface AnomalyItem {
  type: string
  column: string
  detail: string
  severity: 'error' | 'warning' | 'info'
}

const props = defineProps<{
  anomalies: AnomalyItem[]
  stats?: Record<string, Record<string, number>>
}>()

const ANOMALY_LABELS: Record<string, string> = {
  null_rate_spike: '空值异常',
  value_range: '数值异常',
  row_count: '行数异常',
  duplicate: '重复异常',
  format: '格式异常',
  type_mismatch: '类型异常',
}

interface ChartRow {
  column: string
  pct: number
  pctText: string
  barClass: string
  anomaly: { label: string; severity: string } | null
}

const chartData = computed<ChartRow[]>(() => {
  const nullRates = props.stats?.null_rates || {}
  const anomalyMap = new Map<string, AnomalyItem>()
  for (const a of props.anomalies) {
    anomalyMap.set(a.column, a)
  }

  // Build rows from null_rates stats if available, otherwise from anomalies
  const columns = new Set<string>()
  for (const col of Object.keys(nullRates)) columns.add(col)
  for (const a of props.anomalies) columns.add(a.column)

  const rows: ChartRow[] = []
  for (const col of columns) {
    const rate = nullRates[col] ?? -1
    const anomaly = anomalyMap.get(col)
    const hasRate = rate >= 0
    const pct = hasRate ? Math.min(Math.round(rate * 100), 100) : (anomaly ? 80 : 0)
    const pctText = hasRate ? `${pct}%` : ''
    let barClass = 'anomaly-chart__bar-fill--ok'
    if (anomaly) {
      barClass = anomaly.severity === 'error'
        ? 'anomaly-chart__bar-fill--error'
        : 'anomaly-chart__bar-fill--warning'
    } else if (hasRate && pct > 50) {
      barClass = 'anomaly-chart__bar-fill--warning'
    }

    rows.push({
      column: col,
      pct,
      pctText,
      barClass,
      anomaly: anomaly ? { label: ANOMALY_LABELS[anomaly.type] || anomaly.type, severity: anomaly.severity } : null,
    })
  }

  // Sort: anomaly columns first, then by null rate descending
  rows.sort((a, b) => {
    if (a.anomaly && !b.anomaly) return -1
    if (!a.anomaly && b.anomaly) return 1
    return b.pct - a.pct
  })

  return rows
})
</script>

<style scoped>
.anomaly-chart {
  margin-top: 10px;
  border-top: 1px solid var(--color-border-light);
  padding-top: 10px;
}

.anomaly-chart__label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin: 0 0 8px;
}

.anomaly-chart__bars {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.anomaly-chart__row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.anomaly-chart__col-name {
  font-size: 12px;
  color: var(--color-text);
  width: 80px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.anomaly-chart__bar-track {
  flex: 1;
  height: 14px;
  background: var(--color-surface-hover);
  border-radius: 3px;
  overflow: hidden;
  min-width: 60px;
}

.anomaly-chart__bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
  min-width: 2px;
}

.anomaly-chart__bar-fill--ok {
  background: #22c55e;
}

.anomaly-chart__bar-fill--warning {
  background: #f59e0b;
}

.anomaly-chart__bar-fill--error {
  background: #ef4444;
}

.anomaly-chart__pct {
  font-size: 11px;
  font-weight: 500;
  width: 36px;
  text-align: right;
  flex-shrink: 0;
}

.anomaly-chart__pct.anomaly-chart__bar-fill--ok {
  color: #22c55e;
}

.anomaly-chart__pct.anomaly-chart__bar-fill--warning {
  color: #f59e0b;
}

.anomaly-chart__pct.anomaly-chart__bar-fill--error {
  color: #ef4444;
}

.anomaly-chart__tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
  flex-shrink: 0;
  white-space: nowrap;
}

.anomaly-chart__tag--error {
  background: rgba(239, 68, 68, 0.12);
  color: #dc2626;
}

.anomaly-chart__tag--warning {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
}

.anomaly-chart__tag--info {
  background: rgba(59, 130, 246, 0.12);
  color: #2563eb;
}

:root.dark .anomaly-chart__tag--error {
  color: #fca5a5;
}

:root.dark .anomaly-chart__tag--warning {
  color: #fcd34d;
}

:root.dark .anomaly-chart__tag--info {
  color: #93c5fd;
}
</style>
