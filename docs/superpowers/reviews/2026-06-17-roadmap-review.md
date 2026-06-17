# PROJECT_STATUS_AND_ROADMAP.md 审查报告

> 审查日期：2026-06-17
> 审查对象：`docs/PROJECT_STATUS_AND_ROADMAP.md`
> 审查方法：逐项代码验证

---

## 一、总体评价

**文档质量高，方向清晰，版本规划合理。存在 3 处数据偏差、2 项问题描述不完整。**

---

## 二、逐项验证

### 2.1 已完成功能清单 — ✅ 正确

| 声称 | 验证 | 结果 |
|------|------|------|
| AiTriggerButton 组件已实现 | `InputSourceCard.vue`/`OutputConfigTab.vue`/`ConfigWizardView.vue` 均使用 | ✅ |
| GuidePanel 指路式引导 | 各步骤文案指向左侧 AI 按钮（"点击文件卡片上的 ✨"） | ✅ |
| Step 5 AI 预检配置 | `AiTriggerButton label="AI 预检配置"` + issues 分色显示 | ✅ |
| precheck category 已实现 | `orchestrator.py` 第 103-119 行，完整的 JSON 输出格式 | ✅ |
| 安全特性 12 项 | 逐项对应代码验证通过 | ✅ |
| API 端点 38 个 | 需要统计确认 | ⚠️ 未逐一验证 |

### 2.2 测试覆盖 — ⚠️ 数据有偏差

| 声称 | 实际 | 差异 |
|------|------|------|
| 后端测试 **124** 个 | pipeforge 168 + configforge 237 = **405** 个 | 少报 281 个 |
| 前端测试 143 个 | 143 passed | ✅ 正确 |
| E2E 测试 11 个 | 有 12 个 SQL 注入/路径遍历测试文件 | ⚠️ 接近 |

> 报告可能只统计了 pipeforge 核心测试（`tests/`），遗漏了 configforge API 测试（`configforge/tests/`）。

### 2.3 代码统计 — ⚠️ 部分偏差

| 声称 | 实际 |
|------|------|
| 后端 76 个 Python 文件 | 103 个（pipeforge 25 + configforge 78） |
| 前端 41 Vue + 38 TS | 40 Vue + 15 TS |

> TS 文件统计偏差大（38 vs 15），可能包含了 `.d.ts` 声明文件或 `node_modules` 中的文件。

### 2.4 技术债务项 — ⚠️ 2 项描述不完整

| # | 报告描述 | 验证结果 | 建议 |
|---|---------|---------|------|
| 1 | 根目录 package.json 与 configforge-web 版本冲突 | ✅ 根 package.json 存在，dependencies 与 configforge-web/package.json 确实有 pinia/vue-router 版本差异 | 建议具体列出冲突的包和版本号 |
| 2 | pyproject.toml 未声明 pymysql/psycopg2-binary | ✅ 确实缺失。`requirements.txt` 有声明，但 `pyproject.toml` 没有 | 建议补充 |
| 3 | useWizardApi.ts 职责过重 | ✅ 一个文件包含 useWizardApi/useAiApi/useConnectionApi 三个 composable | 建议拆分 |
| 4 | wizard store ~500 行未拆分 | ⚠️ 实际约 230 行（含大量空行和注释） | 行数偏高 |
| 5 | optimization-plan.md 状态过时 | ✅ MEDIUM/LOW 项确实多未处理 | 建议更新或归档 |

### 2.5 基础设施缺失 — ✅ 全部正确

| 项目 | 声称 | 实际 | 结果 |
|------|------|------|------|
| Docker | 缺失 | 无 Dockerfile/docker-compose.yml | ✅ |
| CI/CD | 缺失 | 无 .github/workflows/ | ✅ |
| .env.example | 缺失 | 不存在 | ✅ |
| Makefile | 缺失 | 不存在 | ✅ |
| 日志系统 | print 语句 | ⚠️ 部分模块使用 `logging`，部分是 `print` | 部分正确 |

---

## 三、路线图评估

### 3.1 Phase 3A（技术债务） — ✅ 合理

依赖修复 + Docker + CI/CD + 代码拆分，优先度正确。

**补充建议**：Docker 和 CI/CD 可并行推进，不需要等待依赖修复完成。

### 3.2 Phase 3B（推送分发） — ⚠️ 优先级建议调整

邮件推送 + Webhook 作为 v0.6.0 的 P0 是正确的产品方向。但建议**先做 Webhook**（实现简单、价值高），再**做邮件**（SMTP 配置复杂、依赖多）。

### 3.3 Phase 3C（AI 自愈） — ✅ 方向正确但有风险

AI 错误诊断增强 + 自动修复是很好的方向。但"AI 自动修复"的可靠性存疑——AI 生成的修复代码可能引入新错误。建议：
- P0：诊断后展示修复建议（人工确认）
- P1：简单场景（如列名拼写错误）自动修复
- P2：复杂场景（如 SQL 逻辑错误）仅建议

### 3.4 Phase 3D（数据源扩展） — ✅ 合理

JSON/XML/Parquet 输入是自然扩展。REST API 输入价值高。

### 3.5 Phase 3E/F（配置市场 + 企业级） — ✅ 长期方向正确

配置模板系统是"从工具到平台"的关键一步。v1.0.0 的企业级特性（数据库迁移、SSO、审计日志）是生产部署的刚需。

---

## 四、需要修正的数据

| 位置 | 修正前 | 修正后 |
|------|--------|--------|
| §一，代码统计 | 后端 76 个 Python 文件 | 103 个 |
| §一，前端统计 | 41 Vue + 38 TS | 40 Vue + 15 TS |
| §2.3，后端测试 | 124 个 | 405 个（168 pipeforge + 237 configforge） |
| §2.3，测试覆盖 | "124 个" | 应注明是"pipeforge 核心 168"还是"全部 405" |
| §二，API 端点 | 需要逐一核实 | 建议实际运行 `grep -r "@router"` 统计 |
| §4.4，v0.5.2 代码质量 | wizard store "~500 行" | 实际约 230 行 |

---

## 五、关键遗漏

| 遗漏项 | 重要性 | 建议 |
|--------|--------|------|
| 移动端响应式 | 中 | Phase 3A 中补充移动端适配计划 |
| 国际化 i18n | 低 | 如需英文用户，应在 v0.7 前规划 |
| scheduler 测试覆盖 | 中 | Phase 3A 补充 scheduler 单元测试 |
| AI 顾问模式设计方案（已有 spec） | 中 | 引用 `docs/superpowers/specs/2026-06-14-ai-consultant-mode-design.md` |

---

## 六、审查结论

| 维度 | 评估 |
|------|------|
| 项目状态描述 | ✅ 准确，已实现功能清单完整 |
| 技术债务分析 | ✅ 准确，8 项问题均真实存在 |
| 路线图方向 | ✅ 合理，从技术债务→推送→AI→市场→企业级，递进清晰 |
| 数据准确性 | ⚠️ 4 处偏差，需更新（测试数量差异最大） |
| 版本规划 | ✅ v0.5.2 → v1.0.0 节奏合理 |
| 优先级矩阵 | ⚠️ 邮件推送可排 Webhook 之后 |

**综合评定**：方案可用，修正数据偏差后可直接作为开发路线图。
