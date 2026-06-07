import { useWizardStore } from '../stores/wizard'
import { useAiApi } from './useWizardApi'
import type { GuideResponse } from '../types/wizard'

const STEP_CATEGORY_MAP: Record<number, string> = {
  1: 'scene',
  2: 'chat',
  3: 'sql',
  4: 'mapping',
  5: 'chat',
}

export function useAiGuide() {
  const store = useWizardStore()
  const { askSuggestion } = useAiApi()

  function parseGuideResponse(aiText: string): GuideResponse {
    // Try markdown code block
    let jsonMatch = aiText.match(/```json\s*([\s\S]*?)\s*```/)
    if (!jsonMatch) {
      // Try bare JSON object
      jsonMatch = aiText.match(/\{[\s\S]*"message"[\s\S]*\}/)
    }
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[1] || jsonMatch[0])
        return {
          message: parsed.message || aiText,
          actions: parsed.actions,
          prefill: parsed.prefill,
        }
      } catch { /* fall through */ }
    }
    return { message: aiText }
  }

  async function startGuide(userInput: string): Promise<GuideResponse> {
    const content = await askSuggestion('scene', {
      current_step: 1,
      description: userInput,
    })
    if (!content) {
      return { message: '抱歉，AI 暂时不可用。你可以手动填写表单，或者先去设置页配置 AI。' }
    }
    const guide = parseGuideResponse(content)
    if (!guide.prefill) {
      guide.prefill = { 'scene.name': extractSceneName(userInput) }
    }
    return guide
  }

  function buildStepPrompt(step: number, ctx: Record<string, any>): string {
    const scene = ctx.scene_name || ctx.user_intent || ''
    const desc = ctx.scene_description || ''
    const inputCount = ctx.inputs_count || 0
    const procCount = ctx.processors_count || 0

    switch (step) {
      case 2:
        return (
          `## 当前步骤：第 2 步 — 输入源配置\n\n` +
          `用户正在配置数据流水线的输入源。这是第 2 步（共 5 步）。\n\n` +
          `## 场景上下文\n` +
          `- 场景名称：${scene}\n` +
          `- 场景描述：${desc}\n` +
          `- 已添加输入源：${inputCount} 个\n\n` +
          `## 你的任务\n` +
          `1. **仔细分析场景名称和描述**，识别其中提到的数据表、文件、数据来源\n` +
          `2. 如果用户提到了具体的表名（如"订单表""用户表""销售数据"），逐一提出来\n` +
          `3. 告诉用户你分析到了哪些数据源，并询问每个数据源的类型\n\n` +
          `## 引导策略\n` +
          `- 如果还没有添加任何输入源：先说"我分析你的场景涉及 X 个数据源"，逐一列举，然后引导添加第一个\n` +
          `- 如果已经添加了一些输入源：确认已添加的，询问是否还有遗漏\n` +
          `- 推荐的输入类型按常见度排序：Excel > CSV > 数据库\n\n` +
          `## 回复格式（JSON）\n` +
          `{\n` +
          `  "message": "引导消息（先分析场景中的数据源，再引导用户选择类型）",\n` +
          `  "actions": [\n` +
          `    {"label": "📊 Excel 文件", "value": "excel"},\n` +
          `    {"label": "🗄 CSV 文件", "value": "csv"},\n` +
          `    {"label": "🔌 数据库", "value": "database"}\n` +
          `  ]\n` +
          `}\n\n` +
          `## 示例消息\n` +
          `"我分析了你的场景「${scene}」，识别到 2 个数据源：\n` +
          `1. **订单表** — 包含订单信息\n` +
          `2. **用户表** — 包含用户信息\n\n` +
          `我们先配置第一个。订单表的数据在哪里？"` +
          `\n\n## 注意\n` +
          `- 如果用户明确提到了数据库（如MySQL、PostgreSQL），应直接推荐数据库类型\n` +
          `- 如果场景描述模糊，主动询问"你的数据是从Excel文件、CSV文件还是数据库来的？"`
        )
      case 3:
        return (
          `## 当前步骤：第 3 步 — 处理步骤配置\n\n` +
          `用户正在配置数据处理逻辑。这是第 3 步（共 5 步）。\n\n` +
          `## 场景上下文\n` +
          `- 场景名称：${scene}\n` +
          `- 场景描述：${desc}\n` +
          `- 已添加输入源：${inputCount} 个\n` +
          `- 已添加处理器：${procCount} 个\n\n` +
          `## 你的任务\n` +
          `1. **分析场景需要的数据处理逻辑**：JOIN关联？GROUP BY分组？聚合计算？过滤条件？\n` +
          `2. 推荐使用 SQL 处理器（适合表格数据处理）还是 Python 处理器（适合复杂脚本）\n` +
          `3. 如果场景逻辑清晰，直接生成 SQL 代码建议并解释逻辑\n\n` +
          `## 引导策略\n` +
          `- 无处理器时：分析场景逻辑，推荐处理方式，引导用户选择 SQL 或 Python\n` +
          `- 有处理器时：询问是否需要修改代码，或添加更多处理步骤\n` +
          `- 代码中标注假设（如关联字段名），提醒用户核对\n\n` +
          `## 回复格式（JSON）\n` +
          `{\n` +
          `  "message": "引导消息（分析处理逻辑 + 建议）",\n` +
          `  "actions": [\n` +
          `    {"label": "🧪 用 SQL 处理", "value": "pick_sql", "style": "primary"},\n` +
          `    {"label": "🐍 用 Python 处理", "value": "pick_python"}\n` +
          `  ]\n` +
          `}\n\n` +
          `## 示例消息\n` +
          `"分析你的场景「${scene}」，数据处理逻辑是：\n` +
          `1. 将订单表和用户表通过用户ID关联（JOIN）\n` +
          `2. 按城市分组（GROUP BY city）\n` +
          `3. 统计每个城市的订单数和总金额（COUNT + SUM）\n\n` +
          `我建议用 SQL 实现，代码已生成在下方。你检查一下，特别是关联字段名是否正确。"`
        )
      case 4:
        return (
          `## 当前步骤：第 4 步 — 输出配置\n\n` +
          `用户正在配置数据输出方式。这是第 4 步（共 5 步）。\n\n` +
          `## 场景上下文\n` +
          `- 场景名称：${scene}\n` +
          `- 已添加输入源：${inputCount} 个\n` +
          `- 已添加处理器：${procCount} 个\n` +
          `- 当前输出类型：${ctx.output_plugin || '未选择'}\n\n` +
          `## 你的任务\n` +
          `1. 根据场景判断最佳输出格式（Excel适合报表，CSV适合数据交换，数据库适合持久化）\n` +
          `2. 确认输出文件名和格式\n` +
          `3. 引导用户完成列映射（AI自动映射 + 用户确认）\n\n` +
          `## 回复格式（JSON）\n` +
          `{\n` +
          `  "message": "引导消息",\n` +
          `  "actions": [{"label": "✅ 确认", "value": "confirm", "style": "primary"}]\n` +
          `}`
        )
      default:
        return `当前步骤：第 ${step} 步。场景：${scene}。请根据上下文引导用户完成此步骤。`
    }
  }

  async function stepGuide(step: number, context: Record<string, any>): Promise<GuideResponse> {
    const category = STEP_CATEGORY_MAP[step] || 'chat'

    const instruction = buildStepPrompt(step, context)
    const enhancedContext = {
      current_step: step,
      ...context,
      instruction,
    }

    const content = await askSuggestion(category, enhancedContext)
    if (!content) {
      return { message: 'AI 暂不可用，请手动完成此步骤。' }
    }
    return parseGuideResponse(content)
  }

  function extractSceneName(userInput: string): string {
    return userInput.length > 30 ? userInput.slice(0, 30) + '...' : userInput
  }

  return { parseGuideResponse, startGuide, stepGuide, extractSceneName }
}
