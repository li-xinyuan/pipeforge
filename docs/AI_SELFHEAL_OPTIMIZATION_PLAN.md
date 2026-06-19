# ConfigForge AI 自愈优化计划

> 编制日期：2026-06-19
> 基于：Phase 3C E2E 测试结果 + 代码审计发现
> 版本范围：v0.6.1 → v0.6.3
> 目标：让不熟悉 IT 技术的用户也能通过系统固有功能和 AI 协助完成复杂场景定义

---

## 一、现状评估

### 1.1 已完成功能（Phase 3C v0.6.1）

| 功能 | 状态 | 说明 |
|------|------|------|
| auto_diagnose 自动诊断 | ✅ 已完成 | 执行失败时自动调用 AI diagnose category |
| DiagnosisPanel 诊断面板 | ✅ 已完成 | severity 分色、根因展示、修复建议、前往修复按钮 |
| autofix 自动修复 | ✅ 已完成 | 简单场景 fixable=true + diff，复杂场景 fixable=false + 建议 |
| anomaly 异常检测 | ✅ 已完成 | 空值率/数值范围/数据量/重复率/格式/类型 6 维度 |
| 执行历史诊断展示 | ✅ 已完成 | ExecutionHistoryView 集成 DiagnosisPanel |
| 推送通知扩展 | ✅ 已完成 | trigger_on_anomaly + dispatcher 支持 anomaly 状态 |
| E2E 测试 | ✅ 已完成 | 8 项 E2E 测试全部通过 |

### 1.2 E2E 测试结果

| 测试项 | 结果 | AI 响应质量 |
|--------|------|-------------|
| SQL 语法错误诊断 | ✅ | 精确识别 FORM→FROM |
| 表名不存在诊断 | ✅ | 识别问题 + 3 种修复方向 |
| 文件路径不存在诊断 | ✅ | 覆盖常见原因 |
| 简单自动修复 | ✅ | fixable: true，old→new diff 精确 |
| 复杂场景自动修复 | ✅ | fixable: false，建议具体 |
| 数据异常检测 | ✅ | 检测到 null_rate_spike |
| 执行自动诊断 | ✅ | diagnosis 字段完整（cause/suggestions/severity/step） |
| AI 预检查 | ✅ | 4 个问题，按严重级别分类 |

### 1.3 核心问题：非技术用户体验

**目标用户画像**：不熟悉 IT 技术的运营/业务人员，可能不懂 SQL，但需要创建数据处理流程。

**当前能力边界**：

| 能力维度 | 评分 | 说明 |
|----------|------|------|
| 理解错误原因 | ⭐⭐⭐⭐⭐ | AI 将技术错误翻译为中文，非技术用户能理解 |
| 获得修复方向 | ⭐⭐⭐⭐⭐ | 每次诊断给出 2-3 条具体建议 |
| 简单错误自动修复 | ⭐⭐⭐⭐ | 拼写错误等一键修复，但修复内容不会自动填入表单 |
| 复杂错误修复 | ⭐⭐ | fixable: false 时建议仍含 SQL 术语，用户可能无法操作 |
| 从零创建配置 | ⭐⭐ | 需要用户写出基本正确的 SQL，完全不懂 SQL 则无法开始 |
| 数据质量感知 | ⭐⭐⭐⭐ | 异常检测能发现问题，但缺乏可视化 |

---

## 二、优化任务清单

### 优先级说明
- 🔴 P0：直接影响非技术用户能否使用，必须完成
- 🟡 P1：显著提升用户体验，应该完成
- 🟢 P2：锦上添花，可延后

---

### O-01 执行失败弹窗优先显示 AI 诊断，折叠原始错误

**优先级**：🔴 P0
**预估工作量**：小

**问题**：当前执行失败弹窗同时显示原始错误（如 `sqlite3.OperationalError: near "FORM": syntax error`）和 AI 诊断。原始错误中的技术术语会吓到非技术用户，且信息重复。

**方案**：
1. 执行失败时，**默认只显示 AI 诊断面板**（DiagnosisPanel），不显示原始错误
2. 在诊断面板底部添加"查看技术详情"折叠区域，点击展开显示原始错误
3. 如果 AI 诊断未返回（AI 未配置或超时），则回退显示原始错误

**涉及文件**：
- 修改：`configforge-web/src/components/ExecuteConfigModal.vue`
- 修改：`configforge-web/src/components/common/DiagnosisPanel.vue`（添加技术详情折叠区）

**验证标准**：
- [ ] 执行失败时默认只显示 AI 诊断
- [ ] "查看技术详情"可展开/折叠
- [ ] AI 未配置时回退显示原始错误
- [ ] 前端测试通过

---

### O-02 autofix 修复内容自动填入表单

**优先级**：🔴 P0
**预估工作量**：大

**问题**：当前点击"应用修复"后仅导航到对应步骤，修复内容不会自动填入表单。用户需要手动复制 old→new diff 中的内容到输入框，非技术用户可能不知道如何操作。

**方案**：
1. autofix 返回的 fixes 数组包含 `step`/`field`/`old`/`new` 信息
2. 点击"应用修复"时，将 fixes 数据传递给 wizard store
3. wizard store 新增 `applyAutofixes(fixes)` 方法，根据 step+field 定位到对应的表单字段并自动填入新值
4. 填入后高亮变更的字段（绿色边框闪烁 2 秒），让用户感知修改
5. 如果 field 是 `sql`，定位到 SQL 编辑器并替换内容
6. 如果 field 是 `path` 或其他配置字段，定位到对应输入框

**涉及文件**：
- 修改：`configforge-web/src/stores/wizard.ts`（新增 `applyAutofixes` 方法）
- 修改：`configforge-web/src/components/ExecuteConfigModal.vue`（传递 fixes 到 store）
- 修改：`configforge-web/src/views/HomeView.vue`（onGotoStep 传递 fixes）
- 修改：`configforge-web/src/views/ConfigWizardView.vue`（接收 fixes 并调用 store）
- 可能修改：`configforge-web/src/components/step3/SqlProcessorContent.vue`（高亮变更）

**验证标准**：
- [ ] 点击"应用修复"后，SQL 编辑器自动更新为修复后的内容
- [ ] 变更字段有视觉高亮反馈
- [ ] 非技术用户无需手动复制粘贴即可完成修复
- [ ] 前端测试通过

---

### O-03 复杂场景修复建议去技术化

**优先级**：🔴 P0
**预估工作量**：中

**问题**：autofix 返回 `fixable: false` 时，建议仍包含 SQL 术语（如"添加 JOIN ON 条件"），非技术用户可能无法理解。

**方案**：
1. 优化 autofix prompt，增加"面向非技术用户"的指令，要求 AI 用业务语言描述建议
2. 在 prompt 中添加示例：
   - 技术描述 → 业务描述 的映射示例
   - "添加 JOIN ON 条件" → "需要告诉系统用户表和订单表怎么关联"
   - "修改 WHERE 子句" → "需要调整筛选条件"
3. DiagnosisPanel 中对建议文字做后处理：如果建议以 SQL 关键字开头，添加简短的业务解释前缀

**涉及文件**：
- 修改：`configforge/services/ai/orchestrator.py`（优化 autofix prompt）
- 修改：`configforge-web/src/components/common/DiagnosisPanel.vue`（建议文字后处理）

**验证标准**：
- [ ] autofix fixable: false 时建议不含纯 SQL 术语
- [ ] 建议用业务语言描述，非技术用户能理解
- [ ] 后端测试通过

---

### O-04 执行失败时提供"让 AI 帮你重写"入口

**优先级**：🔴 P0
**预估工作量**：中

**问题**：完全不懂 SQL 的用户即使看到诊断建议，也无法自行修改。需要一个"让 AI 帮你重写"的入口，将当前配置和错误信息发给 AI 编排模式，自动生成正确的配置。

**方案**：
1. 在 DiagnosisPanel 中新增"让 AI 帮我重写"按钮（与"AI 自动修复"并列）
2. 点击后调用 orchestrate category，传入当前配置 + 错误信息 + 自然语言描述
3. AI 返回完整的 OrchestrationResult，包含修正后的配置步骤
4. 用户确认后，自动更新 wizard store 中的配置

**涉及文件**：
- 修改：`configforge-web/src/components/common/DiagnosisPanel.vue`（新增按钮）
- 修改：`configforge-web/src/components/ExecuteConfigModal.vue`（处理 AI 重写逻辑）
- 修改：`configforge/services/ai/orchestrator.py`（优化 orchestrate prompt 支持错误修复场景）

**验证标准**：
- [ ] 执行失败弹窗有"让 AI 帮我重写"按钮
- [ ] 点击后 AI 生成修正后的配置
- [ ] 用户确认后配置自动更新
- [ ] E2E 测试：不懂 SQL 的用户通过此功能完成配置修复

---

### O-05 诊断结果增加"影响说明"

**优先级**：🟡 P1
**预估工作量**：小

**问题**：当前诊断只说明"错误是什么"和"怎么修"，但不说明"不修会怎样"。非技术用户可能不理解修复的紧迫性。

**方案**：
1. 优化 diagnose prompt，要求 AI 返回 `impact` 字段，描述不修复的后果
2. DiagnosisPanel 在 severity 标签旁显示影响说明
3. 示例：`impact: "不修复则无法导出任何数据，流程完全中断"` / `impact: "数据可能不完整，部分记录会丢失"`

**涉及文件**：
- 修改：`configforge/services/ai/orchestrator.py`（diagnose prompt 增加 impact 字段）
- 修改：`configforge/services/ai/auto_diagnose.py`（处理 impact 字段）
- 修改：`configforge-web/src/components/common/DiagnosisPanel.vue`（显示影响说明）
- 修改：`configforge-web/src/composables/useConfigApi.ts`（ExecuteError 类型增加 impact）

**验证标准**：
- [ ] 诊断结果包含 impact 字段
- [ ] DiagnosisPanel 显示影响说明
- [ ] 非技术用户能理解修复的紧迫性

---

### O-06 异常检测结果可视化

**优先级**：🟡 P1
**预估工作量**：大

**问题**：当前异常检测结果只有文字描述（如"年龄列空值率达到67%"），缺乏直观性。非技术用户对数字不敏感。

**方案**：
1. 新增 AnomalyChart 组件，用简单柱状图展示各列的空值率
2. 异常列用红色标注，正常列用绿色
3. 在 DiagnosisPanel 的 anomaly 模式下显示图表
4. 使用纯 CSS 实现简单柱状图（避免引入图表库增加包体积）

**涉及文件**：
- 新建：`configforge-web/src/components/common/AnomalyChart.vue`
- 修改：`configforge-web/src/components/common/DiagnosisPanel.vue`（集成 AnomalyChart）

**验证标准**：
- [ ] 异常检测结果有可视化图表
- [ ] 异常列红色标注，正常列绿色
- [ ] 纯 CSS 实现，无额外依赖

---

### O-07 定时任务执行失败自动诊断

**优先级**：🟡 P1
**预估工作量**：中

**问题**：手动执行失败时会调用 `auto_diagnose`，但定时任务（scheduler）执行失败时不调用，行为不一致。定时任务的用户无法看到 AI 诊断。

**方案**：
1. 在 `scheduler.py` 的 `_run_scheduled_pipeline` 失败路径中调用 `auto_diagnose`
2. 由于 `auto_diagnose` 是 async 函数，而 `_run_scheduled_pipeline` 是同步函数，需要使用 `asyncio.run()` 或 `loop.run_until_complete()` 调用
3. 同时在定时任务成功/失败路径中调用 `dispatch_notifications_async` 发送通知

**涉及文件**：
- 修改：`configforge/scheduler.py`（失败路径调用 auto_diagnose，成功/失败路径调用 dispatch_notifications_async）

**验证标准**：
- [ ] 定时任务失败时执行记录包含 diagnosis 字段
- [ ] 定时任务成功/失败时发送推送通知
- [ ] 后端测试通过

---

### O-08 诊断结果缓存与去重

**优先级**：🟢 P2
**预估工作量**：中

**问题**：同一配置重复执行失败时，每次都调用 AI 诊断，浪费 API 调用和响应时间。相同错误的诊断结果应该缓存。

**方案**：
1. 以 `config_id + error_message_hash` 为 key 缓存诊断结果
2. 缓存有效期 1 小时（配置可能已修改）
3. 缓存存储在内存中（LRU，最多 100 条）
4. 命中缓存时直接返回，跳过 AI 调用

**涉及文件**：
- 修改：`configforge/services/ai/auto_diagnose.py`（添加缓存逻辑）

**验证标准**：
- [ ] 相同错误 1 小时内不重复调用 AI
- [ ] 缓存命中率可观测（日志）
- [ ] 后端测试通过

---

### O-09 AI 诊断多轮对话支持

**优先级**：🟢 P2
**预估工作量**：大

**问题**：当前诊断是单轮的——AI 给出建议后，用户如果看不懂建议，无法追问。非技术用户可能需要多轮交互才能理解问题。

**方案**：
1. 在 DiagnosisPanel 中新增"继续对话"按钮
2. 点击后打开 AiChatPanel，自动注入诊断上下文（cause/suggestions/error）
3. 用户可以用自然语言追问，如"什么是 JOIN？"、"怎么添加关联条件？"
4. AI 在诊断上下文中回答，更精准

**涉及文件**：
- 修改：`configforge-web/src/components/common/DiagnosisPanel.vue`（新增"继续对话"按钮）
- 修改：`configforge-web/src/components/ExecuteConfigModal.vue`（集成 AiChatPanel）

**验证标准**：
- [ ] 诊断面板有"继续对话"入口
- [ ] 对话自动携带诊断上下文
- [ ] 非技术用户能通过追问理解问题

---

### O-10 诊断历史趋势分析

**优先级**：🟢 P2
**预估工作量**：大

**问题**：当前只看单次执行的诊断结果，无法发现"这个配置经常在第3步失败"等趋势。非技术用户可能反复犯相同错误。

**方案**：
1. 在执行历史页面新增"诊断趋势"标签页
2. 统计同一配置的失败原因分布（饼图）
3. 标注高频错误模式（如"SQL 语法错误占 60%"）
4. 给出"建议学习"提示（如"建议学习 SQL 基础语法"）

**涉及文件**：
- 修改：`configforge-web/src/views/ExecutionHistoryView.vue`（新增趋势标签页）
- 新建：`configforge-web/src/components/common/DiagnosisTrend.vue`（趋势图表）
- 新增后端 API：`GET /api/executions/diagnosis-trend?config_id=xxx`

**验证标准**：
- [ ] 执行历史页面有诊断趋势标签
- [ ] 显示失败原因分布
- [ ] 标注高频错误模式

---

## 三、实施路线

### Phase 3C-1：核心体验优化（v0.6.2）

**目标**：让非技术用户能独立完成从错误到修复的完整闭环

| 任务 | 优先级 | 依赖 | 涉及文件数 |
|------|--------|------|-----------|
| O-01 弹窗优先显示 AI 诊断 | 🔴 P0 | 无 | 2 |
| O-02 autofix 自动填入表单 | 🔴 P0 | O-01 | 5 |
| O-03 修复建议去技术化 | 🔴 P0 | 无 | 2 |
| O-04 "让 AI 帮你重写"入口 | 🔴 P0 | O-01 | 3 |
| O-07 定时任务自动诊断 | 🟡 P1 | 无 | 1 |

### Phase 3C-2：体验增强（v0.6.3）

**目标**：提升诊断的直观性和交互深度

| 任务 | 优先级 | 依赖 | 涉及文件数 |
|------|--------|------|-----------|
| O-05 诊断增加影响说明 | 🟡 P1 | 无 | 4 |
| O-06 异常结果可视化 | 🟡 P1 | 无 | 2 |
| O-08 诊断缓存去重 | 🟢 P2 | 无 | 1 |

### Phase 3C-3：高级功能（v0.7.0 配合配置市场）

| 任务 | 优先级 | 依赖 | 涉及文件数 |
|------|--------|------|-----------|
| O-09 多轮对话支持 | 🟢 P2 | O-01 | 2 |
| O-10 诊断趋势分析 | 🟢 P2 | O-05 | 3 |

---

## 四、验收标准

### 4.1 非技术用户可用性验收

以下场景应由"不懂 SQL 的运营人员"独立完成，无需技术支持：

| # | 场景 | 预期行为 |
|---|------|----------|
| 1 | 创建配置时 SQL 拼写错误 | AI 诊断翻译为中文，一键修复，自动填入正确 SQL |
| 2 | 创建配置时表名错误 | AI 诊断说明"表名不存在"，建议正确的表名 |
| 3 | 创建配置时文件路径错误 | AI 诊断说明"文件不存在"，建议检查路径 |
| 4 | JOIN 逻辑错误（复杂场景） | AI 返回 fixable: false，用业务语言建议，提供"让 AI 帮我重写"入口 |
| 5 | 数据空值率异常 | AI 检测并告警，推送通知，可视化展示 |
| 6 | 完全不懂 SQL | 通过"让 AI 帮我重写"入口，用自然语言描述需求，AI 生成正确配置 |

### 4.2 技术验收

- [ ] 后端测试全部通过（当前 322 个 + 新增测试）
- [ ] 前端测试全部通过（当前 201 个 + 新增测试）
- [ ] vue-tsc 0 errors
- [ ] vite build 成功
- [ ] E2E 测试：6 个用户场景全部通过

---

## 五、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| AI 响应不稳定（不同调用返回不同格式） | 中 | 高 | autofix 结果增加 schema 校验，不符合格式时降级为 fixable: false |
| AI 响应延迟（>5 秒） | 低 | 中 | 诊断异步加载，不阻塞 UI；增加加载动画 |
| "让 AI 帮我重写"生成错误配置 | 中 | 高 | 生成后先预览，用户确认后才应用；保留回退能力 |
| autofix 自动填入表单定位不准 | 中 | 中 | 限定支持的字段类型（sql/path/columns），不支持的提示手动修改 |
| AI 重写引入新错误 | 中 | 高 | 重写后自动 precheck，error 级别问题提示用户手动修复（审查建议 #3） |
| scheduler event loop 冲突 | 低 | 高 | 使用 `asyncio.new_event_loop()` 替代 `asyncio.run()`（审查建议 #4） |
