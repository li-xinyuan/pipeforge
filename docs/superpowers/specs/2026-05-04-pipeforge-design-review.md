# PipeForge 设计再审 —— Superpowers 方法论视角

> 基线: DESIGN_v6.md (高阶设计 v0.6 终版) + DETAILED_DESIGN.md (详细设计)  
> 方法论: Superpowers brainstorming 流程  
> 日期: 2026-05-04  
> 背景: 安装 superpowers 全套技能后，用新的方法论重新审视 PipeForge 设计

---

## 审查方法

采用**方案 C：核心假设挑战 + 定向审查**：

1. 挑战 5 个核心架构假设，每个用替代方案对比
2. 用 superpowers 四维度（范围/边界/错误/简洁性）定向扫描

审查视角：Java 后端程序员，推崇经典设计模式，高内聚低耦合，健壮性+可扩展性优先。

---

## 第一部分：核心假设挑战

### 假设 #1：为什么是 SQLite 作为中间层？

| 方案 | 优势 | 劣势 |
|------|------|------|
| **DuckDB** | 分析查询更快，原生支持 CSV/Parquet，同样有 Python 包 | 多一个依赖，安装包 ~30MB |
| **Pandas DataFrame** | Python 用户熟，内存操作方便 | 依赖 numpy+pandas ~50MB+ |
| **纯 Python dict/list** | 零依赖 | 无 SQL，JOIN/聚合得手写代码 |

**结论**：SQLite 站得住。`sqlite3` 是 Python 内置模块，零依赖优势对 CLI 工具重要。SQL 天然适合 JOIN/聚合/CASE 场景。

---

### 假设 #2：为什么是三段式管道？

| 方案 | 优势 | 劣势 |
|------|------|------|
| **两端式**（Input → Output） | 更简单 | 无法做跨源 JOIN 和复杂转换 |
| **DAG 任意节点图** | 最灵活 | MVP 过度设计 |
| **单脚本**（Python 直接写） | 最灵活 | 失去"配置固化"的核心价值 |

**结论**：三段式是正确抽象。SQLite 作为中间层是关键的架构洞见——每个阶段只需知道 SQLite 表，不需要知道其他阶段的内部格式。

---

### 假设 #3：为什么是插件体系？

> 这是最需要认真挑战的假设。Superpowers 第一性原则：YAGNI。MVP 只有 3 个插件。

| 方案 | 优势 | 劣势 |
|------|------|------|
| **硬编码**（if plugin=="excel" → … ） | 极简，3 个 if 分支 | v0.2 加 CSV 时要改引擎代码 |
| **函数注册**（dict 映射） | 比类简单，比硬编码好扩展 | 失去类的状态管理 |
| **保留插件体系** | 策略模式 + 工厂模式 + 注册模式，经典 OOP | 代码量稍多 |

**结论**：保留完整插件体系。

从 Java OOP 视角重新审视：
- `Plugin[C]` 泛型 = 策略模式 + 类型契约，IDE 可静态分析
- `InputPlugin` / `ProcessorPlugin` / `OutputPlugin` 空子类 = 接口隔离，各自是独立扩展点
- `PluginRegistry` + `@register_plugin` = 工厂 + 注册模式，添加新插件不修改引擎
- 参数注入保留在引擎 = 依赖注入模式，插件不耦合运行时参数获取方式
- 空子类不是"冗余代码"，是**语义类型标记**和**未来扩展点**。砍掉后 v0.2 加回来就是 breaking change

---

### 假设 #4：为什么是 YAML + Pydantic？

**结论**：直接通过。YAML 人可读、AI 可生成、支持注释。Pydantic v2 强类型校验启动前发现配置错误。

**修正**：`extra` 策略从 `"ignore"` + 手动 warning 检测改为 `"forbid"`——拼写错误当场报错，省掉 ~40 行检测代码，零额外复杂。v0.2 需要向前兼容时，新字段配默认值即可。

---

### 假设 #5：为什么是 openpyxl + 三阶段写入？

**结论**：通过。openpyxl 是 Python Excel 生态的事实标准。三阶段写入是保留模板样式+列宽的唯一可行方案。

```
阶段 1 (普通模式): 读模板 → 提取表头样式 + column_dimensions + freeze_panes
阶段 2 (write_only): 创建新文件 → set freeze_panes → 写表头(带样式) → 写数据
阶段 3 (普通模式): 重新打开 → set column_dimensions → 保存
```

---

## 第二部分：四维度定向扫描

### 维度 1：MVP 范围（YAGNI）

逐项审视：

| 功能 | 判断 | 理由 |
|------|------|------|
| Excel 输入 | ✅ 保留 | 核心场景 |
| Excel 输出 | ✅ 保留 | 模板保留样式是差异化价值 |
| SQL 处理 | ✅ 保留 | JOIN/CASE/聚合，核心能力 |
| 单 SQL 处理器 | ✅ 保留 | `processors` 列表已为 v0.2 预留 |
| CLI `--param` + 交互式 | ✅ 保留 | 覆盖两类用户 |
| `--cleanup` / `--verbose` | ✅ 保留 | CLI 标配，cleanup 是资源管理，verbose 是可观测性 |
| `scene.version` | ✅ 保留 | 向前兼容，Java 程序员从 day one 考虑 |
| Logger 类 | ✅ 保留 | 依赖倒置——稳定接口，未来切文件日志不改变调用方 |
| `config/loader.py` 独立文件 | ✅ 保留 | 关注点分离——models 定义数据，loader 编排 I/O+校验 |
| `RequiredParam` Pydantic 模型 | ✅ 保留 | CLI-引擎类型安全契约 |

**结论**：MVP 范围合理，无需砍任何功能。

---

### 维度 2：模块边界（高内聚低耦合）

#### 依赖图

```
cli.py
  └── core/engine.py
        ├── config/models.py          ← 数据层（纯结构，零依赖）
        ├── config/loader.py          ← 编排层（只依赖 models）
        ├── core/registry.py          ← 独立组件（无内部依赖）
        ├── core/context.py           ← 数据层（纯结构）
        ├── core/sqlite.py            ← 基础设施（只依赖 sqlite3 标准库）
        └── plugins/
              ├── base.py             ← 抽象层
              ├── input/excel.py      ← 只依赖 base + Context
              ├── processor/sql.py    ← 只依赖 base + Context
              └── output/excel.py     ← 只依赖 base + Context
```

**依赖方向**：cli → engine → {config, registry, context, sqlite, plugins}。所有箭头向下，无循环。

#### 逐模块审查

| 模块 | 职责数 | 内聚性 | 耦合度 | 可测试性 |
|------|--------|--------|--------|---------|
| `config/models.py` | 1：数据结构定义 | 高 | 低（零依赖） | 纯数据，零 mock |
| `config/loader.py` | 1：加载编排 | 高 | 低（只依赖 models） | mock YAML 文件 |
| `core/registry.py` | 1：插件注册 | 高 | 低 | 纯逻辑，零 mock |
| `core/context.py` | 1：运行时状态容器 | 高 | 低 | 纯数据 |
| `core/sqlite.py` | 1：SQLite 适配 | 高 | 低 | 临时 SQLite fixture |
| `core/engine.py` | 2：流程编排+插件生命周期 | 可接受（天然内聚） | 中（依赖最多但单向） | 集成测试 |
| `plugins/base.py` | 1：策略接口 | 高 | 低 | 纯抽象 |
| `plugins/*/` | 1：具体策略实现 | 高 | 低 | mock Context |
| `cli.py` | 1：终端 I/O | 高 | 低（只依赖 engine） | 端到端测试 |

**engine.py 的 2 个职责**：流程编排（三阶段顺序控制）和插件生命周期管理天然内聚——两者共同完成"执行一次流水线"这个用例。强行拆分会制造人为边界。**保持现状。**

**结论**：模块边界清晰，符合高内聚低耦合。每个模块可独立单元测试。

---

### 维度 3：错误处理完备性

原设计覆盖 16 个错误场景。补充 3 个遗漏：

| 遗漏场景 | 阶段 | 处理 |
|----------|------|------|
| `columns` 配置为空列表 | 配置 | ConfigError，"至少需要一列映射" |
| `param_key` 在多个 input 中重复 | 配置 | ConfigError，"param_key '{key}' 同时被 inputs[name=X] 和 inputs[name=Y] 使用" |
| `output_dir` 无写权限 | 输出 | PipelineError，提示检查目录权限 |

#### 合法边界场景明确化

| 场景 | 行为 | 理由 |
|------|------|------|
| `inputs` 为空列表 | ✅ 合法 — processor 可直接用 SQL 创建表 | 不需要输入数据的场景 |
| 数据库查询结果 0 行 | ✅ 合法 — 输出仅表头的空 Excel | 当月无数据是正常业务场景 |

**结论**：补充 3 个错误场景，明确 2 个合法边界场景。

---

### 维度 4：架构简洁性

从 Java OOP 视角：

| 设计要素 | 评价 |
|----------|------|
| `Plugin[C]` 泛型 | 策略模式+类型契约，IDE 可静态分析。不值删 |
| 空子类 `ProcessorPlugin`/`OutputPlugin` | 语义类型标记，未来扩展点。不值删 |
| 参数注入保留在引擎 | 依赖注入模式，插件解耦运行时。不值简化 |
| `config/loader.py` 独立 | 关注点分离。不值合并 |
| Logger 类 | 依赖倒置，稳定接口。不值简化 |
| `extra="forbid"` | **唯一真正该改的** — 更严格、更少代码 |

---

## 第三部分：最终结论

### 对 DESIGN_v6.md 的修正

| # | 修正点 | HLD 位置 | 变更 |
|---|--------|---------|------|
| 1 | `extra="forbid"` 替代 `extra="ignore"` + warning | §4.7 | 拼写错误当场报错，砍掉 ~40 行检测代码 |
| 2 | 补充 `columns` 为空 → ConfigError | §3.5 | 错误场景 |
| 3 | 补充 `param_key` 重复 → ConfigError | §3.5 | 错误场景 |
| 4 | 补充 `output_dir` 无写权限 → PipelineError | §3.5 | 错误场景 |
| 5 | 明确 `inputs` 为空列表 = 合法 | §4.6 | 边界场景 |
| 6 | 明确查询结果 0 行 = 合法 | §4.4 | 边界场景 |

### 新增决策

| # | 决策 | 理由 |
|---|------|------|
| 24 | `extra="forbid"`（MVP） | 拼写错误零容忍。v0.2 配默认值即可向前兼容 |
| 25 | 空 inputs / 空查询结果为合法 | 零进零出是合理管道语义 |
| 26 | columns 为空 / param_key 重复 / output_dir 无权限 → 显式报错 | 补漏 |

### 总体评价

**DESIGN_v6.md 从 OOP 角度已经相当成熟。** 6 轮迭代沉淀下来的泛型 + 子类 + 依赖注入 + 关注点分离，经得起 Java 程序员的审视。5 个核心假设全部站得住，四维度扫描未发现需要结构性调整的问题。

真正需要修正的只有 6 个精确的小点（4 个错误场景补充 + 2 个边界场景明确化 + extra 策略调整），其余设计保持不变。
