# ConfigForge 设计文档

> 产品: ConfigForge — PipeForge 配置的引导式、可视化、AI 辅助创建工具
> 文档版本: v1.1
> 日期: 2026-05-04
> 状态: 设计完成，待实现
>
> **v1.1 变更**: 修复 CONFIGFORGE_REVIEW.md 指出的 15 个问题（P0×3, P1×6, P2×6）

---

## 1. 愿景与定位

### 1.1 解决的问题

PipeForge 解决了"数据流水线可重复执行"的问题，但留下了另一个痛点：**配置创建门槛高**。创建一个 PipeForge 配置需要用户：

1. 手写 YAML（知道所有字段含义）
2. 写 SQL（理解表结构和业务逻辑）
3. 制作 Excel 模板（设置样式、冻结窗格等）
4. 理解列映射关系（source → target）

ConfigForge 通过**引导式 Web 界面 + AI 辅助**，将这个过程变成可视化的 4 步向导，让配置创建者只需描述需求、上传样例数据，即可获得一套可用的 PipeForge 配置。

### 1.2 核心原则

| 原则 | 说明 |
|------|------|
| **独立运行** | ConfigForge 是独立 Web 应用，不嵌入 PipeForge CLI |
| **本地优先** | 运行在 localhost，不上传文件内容到外部服务；AI 建议为可选增强功能，仅发送列名和少量样例行 |
| **AI 辅助而非替代** | AI 给出建议，用户确认/修改，最终产物是纯 YAML + 文件 |
| **产物可脱离 AI** | 生成的 YAML 和模板文件可由 PipeForge CLI 独立执行，无需 AI 运行时 |
| **OOP + 设计模式** | 面向对象、策略模式、注册中心、依赖注入 |

### 1.3 与 PipeForge 的关系

```
ConfigForge (Web App)              PipeForge (CLI)
─────────────────────              ───────────────
配置创建阶段                        配置执行阶段
· 引导式 4 步向导                  · 命令行运行
· AI 辅助生成 YAML + SQL           · 无需 AI，无需网络
· 可视化列映射                     · 读取 YAML → 执行 → 输出
· 导出 YAML + 模板文件             · 适用于每月重复执行
```

---

## 2. 架构总览

### 2.1 技术栈

| 层 | 技术 | 理由 |
|----|------|------|
| **后端** | Python FastAPI | 复用 PipeForge 的 `config.models` 作为接口契约；openpyxl 为 ConfigForge 自身依赖（文件读取、模板生成） |
| **前端** | Vue 3 + Vite + TypeScript | SFC 天然高内聚，Composition API 与 DI 思维一致 |
| **状态管理** | Pinia + pinia-plugin-persistedstate | Vue 3 官方推荐，类型安全；插件提供 localStorage 持久化 |
| **路由** | Vue Router 4 | 4 步向导对应 4 个路由 |
| **样式** | Tailwind CSS | 快速构建，无需单独 CSS 文件 |
| **AI 后端** | 调用 LLM API，提供商可插拔 | 生成 SQL、列映射建议、场景推断；支持无 AI 模式降级 |

### 2.2 物理架构

```
┌─────────────────────────────────────────────┐
│                  浏览器                      │
│  ┌───────────────────────────────────────┐  │
│  │         Vue 3 SPA (localhost:5173)    │  │
│  │  4 步向导 · 列预览 · YAML 预览 · 导出  │  │
│  └──────────────┬────────────────────────┘  │
└─────────────────┼───────────────────────────┘
                  │ HTTP /api/*
┌─────────────────┼───────────────────────────┐
│  ┌──────────────▼────────────────────────┐  │
│  │     FastAPI Server (localhost:8000)    │  │
│  │                                        │  │
│  │  api/wizard.py   ← 向导步骤 API        │  │
│  │  api/ai.py       ← AI 建议 API         │  │
│  │  api/preview.py  ← 文件预览 API        │  │
│  │                                        │  │
│  │  generators/     ← 配置生成器（策略）    │  │
│  │  services/       ← 文件解析、YAML 构建  │  │
│  └────────────────────────────────────────┘  │
│                   ConfigForge                 │
└──────────────────────────────────────────────┘
```

### 2.3 目录结构（v0.1）

```
configforge/
├── server.py                        # FastAPI 入口，挂载静态文件
├── core/
│   ├── __init__.py
│   ├── registry.py                  # GeneratorRegistry（策略注册中心）
│   └── pipeline.py                  # 配置生成流水线编排
├── generators/
│   ├── __init__.py
│   ├── base.py                      # ConfigGenerator[T] 泛型基类
│   ├── input/
│   │   ├── __init__.py
│   │   └── excel_input.py           # ExcelInputGenerator
│   ├── output/
│   │   ├── __init__.py
│   │   └── excel_output.py          # ExcelOutputGenerator
│   └── processor/
│       ├── __init__.py
│       └── sql_processor.py         # SqlProcessorGenerator
├── api/
│   ├── __init__.py
│   ├── wizard.py                    # /api/wizard/* 向导步骤接口
│   ├── ai.py                        # /api/ai/* AI 建议接口
│   └── preview.py                   # /api/preview/* 文件预览接口
├── services/
│   ├── __init__.py
│   ├── excel_reader.py              # Excel 文件读取 + 列推断
│   ├── sql_generator.py             # SQL 生成（模板 + AI）
│   ├── yaml_builder.py              # YAML 序列化构建（TS camelCase → YAML snake_case）
│   └── template_builder.py          # Excel 模板生成
├── models/
│   ├── __init__.py
│   ├── wizard.py                    # 向导步骤的请求/响应模型
│   ├── config.py                    # PipeForge 配置的 Pydantic 模型
│   └── ai.py                        # AI 请求/响应模型
└── static/                          # Vue 3 构建产物（生产模式）
```

> **扩展文件规划**：csv_input.py / csv_output.py 等扩展 Generator 在各自版本（v0.3+）实现，相应版本规划见 §8。

---

## 3. 向导流程

### 3.1 4 步总览

```
Step 1: 场景信息        Step 2: 数据源配置       Step 3: 输出定义          Step 4: 预览与导出
┌──────────────┐      ┌──────────────┐      ┌──────────────────┐      ┌──────────────┐
│ · 场景名称    │      │ · 上传输入文件 │      │ [Tab: SQL处理]    │      │ · YAML 预览  │
│ · 场景描述    │  →   │ · 列自动推断  │  →   │ · SQL 编辑器      │  →   │ · 模板预览   │
│ · 上传样例文件│      │ · 列预览      │      │ · AI 生成 SQL     │      │ · 一键导出   │
│ · AI 场景推断 │      │ · AI 列建议   │      │ [Tab: 输出配置]   │      │              │
└──────────────┘      └──────────────┘      │ · 列映射          │      └──────────────┘
                                            │ · 文件名/Sheet    │
                                            └──────────────────┘
```

> Step 3 使用 Tab 分栏设计（SQL 处理 / 输出配置），见 §6.5 Step 3 详细布局。

### 3.2 每步的 AI 触发点

| 步骤 | AI 触发时机 | AI 做什么 |
|------|------------|----------|
| Step 1 | 上传文件后 | 根据文件内容推断场景名称、描述 |
| Step 2 | 文件解析完成后 | 推荐列类型、检测多表关联字段 |
| Step 3 | 输入源配置完成后 | 生成 SQL（JOIN / CASE WHEN 等）、推荐列映射 |
| Step 4 | 无 | 无（仅预览和导出） |

### 3.3 步骤间数据流（snake_case 命名，与 PipeForge YAML 一致）

```
Step 1                    Step 2                    Step 3                    Step 4
scene: {                  inputs: [                 processor: {              ┌─────────────┐
  name                     { name,                    sql,                    │ pipeline.yaml│
  description                plugin,                  output_tables           │ template.xlsx│
  version                    table,                 }                         └─────────────┘
}                            param_key,             output: {
  uploaded_files: [          config: { sheet }        plugin,
    {file_id, name}        },                         config: {
  ]                         { ... 考勤数据 }            template,
                         ]                              sheet,
                                                        output_dir,
                                                        source_table,
                                                        filename,
                                                        columns: [
                                                          {source, target},
                                                          ...
                                                        ]
                                                      }
```

**关键修正**：
- `columns` 属于 `output.config`，不属于 `inputs`（与 PipeForge `ExcelOutputConfig` 模型一致）
- 所有字段使用 snake_case（与 PipeForge YAML 一致）
- 前端 TypeScript 侧使用 camelCase（语言惯例），序列化映射由 `yaml_builder.py` 负责

---

## 4. 可扩展插件矩阵

### 4.1 PipeForge 当前支持（v0.1）

| | Excel | CSV | Database | PDF | PPT | API |
|------|-------|-----|----------|-----|-----|-----|
| **Input** | ✅ | — | — | — | — | — |
| **Processor** | SQL ✅ |
| **Output** | ✅ | — | — | — | — | — |

### 4.2 ConfigForge 设计目标（完整矩阵）

| | Excel | CSV | Database | PDF | PPT | API |
|------|-------|-----|----------|-----|-----|-----|
| **Input** | ✅ | ✅ v0.3 | ✅ v0.4 | ✅ v0.5 | ✅ v0.5 | ✅ v0.6 |
| **Processor** | SQL ✅ · Python v0.4 · Jinja2 v0.3 |
| **Output** | ✅ | ✅ v0.3 | ✅ v0.4 | ✅ v0.5 | ✅ v0.5 | ✅ v0.6 |

### 4.3 扩展机制

ConfigForge 通过 Pydantic 判别联合（discriminated union）+ 策略模式实现类型扩展：

```python
# 新增一个类型只需两步：
# 1. 定义 Config Pydantic 模型
class CsvInputConfig(InputConfig):
    type: Literal["csv"] = "csv"
    delimiter: str = ","
    encoding: str = "utf-8"

# 2. 实现 Generator 子类并注册
@GeneratorRegistry.register("csv", "input")
class CsvInputGenerator(ConfigGenerator[CsvInputConfig]):
    def infer_config(self, source: dict) -> CsvInputConfig: ...
    def build_config(self, wizard_state: dict) -> CsvInputConfig: ...
    def validate_config(self, config: CsvInputConfig) -> list[str]: ...
```

---

## 5. 后端架构

### 5.1 核心类设计

#### ConfigGenerator 基类

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

C = TypeVar("C", bound=BaseModel)

class ConfigGenerator(ABC, Generic[C]):
    """配置生成器基类 — 策略模式"""

    @classmethod
    @abstractmethod
    def config_model(cls) -> type[C]:
        """返回此生成器对应的 Pydantic 配置模型"""
        ...

    @abstractmethod
    def infer_config(self, source: dict) -> C:
        """从原始数据源推断初始配置。
        source 结构由子类定义：
        - 文件类型: {"file_path": str, "type": "excel"}
        - 数据库:   {"conn_string": str, "type": "postgresql"}
        - API:      {"url": str, "method": "GET", "type": "api"}
        """
        ...

    @abstractmethod
    def build_config(self, wizard_state: dict) -> C:
        """从向导状态构建完整配置（用户确认后的最终配置）"""
        ...

    @abstractmethod
    def validate_config(self, config: C) -> list[str]:
        """校验配置，返回错误信息列表（空列表 = 通过）"""
        ...
```

> **v1.1 修正**：`infer_config` 参数从 `file_path: str` 改为 `source: dict`，支持非文件类型数据源（数据库、API 等）。

#### GeneratorRegistry

```python
class GeneratorRegistry:
    """策略注册中心 — 类似 PipeForge 的 PluginRegistry"""

    _generators: dict[tuple[str, str], type[ConfigGenerator]] = {}

    @classmethod
    def register(cls, name: str, category: str):
        """装饰器：注册 ConfigGenerator 子类"""
        def decorator(generator_cls):
            cls._generators[(name, category)] = generator_cls
            return generator_cls
        return decorator

    @classmethod
    def get(cls, name: str, category: str) -> type[ConfigGenerator]:
        """获取注册的生成器类"""
        key = (name, category)
        if key not in cls._generators:
            raise KeyError(f"Generator '{name}' of type '{category}' not found")
        return cls._generators[key]
```

### 5.2 API 设计

| 端点 | 方法 | 请求体 | 响应体 | 说明 |
|------|------|--------|--------|------|
| `/api/wizard/init-scene` | POST | `{ file_ids: string[] }` | `SceneInitResponse` | 根据已上传文件推断场景信息 |
| `/api/wizard/infer-input/{input_name}` | POST | `{ file_id: string, type: string }` | `InputInferResponse` | 读取 Excel/CSV → 返回列信息；`input_name` 为 InputSpec.name |
| `/api/wizard/infer-output` | POST | `{ inputs: InputConfig[] }` | `OutputInferResponse` | 根据输入推断输出配置 |
| `/api/wizard/generate` | POST | `WizardState`（不含 File 对象） | `GenerateResponse` | 生成最终 YAML + 模板 |
| `/api/ai/suggest` | POST | `AiSuggestionRequest` | `AiSuggestionResponse` | 请求 AI 建议（SQL/映射/场景） |
| `/api/preview/file` | POST | `{ file: File, sheet?: string }` | `ColumnPreview` | 上传文件 → 返回前 N 行预览 |
| `/api/preview/yaml` | POST | `WizardState`（不含 File 对象） | `{ yaml: string }` | 预览生成的 YAML 内容 |

**文件上传约束**：

| 限制项 | 值 |
|--------|-----|
| 最大文件大小 | 50MB（超限返回 413） |
| 白名单格式 | `.xlsx`、`.xls`、`.csv` |
| 大文件策略 | v0.1 不做分片；v0.3+ 实现分片上传 |

> **v1.1 修正**：
> - `source_id` → `input_name`（与 InputSpec.name 对齐）
> - `/api/wizard/generate` 和 `/api/preview/yaml` 的请求体说明加入"不含 File 对象"（文件先上传，state 存 file_id 引用）

### 5.3 服务层

| 服务 | 职责 |
|------|------|
| `excel_reader.py` | 读取 Excel 文件：工作表列表、列名、前 N 行数据、样式提取 |
| `sql_generator.py` | 模板化 SQL 生成 + AI 生成回退（JOIN 检测、CASE WHEN） |
| `yaml_builder.py` | 将 `WizardState` 序列化为 PipeForge 兼容的 YAML 字符串（snake_case） |
| `template_builder.py` | 生成带样式的 Excel 模板文件（表头样式、列宽、冻结窗格） |

---

## 6. 前端架构

### 6.1 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.5+ | UI 框架，Composition API + SFC |
| Vite | 6.x | 开发服务器 + 构建 |
| TypeScript | 5.x | 类型安全 |
| Pinia | 2.x | 状态管理（4 步共享状态） |
| pinia-plugin-persistedstate | 3.x | 自动持久化到 localStorage（防刷新丢失） |
| Vue Router | 4.x | 路由（4 步 + 首页） |
| Tailwind CSS | 4.x | 样式 |
| CodeMirror | 6.x | SQL 语法高亮编辑 |

### 6.2 项目结构

```
configforge-web/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/
│   │   └── index.ts              # Vue Router (4 steps + home)
│   ├── stores/
│   │   └── wizard.ts             # Pinia store — wizard 4步共享状态
│   ├── composables/              # 可组合逻辑 = Java Service 层
│   │   ├── useWizardApi.ts       # 调用后端 /api/wizard/* 接口
│   │   ├── useAiSuggest.ts      # 调用后端 /api/ai/* 接口
│   │   └── useFileUpload.ts     # 文件上传 + 预览
│   ├── types/
│   │   └── wizard.ts             # TypeScript 类型（对应 Pydantic 模型）
│   ├── components/
│   │   ├── common/
│   │   │   ├── StepIndicator.vue     # 步骤指示器（1-4 进度条）
│   │   │   ├── LoadingSpinner.vue
│   │   │   └── AiSuggestPanel.vue    # 通用 AI 建议面板
│   │   ├── step1/
│   │   │   └── SceneInfoForm.vue     # 场景名称、描述、版本 + 文件上传
│   │   ├── step2/
│   │   │   ├── InputSourceList.vue   # 输入源列表（可增删）
│   │   │   ├── InputSourceCard.vue   # 单个输入源配置卡片
│   │   │   └── ColumnPreview.vue     # Excel/CSV 列预览表格
│   │   ├── step3/
│   │   │   ├── SqlEditorTab.vue      # Tab 1: SQL 编辑器 + AI 生成 + 语法验证
│   │   │   ├── OutputConfigTab.vue   # Tab 2: 输出配置 + 列映射 + 文件名模板
│   │   │   └── ColumnMapping.vue     # 列映射（source → target）
│   │   └── step4/
│   │       ├── YamlPreview.vue       # YAML 语法高亮预览
│   │       ├── TemplateDownload.vue  # 模板下载按钮
│   │       └── ExportActions.vue     # 导出操作按钮组
│   └── views/
│       ├── HomeView.vue
│       ├── Step1SceneView.vue
│       ├── Step2InputView.vue
│       ├── Step3OutputView.vue
│       └── Step4ExportView.vue
```

> **v1.1 调整**：Step 3 组件拆分为 `SqlEditorTab.vue` + `OutputConfigTab.vue`（Tab 分栏），原 `OutputConfig.vue` 和 `TemplatePreview.vue` 合并进 `OutputConfigTab.vue`。

### 6.3 核心 Composables（前端服务层）

```typescript
// useWizardApi.ts —— 对应后端 /api/wizard/*
function useWizardApi() {
  const loading = ref(false)
  const error = ref<ApiError | null>(null)  // 结构化错误

  async function initScene(fileIds: string[]): Promise<SceneInitResponse>
  async function inferInputConfig(inputName: string): Promise<InputInferResponse>
  async function inferOutputConfig(sources: InputConfig[]): Promise<OutputInferResponse>
  async function generateFinal(state: WizardState): Promise<GenerateResponse>

  return { loading, error, initScene, inferInputConfig, inferOutputConfig, generateFinal }
}
```

```typescript
// useAiSuggest.ts —— 对应后端 /api/ai/*
function useAiSuggest() {
  const suggesting = ref(false)
  const suggestion = ref<AiSuggestion | null>(null)
  const error = ref<AiError | null>(null)
  const aiConfigured = ref(false)   // 服务端是否配置了 AI Key

  async function askSuggestion(context: AiSuggestionRequest): Promise<void>
  function accept(): void
  async function regenerate(feedback?: string): Promise<void>

  return { suggesting, suggestion, error, aiConfigured, askSuggestion, accept, regenerate }
}
```

```typescript
// useFileUpload.ts —— 文件上传 + 列预览
function useFileUpload() {
  const uploading = ref(false)
  const preview = ref<ColumnPreview | null>(null)
  const uploadedFiles = ref<UploadedFileMeta[]>([])  // { file_id, original_name }

  async function upload(file: File): Promise<UploadedFileMeta>
  async function previewFile(fileId: string, sheet?: string): Promise<ColumnPreview>
  function removeFile(fileId: string): void
  function clearAll(): void

  return { uploading, preview, uploadedFiles, upload, previewFile, removeFile, clearAll }
}
```

**设计原则**：
- Composable 内部用 `ref()` 管理异步状态，错误结构化为对象（含 code + recoverable），不抛异常到组件层
- 所有 API 调用走 `useWizardApi` 统一出口，组件不直接调 `fetch()`
- 文件上传独立于 WizardState：`useFileUpload` 先上传文件 → 获得 `file_id` → 存入 WizardState 的 `uploaded_files`
- AI 建议独立为一个 composable，因为采纳/拒绝/重新生成是独立的交互循环

### 6.4 Wizard Store（Pinia 状态管理）

```typescript
// types/wizard.ts —— 前端内部使用 camelCase（TS 惯例）
// 序列化为 YAML 时由 yaml_builder.py 转换为 snake_case

interface UploadedFileMeta {
  fileId: string       // 服务端返回的文件标识
  originalName: string // 原始文件名
}

interface AiSuggestion {
  content: string
  category: "scene" | "columns" | "sql" | "mapping"
  accepted: boolean
  timestamp: number
}

interface WizardState {
  currentStep: number                    // 1-4

  // Step 1: 场景信息
  scene: {
    name: string
    description: string
    version: string
  }

  // Step 2: 输入源列表
  inputs: InputSource[]

  // Step 3: 处理器 + 输出
  processor: {
    sql: string
    outputTables: string[]
  }
  output: OutputTarget

  // 元数据
  uploadedFiles: Record<string, UploadedFileMeta>  // fileId → meta
  aiSuggestions: Record<string, AiSuggestion>      // category → suggestion
}
```

> **v1.1 修正**：
> - `uploadedFiles`: `Map<string, File>` → `Record<string, UploadedFileMeta>`（可序列化、Pinia 响应式兼容）
> - `aiSuggestions`: `Map<string, any>` → `Record<string, AiSuggestion>`（具体类型定义）
> - `File` 对象独立由 `useFileUpload` 管理，文件先上传到服务端，WizardState 只存 `file_id` 引用

Pinia store 暴露的方法：

```typescript
function useWizardStore() {
  // 步骤导航
  function nextStep(): void          // 校验通过 → currentStep++
  function prevStep(): void
  function goToStep(n: number): void // 点击已完成步骤返回

  // 数据写入
  function setScene(scene: SceneInfo): void
  function addInput(input: InputSource): void
  function removeInput(index: number): void
  function updateInput(index: number, input: InputSource): void
  function setProcessor(processor: ProcessorConfig): void
  function setOutput(output: OutputTarget): void

  // 文件引用（file_id 已在 Step 1 上传完成）
  function addFileRef(fileId: string, meta: UploadedFileMeta): void
  function removeFileRef(fileId: string): void

  // 计算属性
  const canProceed: ComputedRef<boolean>        // 当前步骤是否可继续
  const stepValidation: ComputedRef<string[]>   // 当前步骤校验错误列表
  const isComplete: ComputedRef<boolean>        // 全部步骤是否完成

  return { /* state */, nextStep, prevStep, goToStep, setScene, ... }
}
```

**设计要点**：
- Store 是唯一真相源 — 4 个 View 不通过路由参数传数据，全部读写 Store
- 每步切换时 `canProceed` 自动校验，校验不通过禁用"下一步"按钮
- `stepValidation` 返回中文错误提示，组件直接渲染
- 点击已完成步骤可返回（数据不丢失），点击未开始步骤禁用
- 通过 `pinia-plugin-persistedstate` 自动持久化到 localStorage，防刷新丢失

### 6.5 页面布局

#### Step 1: 场景信息

```
┌──────────────────────────────────────────────────┐
│  StepIndicator  ● 场景信息 ○ 数据源 ○ 输出 ○ 导出  │
├──────────────────────────────────────────────────┤
│                                                    │
│  场景名称:  [___________________________]          │
│  场景描述:  [___________________________]          │
│  版    本:  [____1.0____]                          │
│                                                    │
│  上传文件:  ┌─────────────────────────────┐        │
│             │  📎 拖拽或点击上传 Excel/CSV │        │
│             │  最大 50MB，仅 .xlsx/.xls/.csv│       │
│             └─────────────────────────────┘        │
│             已上传: person.xlsx ✓, attendance.xlsx ✓│
│                                                    │
│  ┌─ AI 建议面板 ──────────────────────────┐       │
│  │ 🤖 根据上传文件，我建议：                 │       │
│  │ · 创建 2 个输入源: 人员明细、考勤数据     │       │
│  │ [采纳] [重新生成]                        │       │
│  └──────────────────────────────────────┘       │
│   ── AI 不可用时此面板不显示 ──                  │
│                                                    │
│                              [取消]  [下一步 →]    │
└──────────────────────────────────────────────────┘
```

#### Step 2: 数据源配置

```
┌──────────────────────────────────────────────────┐
│  StepIndicator  ●● 数据源配置 ○ 输出 ○ 导出        │
├──────────────────────────────────────────────────┤
│  输入源列表:                          [+ 添加]    │
│                                                    │
│  ┌─ 人员明细 (excel) ───────────────────────┐     │
│  │ 文件: person.xlsx    Sheet: [人员列表 ▼]    │     │
│  │ 表名: [person____]  参数键: [person_file]  │     │
│  │ ┌─ 列预览 ──────────────────────────┐     │     │
│  │ │ 工号 │ 姓名 │ 部门 │ 岗位 │ 入职日期│     │     │
│  │ │ 001  │ 张三 │ 研发 │ 工程师│ 2020-01│     │     │
│  │ │ 002  │ 李四 │ 产品 │ 经理  │ 2019-06│     │     │
│  │ └──────────────────────────────────┘     │     │
│  │                               [删除此源] │     │
│  └──────────────────────────────────────────┘     │
│                                                    │
│  ┌─ 考勤数据 (excel) ───────────────────────┐     │
│  │ ... (同上，可折叠)                          │     │
│  └──────────────────────────────────────────┘     │
│                                                    │
│  ┌─ AI 建议面板 ──────────────────────────┐       │
│  │ 🤖 检测到两个表的共同字段"工号"，          │       │
│  │ 建议生成 LEFT JOIN SQL 进行合并             │       │
│  │ [采纳] [重新生成]                        │       │
│  └──────────────────────────────────────┘       │
│                                                    │
│                            [← 上一步]  [下一步 →]  │
└──────────────────────────────────────────────────┘
```

#### Step 3: 输出定义（Tab 分栏）

```
┌──────────────────────────────────────────────────┐
│  StepIndicator  ●●● 输出定义 ○ 导出               │
├──────────────────────────────────────────────────┤
│  [SQL 处理]  [输出配置]          ← Tab 切换       │
│  ─────────────                                    │
│                                                    │
│  ▸ SQL 处理 Tab（选中时）:                          │
│  ┌──────────────────────────────────────────┐     │
│  │ CREATE TABLE monthly_report AS            │     │
│  │ SELECT p.姓名, p.部门, a.出勤天数,        │     │
│  │   CASE WHEN CAST(a.迟到次数 AS INTEGER)   │     │
│  │   > 3 THEN '需关注' ELSE '正常' END ...   │     │
│  │ FROM person p LEFT JOIN attendance a ...  │     │
│  └──────────────────────────────────────────┘     │
│  [🤖 AI 生成 SQL]  [🧪 验证语法]  验证通过 ✓       │
│                                                    │
│  ▸ 输出配置 Tab（选中时）:                          │
│  ─────────── 输出配置 ───────────                  │
│  输出插件: [excel ▼]                               │
│  Sheet:    [月度人员报表________]                   │
│  文件名:   [月度考勤报表_{{date:%Y%m%d}}.xlsx]      │
│                                                    │
│  ┌─ 列映射 ─────────────────────────────┐         │
│  │  源列 (SQL输出)    →    目标列 (模板)  │         │
│  │  姓名                →    姓名           │         │
│  │  部门                →    部门           │         │
│  │  岗位                →    岗位           │         │
│  │  出勤天数            →    出勤天数       │         │
│  │  迟到次数            →    迟到次数       │         │
│  │  加班小时            →    加班小时       │         │
│  │  考勤状态            →    考勤状态       │         │
│  └──────────────────────────────────────┘         │
│  [🤖 AI 自动映射]                                   │
│                                                    │
│                            [← 上一步]  [下一步 →]  │
└──────────────────────────────────────────────────┘
```

> **v1.1 调整**：Step 3 拆为两个 Tab，降低单页交互密度。下一步按钮需同时校验两个 Tab 的数据完整性。

#### Step 4: 预览与导出

```
┌──────────────────────────────────────────────────┐
│  StepIndicator  ●●●● 预览与导出                    │
├──────────────────────────────────────────────────┤
│                                                    │
│  ┌─ pipeline.yaml ─────────────────────────┐     │
│  │ scene:                                    │     │
│  │   name: 月度人员考勤报表                   │     │
│  │   description: 汇总人员明细和考勤数据...    │     │
│  │   version: "1.0"                          │     │
│  │ inputs:                                   │     │
│  │   - name: 人员明细                         │     │
│  │     plugin: excel                          │     │
│  │     table: person                          │     │
│  │     param_key: person_file                 │     │
│  │     config:                                │     │
│  │       sheet: 人员列表                       │     │
│  │   - name: 考勤数据                         │     │
│  │     plugin: excel                          │     │
│  │     table: attendance                      │     │
│  │     ...                                   │     │
│  │ processors:                                │     │
│  │   - name: 数据合并与统计                    │     │
│  │     plugin: sql                            │     │
│  │     ...                                   │     │
│  │ output:                                    │     │
│  │   plugin: excel                            │     │
│  │   config:                                  │     │
│  │     columns:                               │     │
│  │       - source: 姓名                       │     │
│  │         target: 姓名                       │     │
│  │       ...                                 │     │
│  └──────────────────────────────────────────┘     │
│  [📋 复制]  [📄 下载 .yaml]  [🔄 刷新预览]         │
│                                                    │
│  导出选项:                                         │
│  ┌─────────────────────────────────────┐          │
│  │ 📄 pipeline.yaml      [下载] [复制]  │          │
│  │ 📊 monthly_report_template.xlsx     │          │
│  │    [下载模板]                        │          │
│  │ 📁 一键打包下载 (YAML + 模板)        │          │
│  └─────────────────────────────────────┘          │
│                                                    │
│                            [← 上一步]  [完成 ✓]    │
└──────────────────────────────────────────────────┘
```

### 6.6 StepIndicator 组件逻辑

```
● 已完成  ◐ 当前  ○ 未开始

状态流转:
- 点击"下一步" → 当前步骤标记为已完成，下一步标记为当前
- 点击已完成步骤 → 跳转到该步骤（不丢失后续步骤的数据）
- 点击未开始步骤 → 禁用
- 在非最后一步修改数据 → 该步骤之后的所有步骤标记为"需重新确认"
```

### 6.7 组件设计原则

1. **views/ 只做布局和组合**，不写业务逻辑
2. **业务逻辑在 composables/**（等价 Java Service 层）
3. **共享状态在 stores/wizard.ts**（Pinia，等价于带响应式的 DTO）
4. **components/ 按步骤分子目录**，每个组件职责单一
5. **所有 API 通信通过 composables**，组件不直接调 `fetch()`

---

## 7. AI 配置

### 7.1 API Key 管理

| 项目 | 方案 |
|------|------|
| **Key 存储** | 环境变量（`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`），后端读取，不经过前端 |
| **提供商切换** | 后端配置文件 `provider: "openai" | "anthropic"`，通过 Pydantic Settings 加载 |
| **提供商可插拔** | `services/ai/` 下按提供商分子类（`OpenAIBackend`、`AnthropicBackend`），统一 `LlmBackend` 接口 |

### 7.2 数据发送策略

AI 调用**仅发送**以下数据到 LLM API：
- 列名（如 `["工号", "姓名", "部门", "岗位"]`）
- 前 3 行样例数据（不含全量数据）
- 用户填写的场景名称和描述

**不发送**：
- 完整文件内容
- 文件名（可能含敏感路径信息）

### 7.3 无 AI 模式降级

| 场景 | 行为 |
|------|------|
| 未配置 API Key | 所有 AI 建议按钮灰显 + tooltip "AI 未启用"；SQL 必须手写；列映射必须手动配置 |
| API 调用超时 | 前端展示 `ErrorBanner`（warning 级别），提示"AI 建议超时，请重试或手动配置" |
| API 返回错误 | 前端展示错误详情，相关功能回退为手动模式 |

### 7.4 用户确认机制

在首次触发 AI 建议前，前端弹窗展示即将发送的数据摘要，用户需点击"确认发送"后才会调用 AI API：

```
┌─ AI 数据发送确认 ──────────────────────┐
│                                         │
│  AI 功能将发送以下数据到 LLM 服务商：      │
│  · 列名: 工号, 姓名, 部门, 岗位, 入职日期 │
│  · 样例行: 3 行                           │
│  · 场景名称: 月度人员考勤报表              │
│                                         │
│  ⚠️ 不会发送文件内容或敏感数据            │
│                                         │
│  [ 取消 ]  [ 确认发送 ]                  │
└─────────────────────────────────────────┘
```

---

## 8. 错误处理

### 8.1 错误分类

| 级别 | 含义 | 示例 | 前端展示 |
|------|------|------|---------|
| **warning** | 可恢复，不阻塞流程 | AI 建议超时 | 黄色横幅，3s 自动消失 |
| **error** | 当前步骤不可提交 | 必填字段为空、SQL 语法错误 | 红色横幅 + 表单内联错误提示 |
| **fatal** | 全流程不可用 | 后端连接失败 | 全屏错误页 + 重试按钮 |

### 8.2 后端统一错误响应格式

```json
{
  "error": "SQL 语法错误: near \"SELEC\"",
  "code": "SQL_SYNTAX_ERROR",
  "recoverable": true
}
```

所有 API 异常通过 FastAPI 统一异常处理器拦截，返回上述格式。

### 8.3 前端错误组件

- `ErrorBanner.vue`：通用错误横幅（`level: "warning" | "error"`）
- `FatalError.vue`：全屏致命错误页
- Composable `useErrorHandler.ts`：统一错误分发逻辑

---

## 9. 状态持久化

### 9.1 浏览器端

| 层级 | 方案 |
|------|------|
| **自动保存** | `pinia-plugin-persistedstate` 将 WizardStore 自动持久化到 localStorage |
| **触发时机** | 每次 store 变更自动写入（debounce 500ms） |
| **恢复时机** | 页面加载时自动恢复；用户点击"取消"时清除 |
| **版本管理** | localStorage key 带版本号（`wizard_state_v1`），升级时自动迁移或清除 |

### 9.2 服务端（v0.2+）

| 功能 | 方案 |
|------|------|
| **保存草稿** | `POST /api/sessions` — 将 WizardState 序列化为 JSON 存储 |
| **恢复草稿** | `GET /api/sessions/{id}` — 返回 WizardState JSON |
| **存储方式** | SQLite 文件（与 PipeForge 技术栈一致） |

> v0.1 只需 localStorage 持久化，服务端存储排入 v0.2。

---

## 10. 部署方案

### 10.1 开发模式

```
# 终端 1: 后端
cd configforge
uvicorn server:app --reload --port 8000

# 终端 2: 前端
cd configforge-web
npm run dev    # Vite dev server on :5173
```

前端 `vite.config.ts` 配置代理：`/api/*` → `http://localhost:8000`。

### 10.2 单进程生产模式

```bash
# 构建前端 → 复制到 configforge/static/
cd configforge-web && npm run build
cp -r dist/* ../configforge/static/

# 启动 FastAPI（自动挂载 static/）
cd configforge
uvicorn server:app --host 0.0.0.0 --port 8000
```

`server.py`:
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()
# ... 注册 API 路由 ...
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

### 10.3 Docker 部署

```yaml
# docker-compose.yml
services:
  configforge:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

Dockerfile：多阶段构建（Node.js 阶段构建前端 → Python 阶段复制产物 + 运行后端）。

---

## 11. 测试策略

### 11.1 测试矩阵

| 层级 | 工具 | 范围 | v0.1 最低覆盖 |
|------|------|------|-------------|
| **后端单元** | pytest | Generator 逻辑、服务层函数、模型校验 | 核心逻辑 100% |
| **后端 API** | httpx (ASGI transport) | 端点请求/响应、错误码、文件上传 | 每个端点至少 1 个 happy path + 1 个 error case |
| **前端单元** | Vitest | Composables 逻辑、Store 计算属性 | 所有 composable 核心方法 |
| **前端组件** | Vue Test Utils | 组件渲染、交互事件、条件分支 | 每个 Step 页面至少 1 个快照测试 |
| **E2E** | Playwright | 完整向导流程 | v0.2+ 引入 |

### 11.2 后端测试示例

```python
# tests/test_api_wizard.py
async def test_init_scene_returns_scene_name():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/wizard/init-scene", json={
            "file_ids": ["file_123"]
        })
    assert response.status_code == 200
    assert "scene_name" in response.json()

async def test_init_scene_no_files_returns_error():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/wizard/init-scene", json={
            "file_ids": []
        })
    assert response.status_code == 422
```

### 11.3 前端测试示例

```typescript
// tests/composables/useWizardApi.test.ts
describe("useWizardApi", () => {
  it("loading is true during request", async () => {
    const { loading, initScene } = useWizardApi()
    const promise = initScene(["file_1"])
    expect(loading.value).toBe(true)
    await promise
    expect(loading.value).toBe(false)
  })
})
```

---

## 12. 关键设计决策

### 12.1 为什么 ConfigForge 是独立项目而非 PipeForge 子模块？

| 维度 | 嵌入 PipeForge | 独立项目 |
|------|---------------|---------|
| 依赖 | PipeForge 引入前端依赖 | 各自独立 |
| 部署 | CLI 工具带着 Web 前端 | Web App 独立运行 |
| 职责 | 违反单一职责 | 清晰分离 |
| 版本 | 耦合发版 | 独立迭代 |

**决策：独立项目。** 两个项目共享 `pipeforge.config.models` 包作为唯一的接口契约。

### 12.2 为什么 Vue 3 而不是 React？

| 维度 | Vue 3 | React |
|------|-------|-------|
| SFC | template/script/style 天然分离 | JSX 混合 |
| 心智模型 | ref/reactive 直观 | useState/useEffect 闭包陷阱 |
| Composition API | 与 Java DI 思维一致 | hooks 规则多 |
| 学习曲线（后端开发者） | 低 | 中高 |
| 生态 | 够用 | 更丰富但冗余 |

**决策：Vue 3。** 对于中等复杂度的 4 步向导，Vue 3 刚好够用不冗余，SFC 的高内聚特性与项目 OOP 原则一致。

### 12.3 AI 能力边界

AI 在 ConfigForge 中的角色是**建议者**，不是**决策者**：

- AI **可以**：推断场景、生成 SQL 草稿、推荐列映射、检测表关联
- AI **不可以**：自动保存配置、覆盖用户修改、在用户未确认的情况下推进步骤
- 所有 AI 输出都有 **[采纳] [重新生成]** 按钮，用户始终拥有最终决定权
- 所有 AI 调用前展示即将发送的数据摘要，用户需确认后才发送

---

## 13. 版本路线图

| 版本 | 内容 | 状态 |
|------|------|------|
| v0.1 | PipeForge MVP（CLI + 3 插件 + 67 测试） | ✅ 已完成 |
| v0.2 | ConfigForge v0.1：Excel 输入/输出 + SQL 处理器的配置生成 | 📋 设计中 |
| v0.3 | CSV 输入/输出 + Jinja2 模板处理器 + 大文件分片上传 | 🔮 规划中 |
| v0.4 | Database 输出 + Python 脚本处理器 | 🔮 规划中 |
| v0.5 | PDF/PPT 输入/输出 | 🔮 规划中 |
| v0.6 | API 输入/输出 | 🔮 规划中 |

---

## 14. 附录：与 PipeForge 的接口契约

ConfigForge 生成的 YAML 文件必须符合 PipeForge 的 `SceneConfig` Pydantic 模型规范：

```python
# pipeforge.config.models — 两个项目共享的契约
class SceneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene: SceneMeta
    inputs: list[InputSpec] = []
    processors: list[ProcessorSpec] = []
    output: OutputSpec | None = None
```

> **v1.1 修正**：补充了 `inputs`、`processors` 的默认值 `= []` 和 `output = None`，与 PipeForge `models.py:92-98` 一致。

ConfigForge 不依赖 PipeForge 的运行时（engine/sqlite/registry），只依赖 `pipeforge.config.models` 包做配置校验。

---

## 附录 B：v1.1 变更清单

| 编号 | 优先级 | 问题 | 变更位置 |
|------|--------|------|---------|
| P0-1 | 接口错误 | `columns` 错放在 inputs 下 | §3.3 数据流图 + §6.5 Step 4 YAML 预览 |
| P0-2 | 命名规范 | 数据流使用 camelCase | §3.3 数据流图全部改为 snake_case |
| P0-3 | 接口不一致 | §14 SceneConfig 缺少默认值 | §14 补充 `= []` / `= None` |
| P1-1 | 文档矛盾 | §2.1 与 §12.1 依赖描述矛盾 | §2.1 技术栈理由改为准确表述 |
| P1-2 | 技术问题 | `Map<string, File>` 不可序列化 | §6.4 WizardState: `Map` → `Record`；`File` → `UploadedFileMeta`；新增 `useFileUpload` 管理文件生命周期 |
| P1-3 | 接口缺失 | `source_id` 未定义 | §5.2 API 表改为 `input_name`；§6.3 `inferInputConfig` 参数同步修改 |
| P1-4 | 设计问题 | Step 3 职责过重 | §3.1 + §6.5 Step 3 改为 Tab 分栏（SQL 处理 / 输出配置）；§6.2 组件目录同步拆分 |
| P1-5 | 接口设计 | `infer_config(file_path)` 不通用 | §5.1 基类参数改为 `source: dict`；§4.3 示例同步 |
| P1-6 | 设计缺失 | 缺少 AI 配置管理 | 新增 §7 "AI 配置"：Key 管理、数据发送策略、无 AI 模式降级、用户确认机制 |
| P2-1 | 设计缺失 | 缺少错误处理策略 | 新增 §8 "错误处理"：三级错误分类、统一响应格式、前端错误组件 |
| P2-2 | 设计缺失 | 缺少会话/状态持久化 | 新增 §9 "状态持久化"：localStorage + pinia-plugin-persistedstate（v0.1）；服务端草稿（v0.2） |
| P2-3 | 需求缺失 | 缺少文件上传限制 | §5.2 新增文件上传约束表 |
| P2-4 | 设计缺失 | 缺少部署方案 | 新增 §10 "部署方案"：开发/单进程生产/Docker 三种模式 |
| P2-5 | 文档误导 | v0.1 目录结构含未实现文件 | §2.3 目录结构只列 v0.1 实际文件；扩展文件在 §13 版本路线图中规划 |
| P2-6 | 设计缺失 | 缺少测试策略 | 新增 §11 "测试策略"：测试矩阵 + 后端/前端示例代码 |
