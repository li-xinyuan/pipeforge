# AI 引导式配置实现计划 — 审查报告

> 审查日期：2026-06-07
> 审查对象：`docs/superpowers/plans/2026-06-07-ai-guided-configuration-impl.md`（v2）
> 审查结论：**v1 的 6 个 Bug + 5 个设计问题 + 4 个遗漏项已基本修正，v2 存在 2 个残留 Bug + 3 个小问题**

---

## 一、总体评价

| 维度 | v1 评价 | v2 评价 | 变化 |
|------|--------|--------|------|
| 任务拆分 | ✅ 合理（13 Task） | ✅ 合理（16 Task） | +3 Task 补充遗漏项 |
| 测试覆盖 | ✅ 良好 | ✅ 良好 | 对话历史隔离新增测试 |
| 代码假设 | ❌ 6 处不符 | ⚠️ 2 处残留 | 大幅改善 |
| 与现有功能兼容 | ⚠️ 部分冲突 | ✅ 已处理 | 编排模式共存、?prompt= 统一 |
| 设计规格覆盖 | ⚠️ 4 项遗漏 | ✅ 已补充 | +Task 13/14/15 |

---

## 二、v1 问题修正状态

### Bug 级问题

| # | v1 问题 | v2 状态 | 说明 |
|---|--------|--------|------|
| Bug 1 | useAiStatus 描述错误 | ✅ 已修正 | Task 2 描述改为"已经是模块级，需改进为三态" |
| Bug 2 | ChatMessage 行号错误 | ✅ 已修正 | Task 1 标注 `wizard.ts:34-39`，保留 `code` 字段 |
| Bug 3 | useAiGuide 直接 fetch | ✅ 已修正 | Task 5 改用 `useAiApi().askSuggestion` |
| Bug 4 | 正则 `(?i)AS` 语法错误 | ✅ 已修正 | Task 10 改为 `/\s+AS\s+/i` |
| Bug 5 | currentStep 重复定义 | ✅ 已修正 | Task 8 注释"复用现有的 currentStep（第 209 行已定义）" |
| Bug 6 | Step2InputView 是旧页面 | ✅ 已修正 | Task 9 改为修改 `InputSourceList.vue` + `ConfigWizardView` |

### 设计问题

| # | v1 问题 | v2 状态 | 说明 |
|---|--------|--------|------|
| 设计 1 | 编排模式共存 | ✅ 已修正 | Task 8 新增 `aiQuickActions` 计算属性，guide 模式下隐藏编排 |
| 设计 2 | ?guide= 与 ?prompt= 冲突 | ✅ 已修正 | Task 8 注释"替换现有 ?prompt= 参数，统一为 ?guide=" |
| 设计 3 | 对话历史按配置隔离 | ✅ 已修正 | Task 4 key 改为 `configforge-chat-history-${configId}`，新增隔离测试 |
| 设计 4 | startGuide 防重复 | ✅ 已修正 | Task 8 新增 `guideInitialized` guard + 恢复历史逻辑 |
| 设计 5 | completeStep 冲突 | ✅ 已修正 | Task 11 注释"在现有 completeStep 中追加"，保留原有逻辑 |

### 遗漏项

| # | v1 问题 | v2 状态 | 说明 |
|---|--------|--------|------|
| 遗漏 1 | AI 填写视觉标记 | ✅ 已补充 | 新增 Task 13 |
| 遗漏 2 | translate-checkpoint | ✅ 已补充 | 新增 Task 14 |
| 遗漏 3 | 5 秒追加提示 | ✅ 已补充 | Task 15 Step 1 |
| 遗漏 4 | 暗色模式 | ✅ 已补充 | Task 15 Step 2 |

### 小问题

| # | v1 问题 | v2 状态 |
|---|--------|--------|
| 1 | onVoicePlaceholder 空函数 | ✅ 已修正（添加 `message.info`） |
| 2 | store.scene.name 直接赋值 | 未明确修正，但 `SceneInfo.name` 是 string 可写，实际无问题 |
| 3 | renderMsgContent v-html XSS | ✅ 已修正（手动转义 HTML） |
| 4 | buildStepContext 泄露敏感信息 | ✅ 已修正（注释"不暴露 fileId/连接字符串"） |
| 5 | existing_prompt_logic 不存在 | ✅ 已修正（改为 `_build_prompt`） |
| 6 | 验证清单缺手动创建 | ✅ 已修正（Task 16 新增 14 项验证） |
| 7 | 打字机效果 | ⚠️ 未处理（见残留问题 3） |
| 8 | applyPrefill 只处理 Step 1 | ⚠️ 未处理（见残留问题 2） |

---

## 三、v2 残留问题

### 残留 Bug 1：Task 2 代码重复声明 `checking`

**Task 2 Step 1 代码**（第 108-109 行）：

```typescript
const checking = ref(false)
const checking = ref(false)  // ← 重复声明
```

两行完全相同的 `const checking = ref(false)`，TypeScript 会报 `Cannot redeclare block-scoped variable 'checking'`。

**修正**：删除第 109 行的重复声明。

---

### 残留 Bug 2：Task 5 的 `useAiApi` 导入路径可能错误

**Task 5 Step 3 代码**（第 405 行）：

```typescript
import { useAiApi } from './useWizardApi'
```

但项目中 `useAiApi` 的实际文件名需要确认。根据搜索结果，现有代码中 AI API 调用分散在 `ConfigWizardView.vue` 和 `Step2InputView.vue` 中，可能没有独立的 `useAiApi` composable 文件。

**建议**：确认 `useWizardApi.ts` 是否存在。如果不存在，需要：
1. 先从 `ConfigWizardView.vue` 中提取 `askSuggestion` 等方法为独立 composable
2. 或者直接在 `useAiGuide.ts` 中 import `ConfigWizardView` 中已有的 AI 调用逻辑

---

### 残留问题 3：guide 模式消息缺少打字机效果

**现有 `AiChatPanel.vue`** 有完整的打字机效果（`typedTexts`、`startTyping`、`stopTyping`、`getDisplayContent`，第 96-131 行），AI 消息逐字显示。

**计划 Task 7** 的 guide 模式模板中，AI 消息直接用 `v-html="renderMsgContent(msg)"` 渲染，没有打字机效果。两种模式下 AI 消息的显示体验不一致。

**建议**：在 guide 模式中复用现有打字机效果，或至少在最后一条 AI 消息上启用逐字显示。

---

### 残留问题 4：`applyPrefill` 只处理 Step 1，Step 2/3/4 缺失

**Task 8 的 `applyPrefill` 函数**只处理 Step 1 的 `scene.name` 和 `scene.description`。Step 2/3/4 的 prefill 逻辑标注为"在 Task 9 处理"，但 Task 9 只处理了输入类型选择（通过 `onGuideAction`），没有处理 prefill。

Step 3 和 Step 4 的 prefill 场景：
- Step 3：AI 生成 SQL 代码 → 需要写入 `store.processors[0].sql`
- Step 4：AI 自动列映射 → 需要写入 `store.output.config.columns`

**建议**：在 `applyPrefill` 中补充 Step 3/4 的处理，或在 Task 14（translate-checkpoint）之后新增一个 Task 专门处理 Step 3/4 的 prefill 应用。

---

### 残留问题 5：Task 6 的 `store.scene.name` 赋值与 `startGuide` 重复

**Task 6 Step 2**：

```typescript
function startAiGuide() {
  store.scene.name = promptText.value.trim()  // ← 手动赋值
  router.push('/config/new?guide=' + ...)
}
```

**Task 8 Step 2**：

```typescript
// startGuide 返回后
if (result.prefill) applyPrefill(result.prefill, 1)
// applyPrefill 中
store.scene.name = prefill['scene.name']  // ← AI 赋值
```

场景名称被赋值了两次：第一次在首页手动赋值（取前 30 字符），第二次在 `applyPrefill` 中被 AI 返回值覆盖。如果 AI 返回了不同的场景名称，首页赋值就浪费了。

**建议**：Task 6 中只将文字通过 URL 参数传递，不在首页赋值 `store.scene.name`。由 Task 8 的 `startGuide` → `applyPrefill` 统一处理。如果 AI 不可用，再 fallback 到首页文字。

---

## 四、v2 修正建议汇总

| 优先级 | 问题 | 修正建议 |
|--------|------|---------|
| **P0** | 残留 Bug 1: checking 重复声明 | 删除第 109 行重复的 `const checking = ref(false)` |
| **P1** | 残留 Bug 2: useAiApi 导入路径 | 确认 `useWizardApi.ts` 是否存在，不存在则需先提取 |
| **P2** | 残留问题 3: guide 模式缺打字机效果 | 复用现有打字机逻辑，至少最后一条 AI 消息逐字显示 |
| **P2** | 残留问题 4: applyPrefill 只处理 Step 1 | 补充 Step 3（SQL 代码）和 Step 4（列映射）的 prefill |
| **P2** | 残留问题 5: scene.name 重复赋值 | Task 6 中移除 `store.scene.name = ...`，由 Task 8 统一处理 |

---

## 五、最终结论

| 类别 | v1 数量 | v2 已修正 | v2 残留 |
|------|--------|----------|--------|
| Bug 级 | 6 | 6 | 2（checking 重复 + 导入路径） |
| 设计问题 | 5 | 5 | 0 |
| 遗漏项 | 4 | 4 | 0 |
| 小问题 | 8 | 6 | 2（打字机效果 + applyPrefill） |

**计划已可进入开发阶段。** 残留的 2 个 Bug（checking 重复声明、导入路径确认）可在开发第一步修正，3 个 P2 问题可在开发中逐步补充。
