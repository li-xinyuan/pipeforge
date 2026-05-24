# AI SQL 生成落地 实施计划 v2 — 审核报告

**审核日期**: 2026-05-08
**审核文件**: `docs/superpowers/plans/2026-05-09-ai-sql-generation-v2.md`
**对照审核**: `docs/superpowers/reviews/2026-05-08-ai-sql-generation-plan-review.md`

---

## 总体评价

**v2 计划质量优秀，v1 审核中全部 14 个问题（3 P0 + 6 P1 + 5 P2）均已修复。** 计划末尾的"审核修订清单"逐条对应了每个问题的修复方案，修复方式合理。同时 v2 未引入新的 P0/P1 级问题，仅发现 3 个 P2 级小改进点。

**结论：可以开始实施。**

---

## 一、v1 审核问题修复验证

### 🔴 P0 问题修复验证

| # | 问题 | 修复方式 | 验证结果 |
|---|------|---------|---------|
| P0-1 | 缺少 LlmBackend 基类 | Task 2 Step 1 新增 `base.py`，文件清单已补充 | ✅ 已修复 |
| P0-2 | settings 路径不安全 | 改用 `CONFIGFORGE_DATA_DIR` 环境变量 + `data/` 默认目录 + `.gitignore` | ✅ 已修复 |
| P0-3 | Key 清空逻辑漏洞 | 新增 `AiSettingsUpdate` 模型，`api_key: str\|None`，`None`=保留，`""`=清空 | ✅ 已修复 |

**P0-3 补充验证**：`update_settings` 端点逻辑正确（第 449-456 行），`test_ai_settings_clear_key` 测试覆盖了 `null` 保留和 `""` 清空两种场景（第 702-723 行），前端 `saveSettings` 中 `if (!body.api_key) body.api_key = null` 正确映射了"空输入→保留旧值"的语义（第 974 行）。

### 🟡 P1 问题修复验证

| # | 问题 | 修复方式 | 验证结果 |
|---|------|---------|---------|
| P1-1 | AiSuggestion 缺 diagnose | Task 6 Step 2 更新 `types/wizard.ts` | ✅ 已修复 |
| P1-2 | App.vue 无导航栏 | 改为浮动齿轮按钮 (Task 6 Step 5) | ✅ 已修复 |
| P1-3 | onAiMapping sourceCols 为空 | 从 `store.uploadedFiles[fileId].columns` 提取 (Task 7 Step 2) | ✅ 已修复 |
| P1-4 | useAiSuggest 与 useWizardApi 重叠 | 在 `useWizardApi.ts` 中新增 `useAiApi()` composable (Task 6 Step 1) | ✅ 已修复 |
| P1-5 | 缺少 Mock SDK 测试 | Task 5 Step 2 新增 `test_openai_generate_mock` / `test_anthropic_generate_mock` | ✅ 已修复 |
| P1-6 | mask_key 格式不一致 | 统一为 `sk-***456` 格式，测试断言同步更新 | ✅ 已修复 |

### 🟢 P2 问题修复验证

| # | 问题 | 修复方式 | 验证结果 |
|---|------|---------|---------|
| P2-1 | SDK 应放 optional-dependencies | Task 2 Step 0 添加 `[project.optional-dependencies]` | ✅ 已修复 |
| P2-2 | autoSuggestScene fileColumns 为空 | Task 7 Step 3 从 `store.uploadedFiles` 提取 `columnsByFile` | ✅ 已修复 |
| P2-3 | build_prompt 命名冲突 | scene 使用 `columnsByFile`，columns 使用 `fileColumns` | ✅ 已修复 |
| P2-4 | 非 JSON 响应前端解析失败 | `parse_response` 返回 `{"raw": text, "is_json": false}` | ✅ 已修复 |
| P2-5 | 测试数量预估不精确 | ~160 → ~155 | ✅ 已修复 |

---

## 二、v2 新发现的问题

### 🟢 P2 — 小改进建议

**P2-A：`AiSettingsUpdate` 的 `model_dump()` 可能传入 `api_key=None` 导致 `AiSettings` 校验失败**

Task 4 Step 1 第 454 行：

```python
full_settings = AiSettings(**body.model_dump())
```

当 `body.api_key is None` 时，`body.model_dump()` 会产出 `{"api_key": None, ...}`，而 `AiSettings.api_key` 类型是 `str`，Pydantic 会将 `None` 转为字符串 `"None"` 而非保留旧值。

**修复方案**：在构造 `AiSettings` 前先处理 `api_key`：

```python
@router.put("/settings")
async def update_settings(body: AiSettingsUpdate):
    existing = load_settings()
    api_key = existing.api_key if body.api_key is None else body.api_key
    dump = body.model_dump(exclude={"api_key"})
    full_settings = AiSettings(api_key=api_key, **dump)
    save_settings(full_settings)
    return {"ok": True}
```

---

**P2-B：`test_ai_settings_clear_key` 测试依赖执行顺序**

Task 5 Step 4 中 `test_ai_settings_clear_key` 先 PUT 一个 Key，再 PUT `api_key: null`，再 GET 验证。但 `test_ai_settings_mask` 也做了类似操作。如果测试并行执行或顺序变化，可能互相干扰。

**建议**：每个测试在开始时重置 settings 到已知状态，或使用独立的临时文件（类似 `test_ai_settings.py` 中 `mod.SETTINGS_FILE` 的 monkey-patch 方式）。

---

**P2-C：`useAiApi` 中 `askSuggestion` 的错误信息提取逻辑与 `useWizardApi.post` 不一致**

`useWizardApi.post` 从 `data.error` 提取错误，而 `useAiApi.askSuggestion` 从 `data.detail || data.error` 提取。FastAPI 的 HTTPException 默认返回 `{"detail": "..."}` 格式，所以 `data.detail` 是正确的。但建议统一风格，或让 `useAiApi` 也使用 `useWizardApi.post` 的封装来保持一致。

---

## 三、审核清单

| # | 级别 | 问题 | 状态 |
|---|------|------|------|
| v1-P0-1 | 🔴→✅ | 缺少 LlmBackend 基类 | 已修复 |
| v1-P0-2 | 🔴→✅ | settings 路径不安全 | 已修复 |
| v1-P0-3 | 🔴→✅ | Key 清空逻辑漏洞 | 已修复 |
| v1-P1-1 | 🟡→✅ | AiSuggestion 缺 diagnose | 已修复 |
| v1-P1-2 | 🟡→✅ | App.vue 无导航栏 | 已修复 |
| v1-P1-3 | 🟡→✅ | onAiMapping sourceCols 为空 | 已修复 |
| v1-P1-4 | 🟡→✅ | useAiSuggest 与 useWizardApi 重叠 | 已修复 |
| v1-P1-5 | 🟡→✅ | 缺少 Mock SDK 测试 | 已修复 |
| v1-P1-6 | 🟡→✅ | mask_key 格式不一致 | 已修复 |
| v1-P2-1 | 🟢→✅ | SDK 应放 optional-dependencies | 已修复 |
| v1-P2-2 | 🟢→✅ | autoSuggestScene fileColumns 为空 | 已修复 |
| v1-P2-3 | 🟢→✅ | build_prompt 命名冲突 | 已修复 |
| v1-P2-4 | 🟢→✅ | 非 JSON 响应前端解析失败 | 已修复 |
| v1-P2-5 | 🟢→✅ | 测试数量预估不精确 | 已修复 |
| v2-P2-A | 🟢 | AiSettingsUpdate.model_dump() 可能传入 None | 💡 建议 |
| v2-P2-B | 🟢 | test_ai_settings_clear_key 依赖执行顺序 | 💡 建议 |
| v2-P2-C | 🟢 | useAiApi 错误提取与 useWizardApi 不一致 | 💡 建议 |

---

## 四、结论

v2 计划已完整修复 v1 审核的全部问题，可以开始实施。3 个新发现的 P2 级问题为非阻塞性改进建议，可在实施过程中酌情处理。其中 **P2-A（`model_dump()` 传入 None）** 建议优先处理，否则 PUT /settings 端点在 `api_key=null` 时会行为异常。
