# 数据检查点 (Data Checkpoints) — 设计文档 v0.1

**日期**: 2026-06-03  
**状态**: 已确认

---

## 1. 目标

在数据处理管道的任意位置插入检查规则，执行时自动验证数据质量。检查不通过可配置为阻断或警告。目标是保证最终输出的稳定性和正确性。

---

## 2. 核心原则

- **确定性执行**: 所有检查规则编译为具体的、可重复执行的类型，不保留"运行时 AI 判断"的模糊规则
- **自然语言是输入方式，不是规则类型**: 用户可以用自然语言描述规则，AI 翻译为具体规则类型后存储；存储和执行的永远只有具体类型
- **可扩展**: 新增规则类型只需加一个 Pydantic 模型 + 一个 executor 函数

---

## 3. 数据模型

### 3.1 检查规则（PipeForge / YAML 层）

```python
# 所有规则类型的基类 — discriminated union
class RowCountRule(BaseModel):
    type: Literal["row_count"] = "row_count"
    table: str                          # 检查哪张表，默认是当前步骤的输出表
    min: int | None = None
    max: int | None = None

class FieldNotNullRule(BaseModel):
    type: Literal["field_not_null"] = "field_not_null"
    table: str
    field: str
    min_rate: float                     # 非空率下限，0.0-1.0

class FieldRangeRule(BaseModel):
    type: Literal["field_range"] = "field_range"
    table: str
    field: str
    min: float | None = None
    max: float | None = None

class RowCountRatioRule(BaseModel):
    type: Literal["row_count_ratio"] = "row_count_ratio"
    source_table: str                   # 参照表（如输入表）
    target_table: str                   # 当前表（如输出表）
    min_ratio: float | None = None
    max_ratio: float | None = None

# 扩展：加新类型时追加到 CheckRule 的 Union
CheckRule = Annotated[
    RowCountRule | FieldNotNullRule | FieldRangeRule | RowCountRatioRule,
    Field(discriminator="type")
]
```

### 3.2 检查点

在 YAML 配置层，检查点是独立的配置块，`step_index` 指明挂载位置：

```python
class StepCheckpoint(BaseModel):
    step_index: int                     # 挂载的步骤索引（-1=最终输出）
    rules: list[CheckRule] = []
    on_failure: Literal["block", "warn"] = "block"

class CheckpointConfig(BaseModel):
    checkpoints: list[StepCheckpoint] = []
```

在 Wizard 层的 `ProcessorConfig` 中嵌入时，去掉 `step_index`（数组位置隐含）：

```python
class ProcessorConfig(BaseModel):
    # ... 现有字段 ...
    checkpoints: list[CheckRule] = []   # 内嵌时不带 step_index
    on_failure: Literal["block", "warn"] = "block"
```

### 3.3 ConfigForge 后端（Wizard 层）

检查点嵌入到现有的 `ProcessorConfig` 和 `OutputTarget` 中：

```python
class ProcessorConfig(BaseModel):
    # ... 现有字段 ...
    checkpoints: list[StepCheckpoint] = []
```

### 3.4 规则来源（前端专用，不持久化到 YAML）

仅在 Wizard UI 中用于回显规则创建方式。提交到后端时，`natural_language_text` 不参与序列化。

```python
class RuleSource(BaseModel):
    source: Literal["template", "natural_language"] = "template"
    natural_language_text: str | None = None  # AI 翻译前的原文，用于 UI 展示
```

### 3.5 前端类型（对应 TypeScript）

```typescript
// 与后端 CheckRule 一一对应
type CheckRule =
  | { type: "row_count"; table: string; min?: number; max?: number }
  | { type: "field_not_null"; table: string; field: string; min_rate: number }
  | { type: "field_range"; table: string; field: string; min?: number; max?: number }
  | { type: "row_count_ratio"; source_table: string; target_table: string; min_ratio?: number; max_ratio?: number }

interface StepCheckpoint {
  step_index: number
  rules: CheckRule[]
  on_failure: "block" | "warn"
}
```

---

## 4. 架构

### 4.1 规则执行流程

```
Pipeline Engine 执行步骤 → 产生输出表
       ↓
StepCheckpoint.rules 逐一执行
       ↓
rule.executor(table, context) → (pass, message) | (fail, message)
       ↓
  ┌─ 全部 pass → 继续下一步
  └─ 有 fail →
       ├─ on_failure=block → 停止管道，返回 CheckpointError
       └─ on_failure=warn  → 记录警告，继续执行
```

### 4.2 执行器注册（与现有 PluginRegistry 模式一致）

```python
# PipeForge 新增 pipeforge/core/checkpoints.py
from pipeforge.config.models import CheckRule

_CHECK_EXECUTORS: dict[str, Callable] = {}

def register_check(type: str):
    """装饰器：注册检查规则执行器"""
    def decorator(fn):
        _CHECK_EXECUTORS[type] = fn
        return fn
    return decorator

def execute_check(rule: CheckRule, db: SQLiteManager) -> tuple[bool, str]:
    executor = _CHECK_EXECUTORS.get(rule.type)
    if not executor:
        raise ValueError(f"Unknown check rule type: {rule.type}")
    return executor(rule, db)
```

### 4.3 AI 翻译自然语言

当用户在 UI 中选择"自然语言描述"输入规则时：
1. 前端将自然语言文本发给后端 `/api/ai/translate-checkpoint`
2. 后端 LLM prompt：`将以下数据检查需求翻译为具体的检查规则 JSON："{用户输入}"。可用的规则类型：[row_count, field_not_null, field_range, row_count_ratio]。表名默认用当前步骤的输出表。`
3. LLM 返回具体的 `CheckRule` JSON
4. 前端将其填入规则列表，同时保留 `RuleSource.natural_language_text` 用于回显

**关键**：翻译只发生一次（创建/编辑规则时），执行时不调 AI。

---

## 5. UI 设计

### 5.1 位置

在 ProcessorCard 和 OutputConfigTab 底部新增可折叠区域：

```
┌─ ProcessorCard ─────────────────────────────┐
│  步骤名称 [xxxx]  输入表 [xxxx]              │
│  SQL 编辑器 ...                              │
│  ────────────────────────────────────────── │
│  ▸ 数据检查 (1 条规则)          [展开/折叠]   │
└─────────────────────────────────────────────┘
```

展开后：
```
  ┌─ 规则 1 ──────────────────────────────────┐
  │  类型: [行数范围 ▾]  严重度: [阻断 ▾]     │
  │  表名: result1                            │
  │  最小行数: 1000   最大行数: (不限制)        │
  │  [删除此规则]                              │
  └───────────────────────────────────────────┘
  [+ 添加规则]  [用自然语言描述...]  [AI 翻译]
```

- 默认折叠，不影响现有体验
- 模板模式：下拉选类型 → 填参数
- 自然语言模式：输入框 → 点"AI 翻译" → 自动填到上面的模板表单中

---

## 6. v0.1 范围

### 实现

| 组件 | 内容 |
|------|------|
| 后端模型 | `CheckRule` (row_count + row_count_ratio)、`StepCheckpoint` |
| 执行器 | `row_count`、`row_count_ratio` 两个 executor |
| 前端类型 | 对应 TypeScript 类型定义 |
| 前端 UI | ProcessorCard 内嵌可折叠检查区域，支持模板模式 |
| AI 翻译 | 后端 `/api/ai/translate-checkpoint` 端点 |

### 延期

| 组件 | 版本 |
|------|------|
| `field_not_null`、`field_range` 规则 | v0.2 |
| 自然语言输入 UI（翻译按钮） | v0.2 |
| OutputConfigTab 中的检查点 | v0.2 |
| 检查失败的 AI 诊断建议 | v0.3 |

---

## 7. 文件变更预估

| 文件 | 操作 |
|------|------|
| `src/pipeforge/config/models.py` | 修改 — 新增 CheckRule 模型 |
| `src/pipeforge/core/checkpoints.py` | 新建 — 规则注册 + 执行器 |
| `src/pipeforge/core/engine.py` | 修改 — 步骤执行后调用检查 |
| `configforge/models/wizard.py` | 修改 — ProcessorConfig 新增 checkpoints |
| `configforge/api/ai.py` | 修改 — 新增 translate-checkpoint 端点 |
| `configforge/generators/yaml.py` | 修改 — YAML 输出包含检查配置 |
| `configforge-core-web/src/types/wizard.ts` | 修改 — 新增前端类型 |
| `configforge-web/src/components/step3/ProcessorCard.vue` | 修改 — 内嵌检查区域 |
| `configforge-web/src/components/step3/CheckpointSection.vue` | 新建 — 检查规则编辑组件 |

---

## 8. 验证方式

1. 定义一个 `row_count` 规则 → 跑管道 → 验证规则触发
2. 定义 `on_failure: "warn"` → 验证警告不阻断
3. 类型检查通过 + 后端/前端全量测试通过
