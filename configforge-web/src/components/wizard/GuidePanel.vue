<template>
  <div class="guide-panel" :class="{ 'guide-panel--collapsed': collapsed }">
    <!-- Collapsed strip -->
    <div v-if="collapsed" class="guide-panel__collapsed" @click="collapsed = false">
      <span class="guide-panel__collapsed-icon">🤖</span>
    </div>

    <!-- Expanded panel -->
    <template v-else>
      <div class="guide-panel__header">
        <span class="guide-panel__header-title">🤖 Forge · AI 助手</span>
        <button class="guide-panel__collapse-btn" title="收起面板" aria-label="收起面板" @click.stop="collapsed = true">◀</button>
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
const collapsed = ref(window.innerWidth <= 767)

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
      return '场景名称已填写 ✓\n\n简要描述你的数据处理目标，例如"按月统计各城市销售数据"。完成后点击「下一步」继续。'
    }
    return '请在左侧填写场景名称，描述你想完成的数据处理任务。\n\n好的命名示例：\n• 销售报表生成\n• 用户数据清洗\n• 月度财务汇总\n\n描述中建议说明：数据从哪来、怎么处理、输出什么格式。'
  }

  if (step === 2) {
    const hasFile = store.inputs.length > 0 && store.inputs.every(inp => inp.fileId)
    const hasAnalysis = store.inputs.some(inp => inp.confirmedAnalysis)
    if (hasFile && hasAnalysis) {
      return '文件已上传且 AI 分析完成 ✓\n\n检查表名和参数键是否正确，然后点击「下一步」继续。'
    }
    if (hasFile) {
      return '文件已上传 ✓\n\n点击文件卡片上的 ✨ AI 分析此文件，让 AI 帮你推荐表名、参数键和列类型。\n\n也可以手动填写表名后继续。'
    }
    const hasDatabase = store.inputs.some(inp => inp.plugin === 'database')
    if (hasDatabase) {
      return '选择已配置的数据库连接，或前往「设置」页面添加新连接。\n\n输入表名后系统会自动读取列信息。'
    }
    if (store.inputs.length > 0) {
      return '请点击上传区域选择文件，或拖拽文件到上传区域。\n\n上传后系统会自动解析列信息。'
    }
    return '选择数据来源类型，然后上传对应文件。\n\n• Excel：支持 .xlsx 文件\n• CSV：支持 .csv 文件，可自定义分隔符\n• Database：从数据库连接读取数据\n• JSON：支持 .json 文件，自动展平嵌套字段\n• XML：支持 .xml 文件，可指定行元素路径\n• Parquet：支持 .parquet 大数据文件\n• REST API：从 HTTP 接口拉取数据\n\n上传后可使用 ✨ AI 分析此文件 功能'
  }

  if (step === 3) {
    const hasCode = store.processors.length > 0 && store.processors.every(p =>
      p.plugin === 'sql' ? p.sql.trim() : p.script.trim()
    )
    const hasOutput = store.processors.length > 0 && store.processors.every(p => p.outputTables.length > 0)
    if (hasCode && hasOutput) {
      return '代码和输出表名已填写 ✓\n\n可以点击「▶ 预览结果」查看处理效果。确认无误后点击「下一步」继续。'
    }
    if (store.processors.length > 0 && !hasCode) {
      return '请在代码编辑器中编写处理逻辑。\n\n不确定怎么写？点击 ✨ AI 生成 SQL，用自然语言描述需求，AI 帮你生成代码。\n\n也可以点击「📋 SQL 模板」快速插入常用语句。'
    }
    if (store.processors.length > 0) {
      return '填写输出表名（处理结果的临时表名），后续步骤会引用此表名。\n\n建议使用有意义的英文名，如 order_summary。'
    }
    return '添加处理步骤来加工数据。\n\n• SQL：适合查询、过滤、聚合、关联\n• Python：适合复杂数据清洗、正则处理\n\n创建处理器后，点击 ✨ AI 生成 SQL 用自然语言描述需求，AI 将生成对应代码。\n\n也可以使用「📋 SQL 模板」快速插入常用语句。'
  }

  if (step === 4) {
    const hasColumns = store.output?.config?.columns?.length
    if (hasColumns) {
      return '列映射已配置 ✓\n\n检查映射是否正确，然后点击「下一步」继续。'
    }
    return '配置输出格式和列映射。\n\n1. 选择输出类型（Excel/CSV/Database）\n2. 列映射未完成时，点击 ✨ AI 推断列映射\n   AI 将根据处理步骤的输出列自动完成映射\n3. 也可以手动添加列映射\n\n源列来自上一步 SQL 的 SELECT 字段。'
  }

  if (step === 5) {
    return '配置完成！\n\n建议点击 ✨ AI 预检配置 检查完整性和潜在问题。\n\n确认无误后：\n• 下载 YAML 配置文件\n• 执行流水线查看结果\n• 保存配置以便复用\n• 保存为模板，方便下次快速创建'
  }

  return ''
})
</script>

<style scoped>
.guide-panel {
  width: 280px;
  flex-shrink: 0;
  background: linear-gradient(180deg, rgba(124,58,237,0.04), rgba(99,102,241,0.02), rgba(6,182,212,0.01));
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(124,58,237,0.12);
  border-radius: var(--radius-lg);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.04);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.25s ease;
  margin-left: 16px;
}

.guide-panel--collapsed { width: 36px; border-radius: var(--radius-lg); }

.guide-panel__collapsed {
  width: 36px; height: 100%;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  background: linear-gradient(180deg, rgba(124,58,237,0.04), rgba(99,102,241,0.02));
  border: 1px solid rgba(124,58,237,0.12);
  border-radius: var(--radius-lg);
  transition: background 0.2s;
}
.guide-panel__collapsed:hover { background: rgba(124,58,237,0.08); }
.guide-panel__collapsed-icon { font-size: 16px; writing-mode: vertical-lr; letter-spacing: 2px; }

.guide-panel__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(124,58,237,0.08);
  background: linear-gradient(135deg, rgba(124,58,237,0.06), rgba(99,102,241,0.03));
}
.guide-panel__header-title { font-size: 14px; font-weight: 600; color: var(--color-ai); }
.guide-panel__collapse-btn {
  background: none; border: none; color: var(--color-text-muted);
  cursor: pointer; font-size: 12px; padding: 4px; border-radius: var(--radius-sm);
  transition: color 0.2s, background 0.2s;
}
.guide-panel__collapse-btn:hover { color: var(--color-text); background: var(--color-surface-hover); }

.guide-panel__dots { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 14px 14px 6px; }
.guide-panel__dot { width: 8px; height: 8px; border-radius: 50%; background: var(--color-border); transition: background 0.2s, transform 0.2s; }
.guide-panel__dot--active { background: var(--color-ai); transform: scale(1.3); }
.guide-panel__dot--done { background: var(--color-ai-light); }

.guide-panel__step-label { text-align: center; font-size: var(--font-size-sm); font-weight: 500; color: var(--color-text-secondary); padding: 0 14px 14px; }

.guide-panel__tip {
  display: flex; gap: 8px; padding: 14px; margin: 0 10px 14px;
  background: linear-gradient(135deg, rgba(124,58,237,0.05), rgba(99,102,241,0.03));
  border: 1px solid rgba(124,58,237,0.15);
  border-radius: var(--radius-md);
}
.guide-panel__tip-icon { font-size: 16px; flex-shrink: 0; line-height: 1.5; }
.guide-panel__tip-text { font-size: var(--font-size-sm); color: var(--color-ai); line-height: 1.6; }

@media (max-width: 767px) {
  .guide-panel { width: 100%; border-left: none; border-top: 1px solid rgba(124,58,237,0.12); max-height: 200px; }
  .guide-panel--collapsed { width: 100%; height: 36px; }
  .guide-panel__collapsed { flex-direction: row; padding: 8px 12px; }
}

/* Dark mode */
[data-theme="dark"] .guide-panel {
  background: linear-gradient(180deg, rgba(124,58,237,0.08), rgba(99,102,241,0.04));
  border-color: rgba(124,58,237,0.2);
}
[data-theme="dark"] .guide-panel__header {
  background: linear-gradient(135deg, rgba(124,58,237,0.1), rgba(99,102,241,0.06));
  border-color: rgba(124,58,237,0.15);
}
[data-theme="dark"] .guide-panel__header-title { color: #c4b5fd; }
[data-theme="dark"] .guide-panel__tip {
  background: rgba(124,58,237,0.1);
  border-color: rgba(124,58,237,0.2);
}
[data-theme="dark"] .guide-panel__tip-text { color: #ddd6fe; }
</style>
