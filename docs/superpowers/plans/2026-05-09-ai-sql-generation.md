# AI SQL 生成落地 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ConfigForge 接入真实 LLM 后端（OpenAI + Anthropic），用户在向导中通过自然语言生成 SQL、列映射、场景名。

**Architecture:** 后端 `LlmBackend` 抽象 + OpenAI/Anthropic 具体实现 + 服务端 JSON 配置持久化 + orchestrator 拼 prompt/解析响应。前端 `useAiSuggest` composable + `SettingsPage` 设置页面 + 按钮接线。每次 AI 请求从 `ai_settings.json` 读 Key，不暴露到浏览器。

**Tech Stack:** FastAPI + `openai>=1.0` + `anthropic>=0.30` + Vue 3 + Pinia

**关键约束：**
- API Key 仅存服务端，GET /settings 返回脱敏版本
- AI 默认 disabled，需用户主动开启 + 配置 Key
- Excel/CSV 路径不受影响
- 现有 139 个测试继续通过 + 新增 20+ AI 测试

---

## 受影响文件清单

```
后端:
  Modify: configforge/models/ai.py                     # 扩展 category enum, +AiProvider/AiSettings
  Create: configforge/services/ai/settings.py          # load/save/mask ai_settings.json
  Create: configforge/services/ai/openai_backend.py    # OpenAI SDK 封装
  Create: configforge/services/ai/anthropic_backend.py # Anthropic SDK 封装
  Create: configforge/services/ai/factory.py           # create_backend(settings)
  Create: configforge/services/ai/orchestrator.py      # build_prompt + parse_response
  Modify: configforge/api/ai.py                        # /suggest 真实调用, +/settings GET/PUT, +/test
  Modify: pyproject.toml                               # +openai, +anthropic 依赖
  Create: configforge/tests/test_ai_settings.py        # 配置读写脱敏测试
  Create: configforge/tests/test_ai_backends.py        # 工厂/mock 后端测试
  Create: configforge/tests/test_ai_orchestrator.py    # prompt 构建/响应解析测试
  Modify: configforge/tests/test_api_ai.py             # 扩展 api 测试

前端:
  Create: configforge-web/src/composables/useAiSuggest.ts
  Create: configforge-web/src/views/SettingsPage.vue
  Modify: configforge-web/src/router/index.ts          # +/settings 路由
  Modify: configforge-web/src/App.vue                  # 导航加设置入口
  Modify: configforge-web/src/components/step3/SqlEditorTab.vue         # "AI 生成 SQL" 接线
  Modify: configforge-web/src/components/step3/OutputConfigTab.vue      # "AI 自动映射" 接线
  Modify: configforge-web/src/views/Step1SceneView.vue                  # 场景推断接线
  Modify: configforge-web/src/views/Step2InputView.vue                  # 列分析接线
```

---

### Task 1: 后端 AI 数据模型 + settings 服务

**Files:**
- Modify: `configforge/models/ai.py`
- Create: `configforge/services/ai/settings.py`

- [ ] **Step 1: 更新 models/ai.py**

`configforge/models/ai.py` — 完整替换：

```python
from enum import Enum
from pydantic import BaseModel
from typing import Literal


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

- [ ] **Step 2: 创建 services/ai/settings.py**

`configforge/services/ai/settings.py`:

```python
import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "ai_settings.json")


def load_settings() -> "AiSettings":
    from configforge.models.ai import AiSettings
    if not os.path.exists(SETTINGS_FILE):
        return AiSettings()
    with open(SETTINGS_FILE, "r") as f:
        raw = json.load(f)
    return AiSettings(**raw)


def save_settings(settings: "AiSettings") -> None:
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings.model_dump(), f, indent=2)


def mask_key(key: str) -> str:
    if not key or len(key) <= 6:
        return key
    return key[:3] + "..." + "***" + key[-3:]
```

- [ ] **Step 3: 跑现有测试确认无回归**

```bash
cd /Users/lixinyuan/code/CCTEST && python3 -m pytest tests/ configforge/tests/ -q
```
Expected: 139 passed

- [ ] **Step 4: Commit**

```bash
git add configforge/models/ai.py configforge/services/ai/settings.py
git commit -m "feat(configforge): add AiProvider/AiSettings models and settings persistence service"
```

---

### Task 2: LLM 后端实现（OpenAI + Anthropic + Factory）

**Files:**
- Create: `configforge/services/ai/openai_backend.py`
- Create: `configforge/services/ai/anthropic_backend.py`
- Create: `configforge/services/ai/factory.py`

- [ ] **Step 1: 创建 openai_backend.py**

`configforge/services/ai/openai_backend.py`:

```python
from openai import AsyncOpenAI
from configforge.services.ai.base import LlmBackend


class OpenAiBackend(LlmBackend):
    def __init__(self, settings):
        from configforge.models.ai import AiSettings
        kwargs = {"api_key": settings.api_key}
        if settings.base_url:
            kwargs["base_url"] = settings.base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = settings.model or "gpt-4o"
        self._temperature = settings.temperature
        self._max_tokens = settings.max_tokens

    async def generate(self, prompt: str) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Always respond with valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        return resp.choices[0].message.content or ""
```

- [ ] **Step 2: 创建 anthropic_backend.py**

`configforge/services/ai/anthropic_backend.py`:

```python
from anthropic import AsyncAnthropic
from configforge.services.ai.base import LlmBackend


class AnthropicBackend(LlmBackend):
    def __init__(self, settings):
        from configforge.models.ai import AiSettings
        self._client = AsyncAnthropic(api_key=settings.api_key)
        self._model = settings.model or "claude-sonnet-4-6"
        self._max_tokens = settings.max_tokens
        self._temperature = settings.temperature

    async def generate(self, prompt: str) -> str:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system="You are a helpful assistant. Always respond with valid JSON.",
            messages=[{"role": "user", "content": prompt}],
        )
        content = resp.content[0].text if resp.content else ""
        return content
```

- [ ] **Step 3: 创建 factory.py**

`configforge/services/ai/factory.py`:

```python
from configforge.services.ai.base import LlmBackend
from configforge.models.ai import AiSettings, AiProvider


def create_backend(settings: AiSettings) -> LlmBackend:
    if settings.provider == AiProvider.ANTHROPIC:
        from configforge.services.ai.anthropic_backend import AnthropicBackend
        return AnthropicBackend(settings)
    else:
        from configforge.services.ai.openai_backend import OpenAiBackend
        return OpenAiBackend(settings)
```

- [ ] **Step 4: 跑测试确认**

```bash
cd /Users/lixinyuan/code/CCTEST && python3 -m pytest tests/ configforge/tests/ -q
```
Expected: 139 passed

- [ ] **Step 5: Commit**

```bash
git add configforge/services/ai/openai_backend.py configforge/services/ai/anthropic_backend.py configforge/services/ai/factory.py
git commit -m "feat(configforge): add OpenAI and Anthropic LLM backends with factory"
```

---

### Task 3: Orchestrator（Prompt 构建 + 响应解析）

**Files:**
- Create: `configforge/services/ai/orchestrator.py`

- [ ] **Step 1: 创建 orchestrator.py**

`configforge/services/ai/orchestrator.py`:

```python
import json
import re


SYSTEM_PROMPTS = {
    "scene": (
        "你是一个数据流水线配置专家。根据用户上传的文件信息，生成简洁的中文场景名（5-15字）"
        "和一句话描述（20-50字）。返回 JSON: {\"name\": \"...\", \"description\": \"...\"}。"
        "不要输出其他内容。"
    ),
    "columns": (
        "你是一个数据分析专家。根据文件列名和样本数据，推荐列的类型、检测可能的关联键。"
        "返回 JSON: {\"columnTypes\": {\"列名\": \"string|number|date|boolean\"}, "
        "\"joinKeys\": [{\"file1\": \"列名\", \"file2\": \"列名\"}], "
        "\"suggestedTableNames\": [\"...\"], \"suggestedParamKeys\": [\"...\"]}。"
    ),
    "sql": (
        "你是一个 SQL 专家，针对 SQLite 数据库。根据表结构和用户的自然语言需求，生成 SQLite 兼容的 SQL。"
        "注意：表名用双引号包裹，列名必须来自表结构不要编造，使用 SQLite 支持的函数"
        "（GROUP BY, COUNT, JOIN, CASE WHEN 等）。"
        "返回 JSON: {\"sql\": \"...\", \"outputTables\": [\"...\"], \"explanation\": \"简短说明\"}。"
    ),
    "mapping": (
        "你是一个数据映射专家。根据源列名和目标列名列表，推断最佳映射关系。"
        "匹配规则：语义相似（同义词、中英文对应）、名称相似（编辑距离、包含关系）、位置顺序。"
        "返回 JSON: {\"mappings\": [{\"source\": \"源列名\", \"target\": \"目标列名\"}]}。"
        "源列没有对应目标列的不要强行映射。"
    ),
    "diagnose": (
        "你是一个数据管道调试专家。根据 YAML 配置和错误日志，分析失败原因并给出修复建议。"
        "返回 JSON: {\"cause\": \"根因一句话\", \"suggestions\": [\"具体修复步骤\"], \"severity\": \"error|warning\"}。"
    ),
}


def build_prompt(category: str, context: dict) -> str:
    system = SYSTEM_PROMPTS.get(category, "")
    prompt = system + "\n\n"

    if category == "scene":
        prompt += f"用户上传了 {context.get('fileCount', 0)} 个文件: {context.get('fileNames', [])}。"
        prompt += f"各文件列名: {context.get('fileColumns', {})}。"
    elif category == "columns":
        prompt += f"文件列名: {context.get('fileColumns', [])}。"
        prompt += f"样本数据: {context.get('sampleRows', [])}。"
    elif category == "sql":
        prompt += f"表结构: {context.get('inputs', [])}。"
        prompt += f"需求: {context.get('naturalLanguage', '')}。"
    elif category == "mapping":
        prompt += f"源列: {context.get('sourceColumns', [])}。"
        prompt += f"目标列: {context.get('targetColumns', [])}。"
    elif category == "diagnose":
        prompt += f"YAML: {context.get('yaml', '')}。"
        prompt += f"错误: {context.get('errorLog', '')}。"

    return prompt


def parse_response(text: str) -> str:
    text = text.strip()
    # Try direct JSON parse first
    try:
        json.loads(text)
        return text
    except (json.JSONDecodeError, ValueError):
        pass
    # Try extract from markdown ```json block
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        block = m.group(1).strip()
        try:
            json.loads(block)
            return block
        except (json.JSONDecodeError, ValueError):
            pass
    # Return as-is
    return text
```

- [ ] **Step 2: 跑测试确认**

```bash
cd /Users/lixinyuan/code/CCTEST && python3 -m pytest tests/ configforge/tests/ -q
```
Expected: 139 passed

- [ ] **Step 3: Commit**

```bash
git add configforge/services/ai/orchestrator.py
git commit -m "feat(configforge): add AI orchestrator with prompt builder and response parser"
```

---

### Task 4: API 端点（/suggest 真实调用 + /settings + /test）

**Files:**
- Modify: `configforge/api/ai.py`

- [ ] **Step 1: 更新 api/ai.py**

`configforge/api/ai.py` — 完整替换：

```python
import asyncio
import time
from fastapi import APIRouter, HTTPException
from configforge.models.ai import AiSuggestionRequest, AiSuggestionResponse, AiSettings
from configforge.services.ai.settings import load_settings, save_settings, mask_key
from configforge.services.ai.factory import create_backend
from configforge.services.ai.orchestrator import build_prompt, parse_response

router = APIRouter()


@router.post("/suggest", response_model=AiSuggestionResponse)
async def suggest(req: AiSuggestionRequest):
    settings = load_settings()
    if not settings.enabled:
        return AiSuggestionResponse(content="AI 未配置，请先在设置中启用", category=req.category)
    try:
        backend = create_backend(settings)
        prompt = build_prompt(req.category, req.context)
        result = await asyncio.wait_for(backend.generate(prompt), timeout=30.0)
        parsed = parse_response(result)
        return AiSuggestionResponse(content=parsed, category=req.category)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="AI 响应超时，请重试")
    except Exception as e:
        msg = str(e)
        if "401" in msg or "403" in msg or "invalid" in msg.lower():
            raise HTTPException(status_code=401, detail=f"API Key 无效: {msg}")
        raise HTTPException(status_code=500, detail=f"AI 调用失败: {msg}")


@router.get("/settings")
async def get_settings():
    settings = load_settings()
    data = settings.model_dump()
    data["api_key"] = mask_key(settings.api_key)
    return data


@router.put("/settings")
async def update_settings(body: AiSettings):
    if not body.api_key:
        # Keep existing key if not provided
        existing = load_settings()
        body.api_key = existing.api_key
    save_settings(body)
    return {"ok": True}


@router.post("/test")
async def test_connection():
    settings = load_settings()
    if not settings.api_key:
        raise HTTPException(status_code=400, detail="未配置 API Key")
    try:
        backend = create_backend(settings)
        start = time.monotonic()
        await asyncio.wait_for(backend.generate("Hello, respond with just 'ok'."), timeout=15.0)
        latency_ms = int((time.monotonic() - start) * 1000)
        return {"ok": True, "provider": settings.provider.value, "model": settings.model or "default", "latency_ms": latency_ms}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="连接超时")
    except Exception as e:
        msg = str(e)
        if "401" in msg or "403" in msg:
            raise HTTPException(status_code=401, detail=f"认证失败: {msg}")
        raise HTTPException(status_code=500, detail=f"连接失败: {msg}")
```

- [ ] **Step 2: 跑全量测试确认无回归**

```bash
cd /Users/lixinyuan/code/CCTEST && python3 -m pytest tests/ configforge/tests/ -q
```
Expected: 139 passed

- [ ] **Step 3: Commit**

```bash
git add configforge/api/ai.py
git commit -m "feat(configforge): implement AI suggest with real LLM, add settings and test endpoints"
```

---

### Task 5: 后端测试（settings + backends + orchestrator + api）

**Files:**
- Create: `configforge/tests/test_ai_settings.py`
- Create: `configforge/tests/test_ai_backends.py`
- Create: `configforge/tests/test_ai_orchestrator.py`
- Modify: `configforge/tests/test_api_ai.py`

- [ ] **Step 1: 创建 test_ai_settings.py**

`configforge/tests/test_ai_settings.py`:

```python
import json
import os
import tempfile
from configforge.services.ai.settings import load_settings, save_settings, mask_key
from configforge.models.ai import AiSettings, AiProvider


def test_load_defaults():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        pass
    try:
        import configforge.services.ai.settings as mod
        orig = mod.SETTINGS_FILE
        mod.SETTINGS_FILE = f.name
        settings = load_settings()
        assert settings.enabled is False
        assert settings.provider == AiProvider.OPENAI
        assert settings.api_key == ""
        mod.SETTINGS_FILE = orig
    finally:
        os.unlink(f.name)


def test_save_and_load():
    settings = AiSettings(provider=AiProvider.ANTHROPIC, api_key="sk-test-key", enabled=True, model="claude-sonnet-4-6")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        pass
    try:
        import configforge.services.ai.settings as mod
        orig = mod.SETTINGS_FILE
        mod.SETTINGS_FILE = f.name
        save_settings(settings)
        loaded = load_settings()
        assert loaded.provider == AiProvider.ANTHROPIC
        assert loaded.api_key == "sk-test-key"
        assert loaded.model == "claude-sonnet-4-6"
        assert loaded.enabled is True
        mod.SETTINGS_FILE = orig
    finally:
        os.unlink(f.name)


def test_mask_key():
    assert mask_key("sk-abc123def456") == "sk-...***f456"
    assert mask_key("short") == "short"
    assert mask_key("") == ""
```

- [ ] **Step 2: 创建 test_ai_backends.py**

`configforge/tests/test_ai_backends.py`:

```python
from configforge.models.ai import AiSettings, AiProvider
from configforge.services.ai.factory import create_backend
from configforge.services.ai.openai_backend import OpenAiBackend
from configforge.services.ai.anthropic_backend import AnthropicBackend


def test_factory_creates_openai():
    settings = AiSettings(provider=AiProvider.OPENAI, api_key="sk-test")
    backend = create_backend(settings)
    assert isinstance(backend, OpenAiBackend)


def test_factory_creates_anthropic():
    settings = AiSettings(provider=AiProvider.ANTHROPIC, api_key="sk-test")
    backend = create_backend(settings)
    assert isinstance(backend, AnthropicBackend)


def test_factory_creates_openai_for_custom():
    settings = AiSettings(provider=AiProvider.CUSTOM, api_key="sk-test", base_url="http://localhost:8080")
    backend = create_backend(settings)
    assert isinstance(backend, OpenAiBackend)
```

- [ ] **Step 3: 创建 test_ai_orchestrator.py**

`configforge/tests/test_ai_orchestrator.py`:

```python
from configforge.services.ai.orchestrator import build_prompt, parse_response


def test_build_prompt_sql():
    prompt = build_prompt("sql", {
        "inputs": [{"name": "person", "table": "t", "columns": ["name", "age"]}],
        "naturalLanguage": "查询所有年龄大于30的人",
    })
    assert "person" in prompt
    assert "t" in prompt
    assert "年龄大于30" in prompt


def test_build_prompt_mapping():
    prompt = build_prompt("mapping", {
        "sourceColumns": ["姓名", "年龄"],
        "targetColumns": ["员工姓名", "员工年龄"],
    })
    assert "姓名" in prompt
    assert "员工姓名" in prompt


def test_parse_direct_json():
    result = parse_response('{"sql": "SELECT * FROM t"}')
    assert "SELECT" in result


def test_parse_json_from_markdown():
    result = parse_response('```json\n{"sql": "SELECT 1"}\n```')
    assert "SELECT 1" in result


def test_parse_invalid_returns_original():
    result = parse_response("plain text without json")
    assert "plain text" in result
```

- [ ] **Step 4: 扩展 test_api_ai.py**

在现有 `test_ai_suggest_returns_noop` 后追加：

```python
@pytest.mark.anyio
async def test_ai_suggest_disabled():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/ai/suggest", json={"category": "scene", "context": {}})
    assert resp.status_code == 200
    assert "未配置" in resp.json()["content"]


@pytest.mark.anyio
async def test_ai_settings_get():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/ai/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "provider" in data
    assert "enabled" in data


@pytest.mark.anyio
async def test_ai_settings_put():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put("/api/ai/settings", json={
            "provider": "openai", "api_key": "sk-keep-existing", "enabled": False,
            "temperature": 0.7, "max_tokens": 4096, "model": "", "base_url": "",
        })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.anyio
async def test_ai_settings_mask():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.put("/api/ai/settings", json={
            "provider": "openai", "api_key": "sk-abc123def456", "enabled": False,
            "temperature": 0.7, "max_tokens": 4096, "model": "", "base_url": "",
        })
        resp = await client.get("/api/ai/settings")
    assert "***" in resp.json()["api_key"]


@pytest.mark.anyio
async def test_ai_test_connection_no_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Reset settings first to clear any key
        await client.put("/api/ai/settings", json={
            "provider": "openai", "api_key": "", "enabled": False,
            "temperature": 0.7, "max_tokens": 4096, "model": "", "base_url": "",
        })
        resp = await client.post("/api/ai/test")
    assert resp.status_code == 400
```

- [ ] **Step 5: 跑全量测试**

```bash
cd /Users/lixinyuan/code/CCTEST && python3 -m pytest tests/ configforge/tests/ -v
```
Expected: ~160 passed（139 + ~21 新测试）

- [ ] **Step 6: Commit**

```bash
git add configforge/tests/
git commit -m "test(configforge): add AI settings, backends, orchestrator, and API endpoint tests"
```

---

### Task 6: 前端 Settings 页面 + 路由

**Files:**
- Create: `configforge-web/src/composables/useAiSuggest.ts`
- Create: `configforge-web/src/views/SettingsPage.vue`
- Modify: `configforge-web/src/router/index.ts`
- Modify: `configforge-web/src/App.vue`

- [ ] **Step 1: 创建 useAiSuggest.ts**

`configforge-web/src/composables/useAiSuggest.ts`:

```typescript
import { ref } from 'vue'

export function useAiSuggest() {
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
      error.value = data.detail || data.error || '未知错误'
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

- [ ] **Step 2: 创建 SettingsPage.vue**

`configforge-web/src/views/SettingsPage.vue`:

```vue
<template>
  <div class="max-w-2xl mx-auto py-8 px-4">
    <h1 class="text-2xl font-bold text-slate-900 mb-6">AI 设置</h1>

    <div class="bg-white border border-slate-200 rounded-lg p-6 space-y-5">
      <!-- Enable switch -->
      <div class="flex items-center justify-between">
        <label class="text-sm font-medium text-slate-900">启用 AI</label>
        <button
          @click="form.enabled = !form.enabled"
          :class="form.enabled ? 'bg-blue-600' : 'bg-slate-300'"
          class="relative w-11 h-6 rounded-full transition-colors"
        >
          <span :class="form.enabled ? 'translate-x-5' : 'translate-x-0.5'" class="inline-block w-5 h-5 bg-white rounded-full shadow transition-transform translate-y-0.5" />
        </button>
      </div>

      <!-- Provider -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">提供商</label>
        <select v-model="form.provider" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none bg-white">
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="custom">Custom (OpenAI-compatible)</option>
        </select>
      </div>

      <!-- Model -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">模型</label>
        <input v-model="form.model" :placeholder="defaultModel" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none" />
        <p class="text-xs text-slate-400 mt-1">留空使用默认：{{ defaultModel }}</p>
      </div>

      <!-- API Key -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">API Key</label>
        <input v-model="form.api_key" type="password" placeholder="sk-..." class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none" />
        <p v-if="maskedKey" class="text-xs text-slate-400 mt-1">当前：{{ maskedKey }}</p>
      </div>

      <!-- Base URL -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">Base URL</label>
        <input v-model="form.base_url" :placeholder="form.provider === 'openai' ? 'https://api.openai.com/v1（默认）' : '必填'" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none" />
      </div>

      <!-- Temperature -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">Temperature: {{ form.temperature }}</label>
        <input v-model.number="form.temperature" type="range" min="0" max="2" step="0.1" class="w-full" />
      </div>

      <!-- Max Tokens -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">Max Tokens</label>
        <input v-model.number="form.max_tokens" type="number" min="256" max="65536" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none" />
      </div>

      <!-- Actions -->
      <div class="flex gap-3 pt-2">
        <button @click="testConnection" :disabled="testing" class="px-4 py-2 text-sm font-medium border border-slate-200 rounded-md hover:bg-slate-50 disabled:opacity-50">{{ testing ? '测试中...' : '测试连接' }}</button>
        <button @click="saveSettings" :disabled="saving" class="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50">{{ saving ? '保存中...' : '保存设置' }}</button>
      </div>
      <p v-if="testResult" :class="testResult.ok ? 'text-green-600' : 'text-red-500'" class="text-sm">{{ testResult.msg }}</p>
      <p v-if="saveMsg" class="text-sm text-green-600">{{ saveMsg }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted } from 'vue'

interface AiSettingsForm {
  provider: string
  api_key: string
  base_url: string
  model: string
  temperature: number
  max_tokens: number
  enabled: boolean
}

const form = reactive<AiSettingsForm>({
  provider: 'openai', api_key: '', base_url: '', model: '',
  temperature: 0.7, max_tokens: 4096, enabled: false,
})

const maskedKey = ref('')
const testing = ref(false)
const saving = ref(false)
const testResult = ref<{ ok: boolean; msg: string } | null>(null)
const saveMsg = ref('')

const defaultModel = computed(() => {
  if (form.provider === 'anthropic') return 'claude-sonnet-4-6'
  return 'gpt-4o'
})

onMounted(async () => {
  try {
    const resp = await fetch('/api/ai/settings')
    if (resp.ok) {
      const data = await resp.json()
      form.provider = data.provider
      form.base_url = data.base_url
      form.model = data.model
      form.temperature = data.temperature
      form.max_tokens = data.max_tokens
      form.enabled = data.enabled
      maskedKey.value = data.api_key
    }
  } catch (_) {}
})

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    await saveSettings()
    const resp = await fetch('/api/ai/test', { method: 'POST' })
    const data = await resp.json()
    if (resp.ok) {
      testResult.value = { ok: true, msg: `连接成功！${data.provider}/${data.model}，延迟 ${data.latency_ms}ms` }
    } else {
      testResult.value = { ok: false, msg: data.detail || '连接失败' }
    }
  } catch (e) {
    testResult.value = { ok: false, msg: '网络请求失败' }
  } finally {
    testing.value = false
  }
}

async function saveSettings() {
  saving.value = true
  saveMsg.value = ''
  try {
    const body: any = { ...form }
    if (!body.api_key) body.api_key = ''
    const resp = await fetch('/api/ai/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (resp.ok) {
      saveMsg.value = '设置已保存'
      setTimeout(() => saveMsg.value = '', 3000)
    }
  } finally {
    saving.value = false
  }
}
</script>
```

- [ ] **Step 3: 更新路由**

`configforge-web/src/router/index.ts` — 添加 settings 路由（在现有路由数组中加一项）：

```typescript
{
  path: '/settings',
  name: 'Settings',
  component: () => import('../views/SettingsPage.vue'),
}
```

- [ ] **Step 4: 更新 App.vue 导航**

在导航栏加设置入口——在现有导航区加一个链接：
```html
<router-link to="/settings" class="...">⚙ 设置</router-link>
```
具体样式参照已有导航项。

- [ ] **Step 5: Commit**

```bash
git add configforge-web/src/composables/useAiSuggest.ts configforge-web/src/views/SettingsPage.vue configforge-web/src/router/index.ts configforge-web/src/App.vue
git commit -m "feat(configforge-web): add AI settings page with provider/key configuration and test connection"
```

---

### Task 7: 前端按钮接线（4 个 Wizard 入口）

**Files:**
- Modify: `configforge-web/src/components/step3/SqlEditorTab.vue`
- Modify: `configforge-web/src/components/step3/OutputConfigTab.vue`
- Modify: `configforge-web/src/views/Step1SceneView.vue`
- Modify: `configforge-web/src/views/Step2InputView.vue`

- [ ] **Step 1: SqlEditorTab.vue — "AI 生成 SQL" 按钮接线**

当前第 28 行 `<button>🤖 AI 生成 SQL</button>` 没有点击处理。添加：

```typescript
import { useAiSuggest } from '../../composables/useAiSuggest'
import { useWizardStore } from '../../stores/wizard'

const { suggesting, error: aiError, askSuggestion } = useAiSuggest()
const showNlInput = ref(false)
const nlText = ref('')

async function onAiGenerateSql() {
  if (!nlText.value.trim()) return
  const content = await askSuggestion('sql', {
    inputs: store.inputs.map(inp => ({
      name: inp.name, table: inp.table, columns: [], // filled from preview data
    })),
    naturalLanguage: nlText.value,
  })
  if (content) {
    try {
      const parsed = JSON.parse(content)
      store.processor.sql = parsed.sql || ''
      if (parsed.outputTables) store.processor.outputTables = parsed.outputTables
      store.setSuggestion('sql', { category: 'sql', status: 'pending', content: parsed.explanation || content, timestamp: Date.now() })
    } catch {
      store.processor.sql = content
    }
    showNlInput.value = false
    nlText.value = ''
  }
}
```

模板：按钮点击 `@click="showNlInput = true"`。弹出自然语言输入区：
```html
<div v-if="showNlInput" class="mt-3 p-3 bg-sky-50 border border-sky-200 rounded-lg">
  <textarea v-model="nlText" placeholder="用自然语言描述你想要的查询，例如：查询每个部门有多少员工，按人数降序" rows="3" class="w-full text-sm border border-sky-200 rounded-md px-3 py-2 focus:outline-none focus:border-sky-400" />
  <div class="flex gap-2 mt-2">
    <button @click="onAiGenerateSql" :disabled="suggesting" class="px-3 py-1 text-xs font-medium bg-sky-600 text-white rounded-md hover:bg-sky-700 disabled:opacity-50">{{ suggesting ? '生成中...' : '生成 SQL' }}</button>
    <button @click="showNlInput = false" class="px-3 py-1 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50">取消</button>
  </div>
  <p v-if="aiError" class="text-xs text-red-500 mt-1">{{ aiError }}</p>
</div>
```

- [ ] **Step 2: OutputConfigTab.vue — "AI 自动映射" 按钮接线**

当前第 87 行的 `🤖 AI 自动映射` 按钮无点击处理。添加：

```typescript
import { useAiSuggest } from '../../composables/useAiSuggest'

const { suggesting: mappingLoading, askSuggestion } = useAiSuggest()

async function onAiMapping() {
  const sourceCols: string[] = []
  for (const inp of store.inputs) {
    if (inp.fileId) {
      // source columns from the output config's source table context
    }
  }
  const targetCols = outputConfig.value.columns.map(c => c.target)
  const content = await askSuggestion('mapping', {
    sourceColumns: sourceCols,
    targetColumns: targetCols,
  })
  if (content) {
    try {
      const parsed = JSON.parse(content)
      if (parsed.mappings) {
        outputConfig.value.columns = parsed.mappings
      }
      store.setSuggestion('mapping', { category: 'mapping', status: 'pending', content, timestamp: Date.now() })
    } catch { /* ignore */ }
  }
}
```

按钮：`@click="onAiMapping"`，添加 `:disabled="mappingLoading"`。

- [ ] **Step 3: Step1SceneView.vue — 场景推断**

文件上传后自动调用 AI 推断场景名：

```typescript
import { useAiSuggest } from '../composables/useAiSuggest'

const { askSuggestion } = useAiSuggest()

async function autoSuggestScene() {
  const fileNames = Object.values(store.uploadedFiles).map((m: any) => m.originalName)
  const content = await askSuggestion('scene', { fileCount: fileNames.length, fileNames, fileColumns: {} })
  if (content) {
    try {
      const parsed = JSON.parse(content)
      if (parsed.name) store.scene.name = parsed.name
      if (parsed.description) store.scene.description = parsed.description
    } catch { /* ignore */ }
  }
}
```

在有文件上传后调用 `autoSuggestScene()`。

- [ ] **Step 4: Step2InputView.vue — 列分析**

已有 `AiSuggestPanel` 用于 columns category。添加 `useAiSuggest` 调用：

```typescript
import { useAiSuggest } from '../composables/useAiSuggest'

const { askSuggestion } = useAiSuggest()

// 在文件上传/预览数据加载后
async function analyzeColumns(fileColumns: Record<string, string[]>, sampleRows: any[]) {
  const content = await askSuggestion('columns', { fileColumns, sampleRows })
  if (content) {
    store.setSuggestion('columns', { category: 'columns', status: 'pending', content, timestamp: Date.now() })
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add configforge-web/src/components/step3/SqlEditorTab.vue configforge-web/src/components/step3/OutputConfigTab.vue configforge-web/src/views/Step1SceneView.vue configforge-web/src/views/Step2InputView.vue
git commit -m "feat(configforge-web): wire AI buttons — SQL generation, column mapping, scene inference, column analysis"
```

---

## 验证清单

- [ ] `python3 -m pytest tests/ configforge/tests/ -v` — 所有测试通过（~160 个）
- [ ] API `/api/ai/settings` GET/PUT 正常工作
- [ ] API `/api/ai/suggest` 在 disabled 时返回 no-op
- [ ] API `/api/ai/test` 在有 Key 时返回成功
- [ ] 前端 `/settings` 页面可访问，表单可提交
- [ ] "AI 生成 SQL" 按钮弹出自然语言输入框
- [ ] "AI 自动映射" 按钮调用 API
- [ ] 设置页 API Key 脱敏显示
