# ConfigForge 方案审查与代码扫描报告

> 审查日期：2026-06-14
> 审查对象：`docs/superpowers/reviews/2026-06-12-full-test-and-next-steps.md`
> 审查方法：全项目代码扫描 + 对比验证

---

## 一、总体判断

**方案方向正确，任务优先级合理。但报告中 3 项 P0/P1 问题已实际修复，建议更新报告后按更新后的任务清单执行。**

---

## 二、报告与实际代码对比验证

### 2.1 已修复的问题（报告需更新）

| # | 报告中的问题 | 当前实际状态 | 建议 |
|---|------------|-----------|------|
| S-1 | "插件注册不完整，只导入 3/7" | `pipeforge/__init__.py` 已导入全部 8 个插件（excel/csv/database 输入 + sql/python 处理器 + excel/csv/database 输出） | **从待修列表中移除** |
| S-2 | "requirements.txt 缺少 apscheduler/sqlalchemy/deepdiff" | 5 个依赖全部已声明：`sqlalchemy>=2.0`、`apscheduler>=3.10`、`deepdiff>=5.0`、`pymysql>=1.1.0`、`psycopg2-binary>=2.9.0` | **从待修列表中移除** |
| H-1 | "Database 输出前端未启用，UI 被禁用" | `OutputConfigTab.vue` 中 Database 卡片已验证：有 `cursor-pointer`、`@click`、正常 hover/active 样式（`border-amber-600`），可点击切换 | **从待修列表中移除** |

### 2.2 确认仍存在的问题

| # | 问题 | 当前状态确认 | 严重性 |
|---|------|-----------|--------|
| H-3 | 调度器无测试覆盖 | `configforge/tests/` 中无 scheduler 相关测试 | P1 |
| M-1 | 5 个旧版 View 文件孤立 | `Step1SceneView.vue`~`Step5ExportView.vue` 未在路由注册，属于死代码 | P2 |
| M-2 | 4 个 Composable 未使用 | `useColumnDiff.ts`、`useConversationHistory.ts`、`useTypewriter.ts`、`useErrorHandler.ts` 无引用 | P2 |
| M-3 | 3 个 AI 遗留组件 | `AiChatPanel.vue`、`AiInlineTip.vue`、`OrchestrationResult.vue` 在 `ConfigWizardView` 中已移除引用 | P2 |
| M-4 | 调度器无文件锁 | `scheduler.py` 的 `_load_schedules/_save_schedules` 使用普通 JSON 读写，无并发保护 | P2 |
| M-5 | 数据库输出 SQL 注入风险 | `database.py` 中 `source_table` 直接拼入 SQL | P2 |
| M-6 | MySQL 双引号不兼容 | `_quote()` 使用双引号，MySQL 默认需反引号 | P2 |
| M-7 | MySQL VALUES() 已弃用 | MySQL 8.0.20+ 不再支持 `ON DUPLICATE KEY UPDATE ... VALUES(col)` | P2 |
| M-9 | 3 个后端测试失败 | 分页 API 格式变更后测试未更新 | P1 |
| M-10 | 11 个前端测试失败 | happy-dom 网络请求超时 | P2 |

### 2.3 代码扫描额外发现

| # | 发现 | 文件 | 严重性 |
|---|------|------|--------|
| N-1 | `useAiGuide.ts` 无引用 | 仅被已移除 AI 流程的旧代码引用 | P2 |
| N-2 | `useAiStatus.ts` 被 `AiStatusBanner.vue` 重复实现了检测逻辑 | 两个文件各自维护 AI 状态 | P3 |
| N-3 | `DataPreviewTable.vue` 已实现但未在 ConfigWizardView Step 5 中集成 | 用户执行后看不到数据预览 | P1 |

---

## 三、阶段任务优先级评估

### 3.1 原报告建议 vs 当前实际优先级

| 原阶段 | 任务数 | 评估 | 调整建议 |
|--------|--------|------|---------|
| 阶段一（修复阻塞） | 4 项 | S-1、S-2 已不存在，实际只剩 2 项 | 合并到其他阶段，不单独占 1-2 天 |
| 阶段二（Database+预览） | 4 项 | H-1 已修复，H-2 已修复。**新增第 8 项应为 P1** | 保留 3 项核心任务 |
| 阶段三（清理死代码） | 4 项 | 方向正确 | 保留，注意 M-3 组件可能后续 AI 增强需要 |
| 阶段四（功能扩展） | 8 项 | 合理的长期规划 | 保留 |

### 3.2 建议调整后的执行顺序

**第一轮（1-2 天）：修复测试 + 关键 Bug**

| 序号 | 任务 | 说明 |
|------|------|------|
| 1 | 修复 3 个后端测试 | 更新 API 断言匹配分页格式 |
| 2 | 修复 MySQL 兼容性 | 反引号 `_quote()` + `VALUES()` → 别名 |
| 3 | 修复 SQL 注入 | `source_table` 使用 `safe_identifier` |
| 4 | replace 模式事务一致性 | DROP + INSERT 放在同一事务 |

**第二轮（2-3 天）：死代码清理 + 数据预览集成**

| 序号 | 任务 | 说明 |
|------|------|------|
| 5 | 删除死代码 | Step1-5 View + 4 个 Composable |
| 6 | 评估 AI 组件 | AiChatPanel/AiInlineTip 删除或保留（标记为后续 P4-3 用） |
| 7 | DataPreviewTable 集成 | Step 5 添加数据预览 |
| 8 | 调度器文件锁 | fcntl 保护 JSON 读写 |

**第三轮（按需）：功能扩展**

| 序号 | 任务 | 说明 |
|------|------|------|
| 9 | 调度器测试 | scheduler + schedules API 测试 |
| 10 | 执行监控 | WebSocket + 日志流 |
| 11 | 新用户 Onboarding | 首次引导 |

---

## 四、对 P4-3（AI 引导配置增强版）的建议

报告中 P4-3 标注为未完成，计划"基于固定提示的经验，重新设计 AI 辅助方案"。

**当前现状**：我们已经投入了大量精力实现了 GuidePanel + 固定提示 + AI 按需调用的混合模式。核心功能（5 步向导 + 固定提示引导 + 返回上一步）已经可用。

**建议**：P4-3 不应从零重新设计，而应在当前 GuidePanel 基础上增强：
1. 保留固定提示作为主线引导
2. AI 只在用户主动触发时介入（如"AI 分析数据"、"AI 推荐处理方式"）
3. 每个步骤增加一个"🤖 AI 建议"按钮，点击后调 AI，结果作为建议展示（不自动执行）

---

## 五、审查结论

| 维度 | 评估 |
|------|------|
| 方案方向 | ✅ 合理，问题分析准确，阶段划分清晰 |
| 问题时效性 | ⚠️ 3 项 P0/P1 已修复但报告未更新，需刷新 |
| 优先级排序 | ✅ 修复测试 → 清理代码 → 功能扩展，顺序正确 |
| 新增发现 | N-1/N-2/N-3 需加入待修清单 |
| AI 增强建议 | P4-3 应在当前 GuidePanel 基础上迭代，不重做 |

**综合评定**：方案可用，建议按本报告的调整后优先级执行。
