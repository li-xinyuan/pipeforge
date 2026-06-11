<template>
  <div class="guide-panel" :class="{ 'guide-panel--collapsed': collapsed }">
    <!-- Collapsed strip -->
    <div v-if="collapsed" class="guide-panel__collapsed" @click="collapsed = false">
      <span class="guide-panel__collapsed-icon">📋</span>
    </div>

    <!-- Expanded panel -->
    <template v-else>
      <div class="guide-panel__header">
        <span class="guide-panel__header-title">配置向导</span>
        <button class="guide-panel__collapse-btn" @click.stop="collapsed = true" title="收起面板">◀</button>
      </div>

      <!-- Step indicator dots -->
      <div class="guide-panel__dots">
        <span
          v-for="s in 5"
          :key="s"
          class="guide-panel__dot"
          :class="{
            'guide-panel__dot--active': s === currentStep,
            'guide-panel__dot--done': s < currentStep,
          }"
        />
      </div>

      <!-- Step label -->
      <div class="guide-panel__step-label">{{ stepLabel }}</div>

      <!-- Tip content -->
      <div class="guide-panel__tip">
        <span class="guide-panel__tip-icon">💡</span>
        <span class="guide-panel__tip-text">{{ currentTip }}</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useWizardStore } from '../../stores/wizard'

const props = defineProps<{
  currentStep: number
}>()

const store = useWizardStore()
const collapsed = ref(false)

const stepLabels: Record<number, string> = {
  1: '步骤 1 · 场景信息',
  2: '步骤 2 · 输入源',
  3: '步骤 3 · 处理步骤',
  4: '步骤 4 · 输出配置',
  5: '步骤 5 · 预览与导出',
}

const stepLabel = computed(() => stepLabels[props.currentStep] || '配置向导')

const currentTip = computed(() => {
  const step = props.currentStep

  if (step === 1) {
    if (store.scene.name.trim()) {
      return '场景名称已填写 ✓ 点击「下一步」继续'
    }
    return '请填写场景名称，描述你想完成的数据处理任务。例如：\'销售报表生成\'、\'用户数据清洗\'\n\n版本号用于配置版本管理，默认 1.0 即可'
  }

  if (step === 2) {
    const hasFile = store.inputs.length > 0 && store.inputs.every(inp => inp.fileId)
    if (hasFile) {
      return '文件已上传 ✓ 系统已自动读取列信息。如需修改表名，点击表名旁的编辑图标。点击「下一步」继续。'
    }
    const hasDatabase = store.inputs.some(inp => inp.plugin === 'database')
    if (hasDatabase) {
      return '选择已配置的数据库连接，或前往「设置」页面添加新连接。输入表名后系统会自动读取列信息。'
    }
    if (store.inputs.length > 0) {
      return '请点击上传区域选择文件，或拖拽文件到上传区域。上传后系统会自动解析列信息。'
    }
    return '选择数据来源类型，然后上传对应文件。系统会自动读取列信息。\n\n• Excel：支持 .xlsx 文件，自动读取第一个工作表\n• CSV：支持 .csv 文件，自动识别分隔符\n• Database：从已有数据库连接读取数据'
  }

  if (step === 3) {
    const hasCode = store.processors.length > 0 && store.processors.every(p =>
      p.plugin === 'sql' ? p.sql.trim() : p.script.trim()
    )
    const hasOutput = store.processors.length > 0 && store.processors.every(p => p.outputTables.length > 0)
    if (hasCode && hasOutput) {
      return '代码已填写 ✓ 填写输出表名后点击「下一步」继续。输出表名建议使用有意义的英文名，如 order_summary。'
    }
    if (store.processors.length > 0 && !hasCode) {
      return '请在代码编辑器中编写处理逻辑。输出表名是处理结果的临时表名，后续步骤会引用此表名。'
    }
    if (store.processors.length > 0) {
      return '请在代码编辑器中编写处理逻辑。输出表名是处理结果的临时表名，后续步骤会引用此表名。'
    }
    return '添加处理步骤来加工数据。\n\n常见 SQL 模式：\n• 统计：SELECT COUNT(*) AS total FROM 表名\n• 分组：SELECT 分类, COUNT(*) AS 数量 FROM 表名 GROUP BY 分类\n• 关联：SELECT a.*, b.* FROM 表1 a JOIN 表2 b ON a.id = b.id\n• 过滤：SELECT * FROM 表名 WHERE 条件\n\nPython 适合复杂逻辑，如自定义函数、正则处理等。'
  }

  if (step === 4) {
    const hasColumns = store.output?.config?.columns?.length
    if (hasColumns) {
      return '列映射已配置 ✓ 点击「下一步」继续。'
    }
    return '配置输出格式和列映射。\n\n1. 选择输出类型（Excel/CSV/Database）\n2. 点击「添加列映射」\n3. 将源列映射到目标列\n\n源列来自上一步 SQL 的 SELECT 字段。'
  }

  if (step === 5) {
    return '配置完成！检查 YAML 预览，确认无误后导出或执行。'
  }

  return ''
})
</script>

<style scoped>
.guide-panel {
  width: 280px;
  flex-shrink: 0;
  background: var(--color-surface);
  border-left: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.25s ease;
}

.guide-panel--collapsed {
  width: 36px;
}

/* Collapsed strip */
.guide-panel__collapsed {
  width: 36px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: var(--color-surface);
  border-left: 1px solid var(--color-border-light);
  transition: background 0.2s;
}

.guide-panel__collapsed:hover {
  background: var(--color-surface-hover);
}

.guide-panel__collapsed-icon {
  font-size: 16px;
  writing-mode: vertical-lr;
  letter-spacing: 2px;
}

/* Header */
.guide-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--color-border-light);
}

.guide-panel__header-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
}

.guide-panel__collapse-btn {
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 12px;
  padding: 4px;
  border-radius: var(--radius-sm);
  transition: color 0.2s, background 0.2s;
}

.guide-panel__collapse-btn:hover {
  color: var(--color-text);
  background: var(--color-surface-hover);
}

/* Step dots */
.guide-panel__dots {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 14px 6px;
}

.guide-panel__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-border);
  transition: background 0.2s, transform 0.2s;
}

.guide-panel__dot--active {
  background: var(--color-primary);
  transform: scale(1.3);
}

.guide-panel__dot--done {
  background: var(--color-primary-light);
}

/* Step label */
.guide-panel__step-label {
  text-align: center;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  padding: 0 14px 14px;
}

/* Tip content */
.guide-panel__tip {
  display: flex;
  gap: 8px;
  padding: 14px;
  margin: 0 10px 14px;
  background: linear-gradient(135deg, var(--color-primary-bg), var(--color-primary-bg-light));
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
}

.guide-panel__tip-icon {
  font-size: 16px;
  flex-shrink: 0;
  line-height: 1.5;
}

.guide-panel__tip-text {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  line-height: 1.6;
}

/* Responsive */
@media (max-width: 767px) {
  .guide-panel {
    width: 220px;
  }
  .guide-panel--collapsed {
    width: 32px;
  }
}
</style>
