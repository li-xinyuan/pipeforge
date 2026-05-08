# ConfigForge 设计文档

> 产品: ConfigForge — PipeForge 配置的引导式、可视化、AI 辅助创建工具
> 文档版本: v1.0
> 日期: 2026-05-04
> 状态: 设计完成，待实现

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
| **本地优先** | 运行在 localhost，不上传文件到外部服务 |
| **AI 辅助而非替代** | AI 给出建议，用户确认/修改，最终产物是纯 YAML + 文件 |
| **产物可脱离 AI** | 生成的 YAML 和模板文件可由 PipeForge CLI 独立执行 |
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
| **后端** | Python FastAPI | 复用 PipeForge 的 Pydantic 模型和 openpyxl 能力 |
| **前端** | Vue 3 + Vite + TypeScript | SFC 天然高内聚，Composition API 与 DI 思维一致 |
| **状态管理** | Pinia | Vue 3 官方推荐，类型安全 |
| **路由** | Vue Router 4 | 4 步向导对应 4 个路由 |
| **样式** | Tailwind CSS | 快速构建，无需单独 CSS 文件 |
| **AI 后端** | 调用 LLM API（可插拔） | 生成 SQL、列映射建议、场景推断 |

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

### 2.3 目录结构

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
│   │   ├── excel_input.py           # ExcelInputGenerator
│   │   ├── csv_input.py             # CsvInputGenerator
│   │   ├── database_input.py        # DatabaseInputGenerator
│   │   ├── pdf_input.py             # PdfInputGenerator
│   │   └── ppt_input.py             # PptInputGenerator
│   ├── output/
│   │   ├── __init__.py
│   │   ├── excel_output.py          # ExcelOutputGenerator
│   │   ├── csv_output.py            # CsvOutputGenerator
│   │   ├── database_output.py       # DatabaseOutputGenerator
│   │   ├── pdf_output.py            # PdfOutputGenerator
│   │   └── ppt_output.py            # PptOutputGenerator
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
│   ├── yaml_builder.py              # YAML 序列化构建
│   └── template_builder.py          # Excel 模板生成
├── models/
│   ├── __init__.py
│   ├── wizard.py                    # 向导步骤的请求/响应模型
│   ├── config.py                    # PipeForge 配置的 Pydantic 模型
│   └── ai.py                        # AI 请求/响应模型
└── static/                          # Vue 3 构建产物（生产模式）
```

---

## 3. 向导流程

### 3.1 4 步总览

```
Step 1: 场景信息        Step 2: 数据源配置       Step 3: 输出定义        Step 4: 预览与导出
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ · 场景名称    │      │ · 上传输入文件 │      │ · SQL 编写    │      │ · YAML 预览  │
│ · 场景描述    │  →   │ · 列自动推断  │  →   │ · AI 生成 SQL │  →   │ · 模板预览   │
│ · 上传样例文件│      │ · 列预览      │      │ · 列映射配置  │      │ · 一键导出   │
│ · AI 场景推断 │      │ · AI 列建议   │      │ · AI 自动映射 │      │              │
└──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘
```

### 3.2 每步的 AI 触发点

| 步骤 | AI 触发时机 | AI 做什么 |
|------|------------|----------|
| Step 1 | 上传文件后 | 根据文件内容推断场景名称、描述 |
| Step 2 | 文件解析完成后 | 推荐列类型、检测多表关联字段 |
| Step 3 | 输入源配置完成后 | 生成 SQL（JOIN / CASE WHEN 等）、推荐列映射 |
| Step 4 | 无 | 无（仅预览和导出） |

### 3.3 步骤间数据流

```
Step 1                    Step 2                    Step 3                    Step 4
scene: {                  inputs: [                 processor: {              ┌─────────────┐
  name                     { name,                    sql,                    │ pipeline.yaml│
  description                type,                    outputTables            │ template.xlsx│
  version                    plugin,                }                         └─────────────┘
}                            table,                 output: {
  uploadedFiles: [           paramKey,                plugin,
    person.xlsx,             config: { sheet },       config: {
    attendance.xlsx          columns: [...]             template, sheet,
  ]                        },                          filename, columns
                           { ... 考勤数据 }              }
                         ]                           }
```

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
    def infer_config(self, file_path: str) -> CsvInputConfig: ...
    def build_config(self, wizard_state) -> CsvInputConfig: ...
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
    def infer_config(self, file_path: str) -> C:
        """从文件推断初始配置（填好能自动推断的字段）"""
        ...

    @abstractmethod
    def build_config(self, wizard_state: "WizardState") -> C:
        """从向导状态构建完整配置（用户确认后的最终配置）"""
        ...

    @abstractmethod
    def validate_config(self, config: C) -> list[str]:
        """校验配置，返回错误信息列表（空列表 = 通过）"""
        ...
```

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
| `/api/wizard/init-scene` | POST | `{ files: File[] }` | `SceneInitResponse` | 上传文件 → 推断场景信息 |
| `/api/wizard/infer-input/{source_id}` | POST | `{ file: File, type: str }` | `InputInferResponse` | 读取 Excel/CSV → 返回列信息 |
| `/api/wizard/infer-output` | POST | `{ inputs: InputConfig[] }` | `OutputInferResponse` | 根据输入推断输出配置 |
| `/api/wizard/generate` | POST | `WizardState` | `GenerateResponse` | 生成最终 YAML + 模板 |
| `/api/ai/suggest` | POST | `AiSuggestionRequest` | `AiSuggestionResponse` | 请求 AI 建议（SQL/映射/场景） |
| `/api/preview/file` | POST | `{ file: File, sheet?: str }` | `ColumnPreview` | 上传文件 → 返回前 N 行预览 |
| `/api/preview/yaml` | POST | `WizardState` | `{ yaml: str }` | 预览生成的 YAML 内容 |

### 5.3 服务层

| 服务 | 职责 |
|------|------|
| `excel_reader.py` | 读取 Excel 文件：工作表列表、列名、前 N 行数据、样式提取 |
| `sql_generator.py` | 模板化 SQL 生成 + AI 生成回退（JOIN 检测、CASE WHEN） |
| `yaml_builder.py` | 将 `WizardState` 序列化为 PipeForge 兼容的 YAML 字符串 |
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
| Vue Router | 4.x | 路由（4 步 + 首页） |
| Tailwind CSS | 4.x | 样式 |
| CodeMirror | 6.x | YAML/SQL 语法高亮编辑 |

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
│   │   │   ├── OutputConfig.vue      # 输出目标配置
│   │   │   ├── TemplatePreview.vue   # Excel 模板预览
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

### 6.3 核心 Composables（前端服务层）

```typescript
// useWizardApi.ts —— 对应后端 /api/wizard/*
function useWizardApi() {
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function initScene(files: File[]): Promise<SceneInitResponse>
  async function inferInputConfig(sourceId: string): Promise<InputInferResponse>
  async function inferOutputConfig(sources: InputConfig[]): Promise<OutputInferResponse>
  async function generateFinal(store: WizardState): Promise<GenerateResponse>

  return { loading, error, initScene, inferInputConfig, inferOutputConfig, generateFinal }
}
```

```typescript
// useAiSuggest.ts —— 对应后端 /api/ai/*
function useAiSuggest() {
  const suggesting = ref(false)
  const suggestion = ref<string | null>(null)

  async function askSuggestion(context: AiSuggestionRequest): Promise<void>
  function accept(): void
  async function regenerate(feedback?: string): Promise<void>

  return { suggesting, suggestion, askSuggestion, accept, regenerate }
}
```

```typescript
// useFileUpload.ts —— 文件上传 + 列预览
function useFileUpload() {
  const uploading = ref(false)
  const preview = ref<ColumnPreview | null>(null)

  async function uploadAndPreview(file: File, sheet?: string): Promise<void>
  function clearPreview(): void

  return { uploading, preview, uploadAndPreview, clearPreview }
}
```

**设计原则**：
- Composable 内部用 `ref()` 管理异步状态，不抛异常到组件层
- 所有 API 调用走 `useWizardApi` 统一出口，组件不直接调 `fetch()`
- AI 建议独立为一个 composable，因为采纳/拒绝/重新生成是独立的交互循环

### 6.4 Wizard Store（Pinia 状态管理）

```typescript
// stores/wizard.ts
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
  uploadedFiles: Map<string, File>
  aiSuggestions: Map<string, any>
}
```

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
│             └─────────────────────────────┘        │
│             已上传: person.xlsx, attendance.xlsx    │
│                                                    │
│  ┌─ AI 建议面板 ──────────────────────────┐       │
│  │ 🤖 根据上传文件，我建议：                 │       │
│  │ · 创建 2 个输入源: 人员明细、考勤数据     │       │
│  │ [采纳] [重新生成]                        │       │
│  └──────────────────────────────────────┘       │
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

#### Step 3: 输出定义

```
┌──────────────────────────────────────────────────┐
│  StepIndicator  ●●● 输出定义 ○ 导出               │
├──────────────────────────────────────────────────┤
│                                                    │
│  SQL 处理器:                                       │
│  ┌──────────────────────────────────────────┐     │
│  │ CREATE TABLE monthly_report AS            │     │
│  │ SELECT p.姓名, p.部门, a.出勤天数,        │     │
│  │   CASE WHEN CAST(a.迟到次数 AS INTEGER)   │     │
│  │   > 3 THEN '需关注' ELSE '正常' END ...   │     │
│  │ FROM person p LEFT JOIN attendance a ...  │     │
│  └──────────────────────────────────────────┘     │
│  [🤖 AI 生成 SQL]  [🧪 验证语法] 验证通过 ✓        │
│                                                    │
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
│  │     ...                                   │     │
│  └──────────────────────────────────────────┘     │
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

## 7. 关键设计决策

### 7.1 为什么 ConfigForge 是独立项目而非 PipeForge 子模块？

| 维度 | 嵌入 PipeForge | 独立项目 |
|------|---------------|---------|
| 依赖 | PipeForge 引入前端依赖 | 各自独立 |
| 部署 | CLI 工具带着 Web 前端 | Web App 独立运行 |
| 职责 | 违反单一职责 | 清晰分离 |
| 版本 | 耦合发版 | 独立迭代 |

**决策：独立项目。** 两个项目共享 `pipeforge.config.models` 包作为唯一的接口契约。

### 7.2 为什么 Vue 3 而不是 React？

| 维度 | Vue 3 | React |
|------|-------|-------|
| SFC | template/script/style 天然分离 | JSX 混合 |
| 心智模型 | ref/reactive 直观 | useState/useEffect 闭包陷阱 |
| Composition API | 与 Java DI 思维一致 | hooks 规则多 |
| 学习曲线（后端开发者） | 低 | 中高 |
| 生态 | 够用 | 更丰富但冗余 |

**决策：Vue 3。** 对于中等复杂度的 4 步向导，Vue 3 刚好够用不冗余，SFC 的高内聚特性与项目 OOP 原则一致。

### 7.3 AI 能力边界

AI 在 ConfigForge 中的角色是**建议者**，不是**决策者**：

- AI **可以**：推断场景、生成 SQL 草稿、推荐列映射、检测表关联
- AI **不可以**：自动保存配置、覆盖用户修改、在用户未确认的情况下推进步骤
- 所有 AI 输出都有 **[采纳] [重新生成]** 按钮，用户始终拥有最终决定权

---

## 8. 版本路线图

| 版本 | 内容 | 状态 |
|------|------|------|
| v0.1 | PipeForge MVP（CLI + 3 插件 + 67 测试） | ✅ 已完成 |
| v0.2 | ConfigForge v0.1：Excel 输入/输出 + SQL 处理器的配置生成 | 📋 设计中 |
| v0.3 | CSV 输入/输出 + Jinja2 模板处理器 | 🔮 规划中 |
| v0.4 | Database 输出 + Python 脚本处理器 | 🔮 规划中 |
| v0.5 | PDF/PPT 输入/输出 | 🔮 规划中 |
| v0.6 | API 输入/输出 | 🔮 规划中 |

---

## 9. 附录：与 PipeForge 的接口契约

ConfigForge 生成的 YAML 文件必须符合 PipeForge 的 `SceneConfig` Pydantic 模型规范：

```python
# pipeforge.config.models — 两个项目共享的契约
class SceneConfig(BaseModel):
    scene: SceneMeta
    inputs: list[InputSpec]
    processors: list[ProcessorSpec]
    output: OutputSpec | None
```

ConfigForge 不依赖 PipeForge 的运行时（engine/sqlite/registry），只依赖 `pipeforge.config.models` 包做配置校验。
