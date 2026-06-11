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
    return '请填写场景名称，描述你想完成的数据处理任务。例如：\'销售报表生成\'、\'用户数据清洗\''
  }

  if (step === 2) {
    const hasFile = store.inputs.length > 0 && store.inputs.every(inp => inp.fileId)
    if (hasFile) {
      return '文件已上传 ✓ 系统已自动读取列信息。点击「下一步」继续'
    }
    if (store.inputs.length > 0) {
      return '请点击上传区域选择文件，或拖拽文件到上传区域'
    }
    return '选择数据来源类型，然后上传对应文件。系统会自动读取列信息。'
  }

  if (step === 3) {
    const hasCode = store.processors.length > 0 && store.processors.every(p =>
      p.plugin === 'sql' ? p.sql.trim() : p.script.trim()
    )
    const hasOutput = store.processors.length > 0 && store.processors.every(p => p.outputTables.length > 0)
    if (hasCode && hasOutput) {
      return '代码已填写 ✓ 填写输出表名后点击「下一步」继续'
    }
    if (store.processors.length > 0) {
      return '请在代码编辑器中编写处理逻辑'
    }
    return '添加处理步骤来加工数据。SQL 适合查询统计，Python 适合复杂逻辑。'
  }

  if (step === 4) {
    const hasColumns = store.output?.config?.columns?.length
    if (hasColumns) {
      return '列映射已配置 ✓ 点击「下一步」继续'
    }
    return '配置输出格式和列映射。选择输出类型后，添加目标列并映射源列。'
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
