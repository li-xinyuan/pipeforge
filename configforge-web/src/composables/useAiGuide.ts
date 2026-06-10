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
    // Try extracting from JSON block or bare JSON
    let jsonMatch = aiText.match(/```json\s*([\s\S]*?)\s*```/)
    if (!jsonMatch) {
      jsonMatch = aiText.match(/\{[\s\S]*"(?:message|response)"[\s\S]*\}/)
    }
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[1] || jsonMatch[0])
        // Accept both "message" and "response" keys
        const msg = parsed.message || parsed.response || ''
        return {
          message: msg ? cleanMessage(msg) : cleanMessage(aiText),
          actions: parsed.actions,
          prefill: parsed.prefill,
        }
      } catch {
        return { message: cleanMessage(aiText) }
      }
    }
    return { message: cleanMessage(aiText) }
  }

  function cleanMessage(text: string): string {
    if (!text) return ''
    return text
      .replace(/\{[^}]{0,300}"(?:message|response|actions|prefill)"[^}]{0,500}\}/g, '')
      .replace(/```[\s\S]*?```/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim()
  }

  async function startGuide(userInput: string): Promise<GuideResponse> {
    const content = await askSuggestion('scene', {
      current_step: 1,
      description: userInput,
    })
    if (!content) {
      // AI unavailable — give clear manual instruction
      return {
        message: '场景名称已根据你的描述自动填入。你可以完善场景描述，或直接点击下方闪烁的「下一步」按钮进入输入源配置。',
        actions: [{ label: '✅ 确认，下一步', value: 'confirm', style: 'primary' }],
        prefill: { 'scene.name': extractSceneName(userInput) },
      }
    }
    const guide = parseGuideResponse(content)
    if (!guide.prefill) {
      guide.prefill = { 'scene.name': extractSceneName(userInput) }
    }
    // Ensure actions exist for Step 1
    if (!guide.actions || guide.actions.length === 0) {
      guide.actions = [{ label: '✅ 确认，下一步', value: 'confirm', style: 'primary' }]
    }
    return guide
  }

  // ============================================================
  // 步骤专用提示词构建器
  // ============================================================

  function buildStepPrompt(step: number, ctx: Record<string, any>): string {
    const scene = ctx.scene_name || ctx.user_intent || ''
    const desc = ctx.scene_description || ''
    const inputs = ctx.inputs_detail || []
    const inputCount = ctx.inputs_count || 0
    const procCount = ctx.processors_count || 0
    const procDetail = ctx.processors_detail || []
    const uploadedFiles = ctx.uploaded_files_detail || []
    const outputPlugin = ctx.output_plugin || ''

    switch (step) {
      case 2: return buildStep2Prompt(scene, desc, inputs, inputCount, uploadedFiles)
      case 3: return buildStep3Prompt(scene, desc, inputs, inputCount, uploadedFiles, procCount)
      case 4: return buildStep4Prompt(scene, desc, inputs, inputCount, procCount, procDetail, outputPlugin)
      default: return `当前步骤：第 ${step} 步。场景：${scene}。请根据上下文引导用户完成此步骤。`
    }
  }

  // ============================================================
  // Step 2: 输入源 — 深度分析
  // ============================================================
  function buildStep2Prompt(
    scene: string, desc: string,
    inputs: any[], inputCount: number,
    uploadedFiles: any[]
  ): string {
    // Only include Step 2 context — no other steps
    const hasInputs = inputCount > 0
    const addedDesc = hasInputs
      ? `已添加 ${inputCount} 个输入源：${inputs.map((i: any) => i.paramKey || i.table || '未命名').join('、')}`
      : '尚未添加任何输入源'

    const sceneInfo = desc
      ? `场景名称：${scene}。场景描述：${desc}`
      : `场景名称：${scene}`

    // Detect expected tables from scene name
    const tablesFromScene = detectTables(scene)

    return (
      `【严格指令 — 只执行以下内容，不要偏离】\n\n` +
      `用户正在配置数据流水线的第 2 步：输入源。\n` +
      `不要提及其他步骤（第3步、第4步等），只聚焦当前第2步。\n\n` +
      `场景信息（来自第1步）：\n${sceneInfo}\n\n` +
      `当前第2步状态：${addedDesc}\n\n` +
      (tablesFromScene.length > 0
        ? `我分析场景后识别到 ${tablesFromScene.length} 个数据源：${tablesFromScene.join('、')}\n`
        : '') +
      `你需要：\n` +
      (hasInputs
        ? `用户已添加了输入源。**关键**：仔细阅读 conversation_history——如果用户已经指定了哪个文件对应哪个表，绝对不要再问一遍！直接进入字段分析。\n` +
          `你需要：\n` +
          `1. 检查对话历史：用户是否已经确认了表对应关系？\n` +
          `2. 如果已确认：直接进入字段分析，告诉用户每个表应该包含哪些字段\n` +
          `3. 如果未确认：在 actions 中用中文按钮让用户选，例如 [{"label": "文件1是订单表，文件2是用户表", "value": "文件1是订单表，文件2是用户表"}]\n` +
          `   **禁止使用英文 value**（如 assign_orders、confirm_mapping），所有按钮文字和值都必须是中文\n` +
          `4. 检查场景需要几个输入源：缺了继续引导添加，够了就说"配置完成，点下一步"\n` +
          `5. **绝对不要**在确认对应关系上反复循环——一旦用户做了选择就推进\n`
        : `用户还没添加输入源。告诉用户根据场景分析需要哪些数据源，引导用户逐一添加。\n`) +
      `\n**严格要求：所有 label 和 value 必须是中文，禁止英文！**\n` +
      `同时，请在 prefill.knowledge.plan 中输出执行计划（用于进度条徽章显示）：\n` +
      `"plan": {"2": {"total": N, "items": ["表1", "表2"]}, "3": {"total": N, "items": ["关联+统计"]}, "4": {"total": 1, "items": ["Excel输出"]}}\n` +
      `【必须以 JSON 格式回复，禁止返回普通文本】\n` +
      `{"message": "你的引导消息（只谈第2步）", "actions": [{"label": "选项", "value": "xxx"}]}\n\n` +
      (hasInputs
        ? `actions 应包含：确认完成 或 继续添加的选项\n`
        : `actions 必须包含输入类型选项：Excel/CSV/数据库\n`) +
      `引导消息示例（无输入源时）：\n` +
      `"根据场景「${scene}」，你需要${tablesFromScene.length > 0 ? tablesFromScene.length + '个数据源：' + tablesFromScene.join('、') : '数据输入源'}。第一个是什么格式？"\n\n` +
      `引导消息示例（有输入源时）：\n` +
      `"好的，订单表已添加为Excel。根据你的场景，订单表应包含：订单ID、用户ID、金额、日期等字段。请上传文件。还需要添加用户表——它的格式是什么？"`
    )
  }

  /** Simple heuristic to detect table names from scene text */
  function detectTables(text: string): string[] {
    const matches = text.match(/[^\s，,。\.、]{2,8}(?:表|数据|文件)/g)
    if (!matches) return []
    return [...new Set(matches)]
  }

  // ============================================================
  // Step 3: 处理步骤 — 基于前两步的知识生成代码
  // ============================================================
  function buildStep3Prompt(
    scene: string, desc: string,
    inputs: any[], inputCount: number,
    uploadedFiles: any[], procCount: number
  ): string {
    const inputSummary = inputs.length > 0
      ? inputs.map((i: any) => `- ${i.name || '输入源'}：类型=${i.plugin}，列=[${(i.columns || []).join(', ')}]`).join('\n')
      : '（无输入源详情）'

    const fileSummary = uploadedFiles.length > 0
      ? uploadedFiles.map((f: any) => `- ${f.name}：${(f.columns || []).join(', ')}`).join('\n')
      : '（未上传文件）'

    return (
      `## 当前步骤：第 3 步 — 处理步骤配置\n\n` +
      `你已经完成了输入源配置。现在根据前面收集的信息，生成数据处理逻辑。\n\n` +
      `## 场景目标\n` +
      `场景名称：${scene}\n` +
      `场景描述：${desc}\n\n` +
      `## 输入源详情（来自步骤 2）\n${inputSummary}\n\n` +
      `## 文件列详情\n${fileSummary}\n\n` +
      `## 当前状态\n已添加处理器：${procCount} 个\n\n` +
      `## 你的任务（按优先级）\n\n` +
      `### 1. 分析处理逻辑\n` +
      `根据场景目标 + 输入源列信息，推断需要的数据处理步骤：\n` +
      `- 是否需要 JOIN？（多个表且有共同列 → 需要关联）\n` +
      `- 是否需要 GROUP BY？（"按XX统计/分组"→ 需要分组）\n` +
      `- 需要哪些聚合函数？（"统计""求和""计数""平均"）\n` +
      `- 是否需要过滤条件？（"大于""排除""只保留"）\n` +
      `- 是一个 SQL 步骤能完成，还是需要多个步骤？\n\n` +
      `### 2. 生成处理方案\n` +
      `把分析结果组织成一个清晰的处理方案：\n` +
      `- 步骤 A：做什么（如"关联两表"）→ 用什么实现（SQL/Python）→ 关键逻辑\n` +
      `- 步骤 B：做什么（如"分组聚合"）→ 用什么实现\n` +
      `- ...\n` +
      `- 每个步骤标注：输入表 → 输出表、使用的列、假设的关联字段\n\n` +
      `### 3. 询问用户确认\n` +
      `把方案总结成简洁的文字，让用户确认。\n` +
      `如果有不确定的地方（如关联字段名不确定），用选择题让用户选。\n\n` +
      `**严格要求：所有 label 和 value 必须是中文，禁止使用英文单词！**\n\n` +
      `## 回复格式（JSON）\n` +
      `{\n` +
      `  "message": "处理方案说明",\n` +
      `  "actions": [\n` +
      `    {"label": "使用 SQL 实现上述方案", "value": "pick_sql", "style": "primary"},\n` +
      `    {"label": "使用 Python 实现上述方案", "value": "pick_python"}\n` +
      `  ],\n` +
      `  "prefill": {\n` +
      `    "sql": "完整的 SQL 代码（可直接执行）",\n` +
      `    "output_tables": ["输出表名"]\n` +
      `  }\n` +
      `}\n\n` +
      `注意：prefill.sql 必须包含完整可执行的 SQL 代码，不要省略。\n\n` +
      `## 示例消息\n` +
      `"根据你的输入源，我设计了处理方案：\n\n` +
      `**步骤 1：关联两表**\n` +
      `- 用 SQL JOIN 将订单表（o）和用户表（u）关联\n` +
      `- 关联条件：我假设是 o.user_id = u.id（如不对请告诉我）\n` +
      `- 输出表：joined_data\n\n` +
      `**步骤 2：分组统计**\n` +
      `- GROUP BY u.city，计算 COUNT(o.id) 和 SUM(o.amount)\n` +
      `- 输出表：city_stats\n\n` +
      `总共 2 个处理步骤，都用 SQL 实现。方案对吗？"`
    )
  }

  // ============================================================
  // Step 4: 输出配置 — 综合前三步推荐
  // ============================================================
  function buildStep4Prompt(
    scene: string, desc: string,
    inputs: any[], inputCount: number,
    procCount: number, procDetail: any[],
    outputPlugin: string
  ): string {
    const procSummary = procDetail.length > 0
      ? procDetail.map((p: any) => `- ${p.plugin}：输出表=[${(p.outputTables || []).join(', ')}]`).join('\n')
      : `${procCount} 个处理步骤`

    return (
      `## 当前步骤：第 4 步 — 输出配置\n\n` +
      `前三个步骤已完成，现在配置最终输出。\n\n` +
      `## 场景目标\n` +
      `场景名称：${scene}\n` +
      `场景描述：${desc}\n\n` +
      `## 前面的总结\n` +
      `- 输入源：${inputCount} 个\n` +
      `- 处理步骤：${procCount} 个\n${procSummary}\n` +
      `- 当前输出类型：${outputPlugin || '未选择'}\n\n` +
      `## 你的任务\n\n` +
      `### 1. 推荐输出格式\n` +
      `根据场景目标推荐最佳输出格式：\n` +
      `- 场景提到"导出 Excel"→ Excel，带模板可选\n` +
      `- 场景提到"导出 CSV"→ CSV\n` +
      `- 场景提到"写入数据库"→ 数据库\n` +
      `- 未明确指定 → 根据数据类型推荐（报表用 Excel，数据交换用 CSV）\n\n` +
      `### 2. 列映射建议\n` +
      `处理步骤的输出列自动映射到输出文件的列：\n` +
      `- 列出处理步骤的最终输出列\n` +
      `- 建议哪些列需要重命名（中文友好名）\n` +
      `- 确认是否有遗漏\n\n` +
      `### 3. 选择题确认\n` +
      `对于需要用户决策的事情，全部用选择题：\n` +
      `- 输出格式选择\n` +
      `- 文件名确认\n` +
      `- 是否需要模板\n` +
      `- 是否需要数据检查点\n\n` +
      `## 回复格式（JSON）\n` +
      `{\n` +
      `  "message": "推荐方案 + 选择题",\n` +
      `  "actions": [选择题按钮]\n` +
      `}\n\n` +
      `## 示例消息\n` +
      `"根据场景「${scene}」，我推荐：\n` +
      `- 输出格式：📊 Excel（你提到了导出Excel）\n` +
      `- 文件名：订单城市统计-{{date}}.xlsx\n` +
      `- 输出列：城市、订单数、总金额\n\n` +
      `还需要调整吗？"`
    )
  }

  // ============================================================

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
