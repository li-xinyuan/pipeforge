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

  async function stepGuide(step: number, context: Record<string, any>): Promise<GuideResponse> {
    const category = STEP_CATEGORY_MAP[step] || 'chat'

    // Build a richer context description for the AI
    let enhancedContext: Record<string, any> = { current_step: step, ...context }

    if (step === 2) {
      // Step 2: guide AI to analyze scene and suggest specific input sources
      const sceneName = context.scene_name || ''
      const userIntent = context.user_intent || sceneName
      enhancedContext = {
        ...enhancedContext,
        instruction: `用户正在配置数据流水线的第 2 步（输入源）。请根据用户的场景描述"${userIntent}"，分析需要哪些数据输入源（表/文件），并引导用户选择输入类型（Excel/CSV/数据库）。例如如果用户提到"订单表"和"用户表"，应提示"我分析到你需要 订单表 和 用户表 两个输入源，它们的数据格式是什么？"请用 JSON 格式回复，包含 message 和 actions 字段。actions 中建议包含 Excel/CSV/数据库三个选项让用户选择。`,
      }
    } else if (step === 3) {
      const sceneName = context.scene_name || ''
      const userIntent = context.user_intent || sceneName
      enhancedContext = {
        ...enhancedContext,
        instruction: `用户正在配置数据流水线的第 3 步（处理步骤）。请根据场景"${userIntent}"，分析需要什么样的数据处理逻辑，并引导用户选择 SQL 或 Python 处理器。`,
      }
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
