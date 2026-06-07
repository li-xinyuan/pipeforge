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
    const jsonMatch = aiText.match(/```json\s*([\s\S]*?)\s*```/)
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[1])
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
    const content = await askSuggestion('scene', { description: userInput })
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
    const content = await askSuggestion(category, { current_step: step, ...context })
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
