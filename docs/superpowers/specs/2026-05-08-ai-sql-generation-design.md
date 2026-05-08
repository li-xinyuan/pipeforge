# AI SQL 生成落地 设计文档

> **Goal:** ConfigForge 接入真实 LLM 后端（多提供商），用户在向导中通过自然语言生成 SQL、列映射、场景名，AI 辅助配置全流程。

**Architecture:** 后端 `LlmBackend` 抽象 + OpenAI/Anthropic 实现 + 服务端 JSON 配置持久化。前端 `useAiSuggest` composable 调用 `/api/ai/suggest`，`AiSuggestPanel` 展示结果（采纳/拒绝/重新生成）。扩展 `category` 至 `scene | sql | mapping | columns | diagnose`。

**Tech Stack:** FastAPI + `openai` SDK + `anthropic` SDK + Vue 3 + Pinia

**关键约束：**
- API Key 仅存储于服务端，前端只返回脱敏版本
- AI 功能默认关闭（`enabled: false`），需用户主动开启
- 已有 Excel/CSV 路径不受影响
- 现有 130 个测试必须继续通过

---

## AI 覆盖场景

| Category | Wizard Step | 触发方式 | 输入 | 输出 |
|----------|------------|---------|------|------|
| `scene` | Step 1 | 上传文件后自动调 | fileCount, fileNames, fileColumns | name, description |
| `columns` | Step 2 | 上传文件后自动调 | fileColumns, sampleRows | 列类型推荐、关联键检测 |
| `sql` | Step 3 | 点 "AI 生成 SQL" 按钮 | inputs(表结构) + naturalLanguage(用户自然语言) | sql, outputTables, explanation |
| `mapping` | Step 4 | 点 "AI 自动映射" 按钮 | sourceColumns, targetColumns | mappings[{source, target}] |
| `diagnose` | 全局 | 管道失败后自动调 | yaml, errorLog | cause, suggestions[], severity |

---

## 架构

```
┌──────────────────────────────────────────────────┐
│  ConfigForge Web (Vue 3)                          │
│                                                    │
│  SettingsPage.vue     AiSuggestPanel.vue           │
│  (配置提供商/Key/URL  (已存在 - 无需改动)           │
│   测试连接/保存)                                    │
│         │                     ▲                    │
│         ▼                     │                    │
│  useAiSuggest.ts              │                    │
│  (新增 - 调用 /api/ai/suggest)┘                    │
└───────────────┬───────────────────────────────────┘
                │ POST /api/ai/suggest | /settings | /test
                │ { category, context }
┌───────────────▼───────────────────────────────────┐
│  ConfigForge Backend (FastAPI)                     │
│                                                    │
│  api/ai.py              services/ai/               │
│  /suggest ──────────► orchestrator.py              │
│  /settings (GET/PUT)    (build_prompt + 调用后端)   │
│  /test                    │                        │
│                           │                        │
│                    LlmBackend.generate(prompt)      │
│                           │                        │
│               ┌───────────┼───────────┐            │
│               ▼           ▼           ▼            │
│         openai.py   anthropic.py  custom.py        │
│                                                    │
│  configforge/ai_settings.json (API Key 存储于此)     │
└────────────────────────────────────────────────────┘
```

---

## 受影响文件

```
后端:
  Modify: configforge/models/ai.py           # 加 AiProvider enum, AiSettings 模型，扩展 category
  Modify: configforge/api/ai.py              # /suggest 改为真实调用，加 /settings, /test
  Modify: configforge/server.py              # 无需改动（路由已注册）
  Create: configforge/services/ai/openai_backend.py
  Create: configforge/services/ai/anthropic_backend.py
  Create: configforge/services/ai/factory.py
  Create: configforge/services/ai/orchestrator.py   # build_prompt + parse_response
  Create: configforge/services/ai/settings.py       # load/save/mask ai_settings.json
  Modify: configforge/tests/test_api_ai.py          # 新增 settings、test 连接、suggest with mock

前端:
  Create: configforge-web/src/composables/useAiSuggest.ts
  Create: configforge-web/src/views/SettingsPage.vue
  Modify: configforge-web/src/components/step3/SqlEditorTab.vue     # 按钮接线
  Modify: configforge-web/src/components/step3/OutputConfigTab.vue  # 自动映射按钮接线
  Modify: configforge-web/src/views/Step1SceneView.vue              # 场景推断接线
  Modify: configforge-web/src/router/index.ts                       # 添加 /settings 路由
  Modify: configforge-web/src/App.vue                               # 导航加设置入口
  Modify: configforge-web/src/composables/useWizardApi.ts           # 可能需加 ai 方法
```

---

## 数据模型变更

### models/ai.py

```python
from enum import Enum
from pydantic import BaseModel
from typing import Literal, Optional

class AiProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"

class AiSettings(BaseModel):
    provider: AiProvider = AiProvider.OPENAI
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    enabled: bool = False

class AiSuggestionRequest(BaseModel):
    category: Literal["scene", "columns", "sql", "mapping", "diagnose"]
    context: dict

class AiSuggestionResponse(BaseModel):
    content: str
    category: str
```

### ai_settings.json 存储格式

```json
{
  "provider": "openai",
  "api_key": "sk-abc123...",
  "base_url": "",
  "model": "gpt-4o",
  "temperature": 0.7,
  "max_tokens": 4096,
  "enabled": true
}
```

---

## Prompt 设计

### scene — Step 1 场景推断

```
System: 你是一个数据流水线配置专家。根据用户上传的文件信息，生成简洁的中文场景名（5-15字）和一句话描述（20-50字）。返回 JSON: {"name": "...", "description": "..."}。不要输出其他内容。
User: 用户上传了 {fileCount} 个文件: {fileNames}。各文件列名: {fileColumns}。
```

### columns — Step 2 列分析

```
System: 你是一个数据分析专家。根据文件列名和样本数据，推荐列的类型、检测可能的关联键。返回 JSON: {"columnTypes": {"列名": "string|number|date|boolean"}, "joinKeys": [{"file1": "列名", "file2": "列名"}], "suggestedTableNames": ["..."], "suggestedParamKeys": ["..."]}。
User: 文件列名: {columns}。样本数据: {sampleRows}。
```

### sql — Step 3 SQL 生成

```
System: 你是一个 SQL 专家，针对 SQLite 数据库。根据表结构和用户的自然语言需求，生成 SQLite 兼容的 SQL。注意: 表名用双引号包裹，列名必须来自表结构不要编造，使用 SQLite 支持的函数（GROUP BY, COUNT, JOIN, CASE WHEN 等）。返回 JSON: {"sql": "...", "outputTables": ["..."], "explanation": "简短说明这条 SQL 做了什么"}。
User: 表结构: {tableSchemas}。需求: {naturalLanguage}。
```

### mapping — Step 4 列映射

```
System: 你是一个数据映射专家。根据源列名和目标列名列表，推断最佳映射关系。匹配规则: 语义相似（如同义词、中英文对应）、名称相似（编辑距离、包含关系）、位置顺序。返回 JSON: {"mappings": [{"source": "源列名", "target": "目标列名"}]}。源列没有对应目标列的不要强行映射。
User: 源列: {sourceColumns}。目标列: {targetColumns}。
```

### diagnose — 错误诊断

```
System: 你是一个数据管道调试专家。根据以下 YAML 配置和错误日志，分析失败原因并给出修复建议。返回 JSON: {"cause": "根因一句话", "suggestions": ["具体修复步骤"], "severity": "error|warning"}。
User: YAML: {yaml}。错误: {errorLog}。
```

---

## API 设计

### POST /api/ai/suggest — 已有，改为真实调用

```
Request:  { "category": "sql", "context": { "inputs": [...], "naturalLanguage": "..." } }
Response: { "content": "{\"sql\": \"...\", \"outputTables\": [...]}", "category": "sql" }
Errors:   503 — AI 响应超时 | 401 — API Key 无效 | 500 — LLM 返回无法解析
```

每次请求时从 `ai_settings.json` 加载配置，通过 `factory.create_backend(settings)` 获取对应后端，`orchestrator.build_prompt(category, context)` 拼 prompt，`backend.generate(prompt)` 调 LLM，`orchestrator.parse_response(text)` 从 LLM 回复中提取 JSON。

### GET /api/ai/settings — 获取配置（脱敏）

```
Response: { "provider": "openai", "api_key": "sk-...***xyz", "base_url": "", "model": "gpt-4o", "temperature": 0.7, "max_tokens": 4096, "enabled": true }
```

### PUT /api/ai/settings — 更新配置

```
Request:  { "provider": "openai", "api_key": "sk-full-key", ... }
Response: { "ok": true }
```

空 api_key 表示不更新。保存到 `configforge/ai_settings.json`。

### POST /api/ai/test — 测试连接

```
Response: { "ok": true, "provider": "openai", "model": "gpt-4o", "latency_ms": 850 }
Errors:   401 — 认证失败 | 503 — 连接超时
```

---

## 前端设计

### SettingsPage.vue（新增）

路由 `/settings`，包含表单：

- 启用开关 `[toggle]`
- 提供商选择 `[OpenAI | Anthropic | Custom(OpenAI-compatible)]`
- 模型输入（带常用模型建议下拉: gpt-4o, gpt-4-turbo, claude-opus-4-7 等）
- API Key 输入（type=password，从服务端加载时显示脱敏值）
- Base URL 输入（OpenAI 时选填，Anthropic/Custom 时必填）
- Temperature 滑块 (0-2, 步长 0.1)
- Max Tokens 数字输入
- "测试连接" 按钮 → POST /api/ai/test → 显示成功/失败 toast
- "保存" 按钮 → PUT /api/ai/settings

### useAiSuggest.ts（新增）

```typescript
function useAiSuggest() {
  const suggesting = ref(false)
  const error = ref<string | null>(null)

  async function askSuggestion(category: string, context: Record<string, any>): Promise<string | null> {
    suggesting.value = true
    error.value = null
    try {
      const resp = await fetch('/api/ai/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, context }),
      })
      const data = await resp.json()
      if (resp.ok) return data.content
      error.value = data.error || '未知错误'
    } catch (e) {
      error.value = '网络请求失败'
    } finally {
      suggesting.value = false
    }
    return null
  }

  return { suggesting, error, askSuggestion }
}
```

### 按钮接线

| 位置 | 操作 | 调用 | 结果处理 |
|------|------|------|---------|
| Step1SceneView | 文件上传后自动 | `askSuggestion('scene', {fileCount, fileNames, fileColumns})` | 解析 name/description → `store.scene` |
| Step2InputView | 文件上传后自动 | `askSuggestion('columns', {fileColumns, sampleRows})` | 写入 `store.aiSuggestions['columns']` |
| SqlEditorTab "AI 生成 SQL" | 点击 → 弹出自然语言输入框 → 确认 | `askSuggestion('sql', {inputs, naturalLanguage})` | 解析 sql/outputTables → `store.processor` |
| OutputConfigTab "AI 自动映射" | 点击 | `askSuggestion('mapping', {sourceColumns, targetColumns})` | 解析 mappings → `outputConfig.columns` |

---

## 错误处理

| 场景 | 后端行为 | 前端表现 |
|------|---------|---------|
| AI 未配置/未启用 | 返回 `content: "AI 未配置，请先在设置中启用"` | AiSuggestPanel 展示提示 |
| LLM 调用超时 (>30s) | `asyncio.wait_for` 捕获 `TimeoutError` → 503 | 显示 "AI 响应超时，请重试" |
| API Key 无效/403/401 | SDK 异常 → 401 + 错误详情 | 显示 "API Key 无效，请检查设置" |
| LLM 返回非 JSON | `parse_response` 尝试从 markdown ```json block 提取 | 失败则返回原文，前端展示 |
| 网络错误 | 标准 HTTP 异常 | "网络请求失败，请检查连接" |

---

## 测试计划

### test_ai_settings.py（新增）

- `test_load_defaults` — 配置文件不存在时返回默认值
- `test_save_and_load` — 保存后能正确读取
- `test_mask_key` — `sk-abc123def456` → `sk-...***f456`（保留前 3 后 3）
- `test_update_partial` — 空 api_key 不覆盖已有 key

### test_ai_backends.py（新增）

- `test_openai_backend_creates` — 工厂根据 settings 创建正确实例
- `test_anthropic_backend_creates`
- `test_custom_backend_uses_openai_class`
- Mock SDK `create` 调用，不消耗真实 token

### test_ai_orchestrator.py（新增）

- `test_build_prompt_sql` — prompt 包含表结构和用户需求
- `test_build_prompt_mapping` — prompt 包含源列/目标列
- `test_parse_json_from_markdown` — 提取 ```json ... ``` 块
- `test_parse_plain_json` — 直接 JSON 字符串
- `test_parse_invalid` — 无法解析时返回原文

### test_api_ai.py（扩展现有文件）

- `test_ai_suggest_returns_noop` — 已有，保留（disabled 时）
- `test_ai_settings_get` — GET /settings 返回脱敏配置
- `test_ai_settings_put` — PUT /settings 保存并返回 ok
- `test_ai_settings_mask` — PUT 后 GET 的 key 已脱敏
- `test_ai_test_connection` — POST /test 正常
- `test_ai_suggest_with_mock_backend` — enabled + mock backend → 返回 AI 内容
- `test_ai_suggest_disabled` — disabled → 返回 no-op
