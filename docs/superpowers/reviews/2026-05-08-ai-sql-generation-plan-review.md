# AI SQL 生成落地 实施计划 — 审核报告

**审核日期**: 2026-05-08
**审核文件**: `docs/superpowers/plans/2026-05-09-ai-sql-generation.md`
**对照设计**: `docs/superpowers/specs/2026-05-08-ai-sql-generation-design.md`

---

## 总体评价

计划质量高，任务拆分清晰（7 个 Task 逐步递进）、代码完整可执行、与设计文档一致。后端架构（LlmBackend 抽象 + Factory + Orchestrator）设计合理，前端接线覆盖了 4 个 Wizard 入口，测试计划覆盖了主要路径。

**存在 3 个 P0 级问题需在实施前修复，6 个 P1 级问题建议在实施中改进。**

---

## 🔴 P0 — 必须修复

### P0-1：缺少 `LlmBackend` 基类定义

**位置**: Task 2（受影响文件清单 + Step 1/2）

**问题**: `OpenAiBackend` 和 `AnthropicBackend` 都继承自 `configforge.services.ai.base.LlmBackend`，但计划中没有创建 `base.py` 的步骤，受影响文件清单中也未列出。这会导致 `ImportError`，所有后端无法实例化。

**修复方案**: 在 Task 2 Step 1 之前，增加创建 `configforge/services/ai/base.py`：

```python
from abc import ABC, abstractmethod

class LlmBackend(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str: ...
```

同时在受影响文件清单中补充：

```
Create: configforge/services/ai/base.py           # LlmBackend 抽象基类
```

---

### P0-2：`ai_settings.json` 路径使用相对路径，生产环境不可靠且存在安全风险

**位置**: Task 1 Step 2 `configforge/services/ai/settings.py`

**问题**:

```python
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "ai_settings.json")
```

1. 依赖 `__file__` 的位置，在不同部署方式下（pip install、Docker、打包）可能指向错误路径
2. API Key 写入源码目录，可能被 git 提交泄露

**修复方案**:

```python
_SETTINGS_DIR = os.environ.get("CONFIGFORGE_DATA_DIR", os.path.join(os.getcwd(), "data"))
SETTINGS_FILE = os.path.join(_SETTINGS_DIR, "ai_settings.json")
```

同时在 `.gitignore` 中添加 `ai_settings.json` 和 `data/`。

---

### P0-3：`PUT /settings` 空 api_key 保留已有 Key 的逻辑有漏洞

**位置**: Task 4 Step 1 `configforge/api/ai.py`

**问题**:

```python
@router.put("/settings")
async def update_settings(body: AiSettings):
    if not body.api_key:
        existing = load_settings()
        body.api_key = existing.api_key
```

前端 `SettingsPage.vue` 的 `saveSettings()` 中 `if (!body.api_key) body.api_key = ''`，用户**有意清空 Key** 时（输入框清空后保存），空字符串也会触发保留旧 Key 的逻辑，导致无法删除已配置的 Key。

**修复方案**: 使用 `Optional` 区分"未提供"和"清空"：

```python
class AiSettingsUpdate(BaseModel):
    provider: AiProvider = AiProvider.OPENAI
    api_key: str | None = None  # None = 保留旧值, "" = 清空
    base_url: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    enabled: bool = False

@router.put("/settings")
async def update_settings(body: AiSettingsUpdate):
    existing = load_settings()
    if body.api_key is None:
        body.api_key = existing.api_key  # 保留
    # else: 使用 body.api_key（可能是空字符串 = 清空）
    full_settings = AiSettings(**body.model_dump())
    save_settings(full_settings)
    return {"ok": True}
```

---

## 🟡 P1 — 建议修复

### P1-1：前端 `AiSuggestion` 类型需要扩展 `diagnose` category

**位置**: Task 7 受影响文件清单

**问题**: 现有 `types/wizard.ts` 中 `AiSuggestion.category` 类型为 `'scene' | 'columns' | 'sql' | 'mapping'`，后端新增了 `diagnose`，但前端类型未更新，受影响文件清单中也未包含 `types/wizard.ts`。

**修复方案**: 在 Task 7 中补充修改 `types/wizard.ts`：

```ts
export interface AiSuggestion {
  category: 'scene' | 'columns' | 'sql' | 'mapping' | 'diagnose'
  status: 'pending' | 'accepted' | 'rejected'
  content: string
  timestamp: number
}
```

---

### P1-2：`App.vue` 没有导航栏，"加设置入口"的描述不准确

**位置**: Task 6 Step 4

**问题**: 计划写"在导航栏加设置入口"，但实际 `App.vue` 只有 `<router-view />`，没有导航栏。各步骤视图内部有"上一步/下一步"按钮。

**修复方案**: 改为在 `App.vue` 中新增一个悬浮设置按钮（齿轮图标），或在各步骤视图的顶部区域添加设置入口。悬浮按钮方案：

```html
<!-- App.vue -->
<template>
  <div class="min-h-screen bg-slate-50 font-sans text-slate-900 antialiased">
    <router-view />
    <router-link
      to="/settings"
      class="fixed bottom-6 right-6 w-10 h-10 flex items-center justify-center bg-white border border-slate-200 rounded-full shadow-md hover:bg-slate-50 text-slate-500 hover:text-slate-700 transition-colors"
      title="AI 设置"
    >⚙</router-link>
  </div>
</template>
```

---

### P1-3：`OutputConfigTab.vue` 的 `onAiMapping` 中 `sourceCols` 为空数组

**位置**: Task 7 Step 2

**问题**:

```typescript
const sourceCols: string[] = []
for (const inp of store.inputs) {
  if (inp.fileId) {
    // source columns from the output config's source table context
  }
}
```

`sourceCols` 填充逻辑为空，AI 拿到空数组无法生成有意义的映射。

**修复方案**: 利用 `store.uploadedFiles` 中的列信息，或从 `store.inputs` 的 `config` 中提取：

```typescript
const sourceCols: string[] = []
for (const inp of store.inputs) {
  const fileMeta = store.uploadedFiles[inp.fileId]
  if (fileMeta?.columns) {
    sourceCols.push(...fileMeta.columns)
  }
}
```

---

### P1-4：`useAiSuggest` 与 `useWizardApi` 功能重叠

**位置**: Task 6 Step 1

**问题**: 现有 `useWizardApi.ts` 已封装 `fetch` + 错误处理 + loading 状态，新建的 `useAiSuggest` 做了类似的事但独立实现，风格不统一。

**修复方案**: 二选一：
- **方案 A**：在 `useWizardApi` 中添加 AI 相关方法（`suggest`、`getAiSettings`、`updateAiSettings`、`testAiConnection`），保持 API 调用风格一致
- **方案 B**：让 `useAiSuggest` 内部复用 `useWizardApi` 的 `post` 方法，避免重复封装 fetch

---

### P1-5：`test_ai_backends.py` 缺少 Mock SDK 测试

**位置**: Task 5 Step 2

**问题**: 设计文档明确要求"Mock SDK `create` 调用，不消耗真实 token"，但计划中的测试只验证了工厂创建的实例类型，没有 Mock `AsyncOpenAI` / `AsyncAnthropic` 的 `generate` 方法。

**修复方案**: 补充 Mock 测试：

```python
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.anyio
async def test_openai_generate_mock():
    settings = AiSettings(provider=AiProvider.OPENAI, api_key="sk-test")
    backend = OpenAiBackend(settings)
    backend._client = MagicMock()
    backend._client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"sql": "SELECT 1"}'))]
    ))
    result = await backend.generate("test prompt")
    assert "SELECT 1" in result

@pytest.mark.anyio
async def test_anthropic_generate_mock():
    settings = AiSettings(provider=AiProvider.ANTHROPIC, api_key="sk-test")
    backend = AnthropicBackend(settings)
    backend._client = MagicMock()
    backend._client.messages.create = AsyncMock(return_value=MagicMock(
        content=[MagicMock(text='{"sql": "SELECT 1"}')]
    ))
    result = await backend.generate("test prompt")
    assert "SELECT 1" in result
```

---

### P1-6：`mask_key` 格式不一致

**位置**: Task 1 Step 2

**问题**: 输出格式 `sk-...***f456` 中 `...` 和 `***` 语义重复，设计文档写 `sk-...***xyz`，测试写 `sk-...***f456`，不够简洁。

**修复方案**: 统一为 `sk-***...456` 或 `sk-...456`：

```python
def mask_key(key: str) -> str:
    if not key or len(key) <= 6:
        return key
    return key[:3] + "***" + key[-3:]
# sk-abc123def456 → sk-***456
```

同步更新测试断言。

---

## 🟢 P2 — 小改进建议

### P2-1：`openai` 和 `anthropic` 应放 `optional-dependencies`

AI 功能是可选的，不应强制安装这两个 SDK。建议：

```toml
[project.optional-dependencies]
ai = ["openai>=1.0", "anthropic>=0.30"]
dev = ["pytest>=7.0", "pytest-mock>=3.0", "pytest-asyncio>=0.21"]
```

---

### P2-2：`autoSuggestScene` 的 `fileColumns` 传了空对象

Task 7 Step 3 中 `fileColumns: {}`，AI 无法基于列名推断场景。应从 `store.uploadedFiles` 中提取各文件的列信息。

---

### P2-3：`build_prompt` 中 `fileColumns` 命名冲突

`category == "columns"` 的 `fileColumns` 是列表，`category == "scene"` 的 `fileColumns` 是字典，同一参数名不同类型。建议 scene 用 `columnsByFile`。

---

### P2-4：`parse_response` 对非 JSON 响应处理不够

直接返回原文时，前端 `JSON.parse(content)` 会失败。建议在 orchestrator 中无法解析时返回 `{"raw": text}`，或在 API 响应中增加 `is_json` 标记。

---

### P2-5：测试数量预估可更精确

计划写 `~160 passed（139 + ~21 新测试）`，但 Task 5 实际新增约 16 个测试（settings 3 + backends 3 + orchestrator 5 + api 5），建议更精确地写 `~155 passed`。

---

## 审核清单

| # | 级别 | 问题 | 状态 |
|---|------|------|------|
| P0-1 | 🔴 | 缺少 LlmBackend 基类定义 | ❌ 待修复 |
| P0-2 | 🔴 | settings 路径不安全 + 可能泄露 Key | ❌ 待修复 |
| P0-3 | 🔴 | Key 清空逻辑漏洞 | ❌ 待修复 |
| P1-1 | 🟡 | AiSuggestion 类型缺 diagnose | ❌ 待修复 |
| P1-2 | 🟡 | App.vue 无导航栏，设置入口描述不准确 | ❌ 待修复 |
| P1-3 | 🟡 | onAiMapping 中 sourceCols 为空 | ❌ 待修复 |
| P1-4 | 🟡 | useAiSuggest 与 useWizardApi 重叠 | ❌ 待修复 |
| P1-5 | 🟡 | 缺少 Mock SDK 测试 | ❌ 待修复 |
| P1-6 | 🟡 | mask_key 格式不一致 | ❌ 待修复 |
| P2-1 | 🟢 | openai/anthropic 应放 optional-dependencies | 💡 建议 |
| P2-2 | 🟢 | autoSuggestScene fileColumns 为空 | 💡 建议 |
| P2-3 | 🟢 | build_prompt fileColumns 命名冲突 | 💡 建议 |
| P2-4 | 🟢 | 非 JSON 响应前端解析会失败 | 💡 建议 |
| P2-5 | 🟢 | 测试数量预估不精确 | 💡 建议 |
