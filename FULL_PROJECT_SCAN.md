# CCTEST 工程全面扫描报告

> 扫描日期: 2026-05-03  
> 范围: 完整工程（PipeForge + ConfigForge + 文档）

---

## 一、工程概述

### 项目定位

CCTEST 是一个 **数据流水线工具集**，包含两个核心产品：

| 产品 | 定位 | 技术栈 | 状态 |
|------|------|--------|------|
| **PipeForge** | CLI 数据流水线引擎 | Python + Pydantic + openpyxl + sqlite3 | ✅ 可用（67 测试全通过） |
| **ConfigForge** | 可视化配置管理界面 | FastAPI + Vue 3 + Pinia + TypeScript | ⚠️ 开发中（有 Bug） |

### 工作流程

```
用户通过 ConfigForge (Web) 创建配置 → 生成 YAML 文件
→ 用户通过 PipeForge (CLI) 执行配置 → 输出 Excel 报表
```

### 目录结构

```
CCTEST/
├── src/pipeforge/          # PipeForge 引擎（Python CLI）
├── configforge/            # ConfigForge 后端（FastAPI）
├── configforge-web/        # ConfigForge 前端（Vue 3）
├── tests/                  # PipeForge 测试
├── demo/                   # 演示文件 + 截图
├── docs/superpowers/       # 设计文档 + 审核记录
├── archive/                # 归档的旧版文档
└── tmp/uploads/            # 文件上传临时目录
```

---

## 二、PipeForge（CLI 引擎）

### 做什么

PipeForge 是一个命令行工具，核心流程：**Excel 输入 → SQLite 临时库 → SQL 处理 → Excel 模板输出**。用户通过 YAML 配置文件定义流水线，引擎自动完成数据读取、处理和格式化输出。

### 怎么做

| 模块 | 职责 |
|------|------|
| `cli.py` | click 入口，参数收集，进度展示 |
| `core/engine.py` | 流程编排，插件调度，参数注入 |
| `core/context.py` | 执行上下文，统计模型 |
| `core/registry.py` | 插件注册/查找 |
| `core/sqlite.py` | 临时库管理，CRUD，事务 |
| `config/models.py` | Pydantic 模型，YAML 加载，校验 |
| `plugins/input/excel.py` | Excel 读取（read_only 模式） |
| `plugins/processor/sql.py` | SQL 执行 |
| `plugins/output/excel.py` | 两阶段写入（样式保留） |

### 问题

| 级别 | 问题 | 说明 |
|------|------|------|
| P2 | Input 用 `read_only=True` 但设计文档写「普通模式」 | 代码更合理，文档需同步 |
| P2 | Output 写文件 3 次（模板→输出→恢复列宽） | openpyxl 限制，MVP 可接受 |
| P2 | `InputSpec.config` 硬编码为 `ExcelInputConfig` | v0.2 加 CSV 时需重构 |
| P2 | Output 插件 label 为空字符串 | 日志显示 `Output '': wrote ...` |
| P2 | Context 用 `@dataclass` 而 ExecutionResult 用 Pydantic | 风格不统一 |
| P3 | `executescript` 隐式 COMMIT | 设计已明确不做跨阶段回滚 |
| P3 | SQLite 所有列默认 TEXT | 数值比较需 CAST |

**PipeForge 整体评价：完成度高，67 测试全通过，可用于生产。**

---

## 三、ConfigForge（Web 配置界面）

### 做什么

ConfigForge 是一个 Web 应用，提供 4 步向导帮助用户创建 PipeForge 的 YAML 配置文件：
1. Step 1：场景信息（名称/描述/版本）
2. Step 2：数据源配置（上传 Excel → 配置输入源）
3. Step 3：数据处理（SQL 编辑 + 输出配置，Tab 分栏）
4. Step 4：预览导出（YAML 预览 + 下载）

### 怎么做

**后端（FastAPI）**：

| 模块 | 职责 |
|------|------|
| `server.py` | FastAPI 入口，CORS，SPA 路由 |
| `api/files.py` | 文件上传（50MB 限制，.xlsx/.xls/.csv） |
| `api/preview.py` | Excel 列预览 |
| `api/wizard.py` | 向导流程 API（init-scene/infer-input/infer-output/generate） |
| `api/ai.py` | AI 建议（v0.1 返回 no-op） |
| `core/registry.py` | Generator 注册表 |
| `core/pipeline.py` | 向导流程逻辑 |
| `generators/` | 输入/输出/处理器配置生成器 |
| `services/excel_reader.py` | Excel 读取（read_only） |
| `services/yaml_builder.py` | YAML 生成 |
| `services/ai/base.py` | LLM 后端抽象 |

**前端（Vue 3）**：

| 模块 | 职责 |
|------|------|
| `stores/wizard.ts` | Pinia 状态管理（5 步向导状态） |
| `types/wizard.ts` | TypeScript 类型定义 |
| `composables/useWizardApi.ts` | 后端 API 调用 |
| `composables/useFileUpload.ts` | 文件上传 |
| `composables/useAiSuggest.ts` | AI 建议交互 |
| `views/Step1~5*.vue` | 5 步向导页面 |
| `components/step3/SqlEditorTab.vue` | SQL 编辑器 + output_tables |
| `components/step3/OutputConfigTab.vue` | 输出配置（模板/列映射） |

### 问题

#### P0 — 阻断性 Bug

##### P0-1: Step 3 向导从 4 步变成了 5 步，与设计文档不一致

设计文档 v1.3 明确是 **4 步向导**：
- Step 1: 场景信息
- Step 2: 数据源
- Step 3: 输出定义（Tab: SQL 处理 + 输出配置）
- Step 4: 预览导出

但实际代码是 **5 步**：
- Step 1: 场景信息
- Step 2: 数据源
- Step 3: 数据处理（仅 SQL）
- Step 4: 输出定义（仅输出配置）
- Step 5: 预览导出

路由表有 `/step/1` ~ `/step/5`，`Step3ProcessView.vue` 只有 SQL 编辑器，`Step4OutputView.vue` 只有输出配置。设计文档中的 Tab 分栏被拆成了两个独立步骤。

**影响**：与设计文档不一致，且 Step 3 和 Step 4 的内容量不均衡（Step 3 内容少，Step 4 内容多）。

**建议**：合并 Step 3 和 Step 4 为一个步骤，使用 Tab 分栏，与设计文档一致。或更新设计文档反映 5 步决策。

---

##### P0-2: `output_tables` 自动推断逻辑错误——从 `FROM` 提取的是源表名而非输出表名

`Step3ProcessView.vue` 的 `onMounted`：

```typescript
const m = sql.match(/\bFROM\s+(\w+)/i)
const inferred = m ? m[1] : 'result'
if (!store.processor.outputTables.includes(inferred)) {
  store.processor.outputTables.push(inferred)
}
```

`SqlEditorTab.vue` 的 `watch`：

```typescript
const tableMatch = trimmed.match(/\bFROM\s+(\w+)/i)
const tableName = tableMatch ? tableMatch[1] : 'result'
if (!store.processor.outputTables.includes(tableName)) {
  store.processor.outputTables.push(tableName)
}
```

两处都从 `FROM` 子句提取表名作为 `output_tables`。但 `FROM` 后面的是**源表**（如 `person`），不是 SQL 创建的**输出表**（如 `monthly_report`）。正确做法是从 `CREATE TABLE xxx AS` 或 `INTO xxx` 中提取。

例如 SQL `SELECT * FROM person`，`FROM` 提取的是 `person`（输入表），但 `output_tables` 应该是 SQL 创建的新表名。

**影响**：output_tables 自动填充了错误的表名，导致 source_table 下拉选项也是错误的。

**建议**：改为从 `CREATE TABLE (\w+)` 正则提取，或让用户手动填写 output_tables（更可靠）。

---

##### P0-3: `output_tables` 双重自动推断导致重复添加

`Step3ProcessView.vue` 的 `onMounted` 和 `SqlEditorTab.vue` 的 `watch` 都会自动推断 output_tables。当用户进入 Step 3 时：
1. `onMounted` 先执行，从 SQL 提取表名并 push
2. `watch` 立即触发（因为 SQL 已有值），再次提取并 push

虽然有 `includes` 检查防止重复，但两处逻辑重复且执行时机不同，容易产生不一致。

**建议**：移除 `Step3ProcessView.vue` 中的 `onMounted` 推断逻辑，只保留 `SqlEditorTab.vue` 的 `watch`。

---

#### P1 — 重要问题

##### P1-1: YamlPreview 使用硬编码模板而非后端生成的 YAML

`YamlPreview.vue` 用 Vue 模板语法手动拼接 YAML：

```vue
<pre>
scene:
  name: {{ store.scene.name }}
  ...
</pre>
```

但后端 `yaml_builder.py` 已经有完整的 YAML 生成逻辑。前端没有调用 `/api/wizard/generate` 接口，而是自己拼接。

**问题**：
- 前后端 YAML 格式可能不一致（如缩进、引号、排序）
- 后端的 `yaml_builder` 用 `yaml.dump()`，前端用字符串拼接，行为不同
- 后端接口 `/api/wizard/generate` 已实现但未被使用

**建议**：Step 5 加载时调用 `/api/wizard/generate` 获取后端生成的 YAML，而非前端拼接。

---

##### P1-2: YamlPreview 中 `output_tables` 渲染格式错误

```vue
<span class="text-blue-300">output_tables</span>:
  - <span class="text-green-300">{{ store.processor.outputTables.join(', ') }}</span>
```

`join(', ')` 会输出 `monthly_report, person`，但 YAML 列表格式应该是：

```yaml
output_tables:
  - monthly_report
  - person
```

当前输出的是：

```yaml
output_tables:
  - monthly_report, person
```

**建议**：改为 `v-for` 循环渲染每个表名。

---

##### P1-3: `OutputConfigTab.vue` 中 `outputConfig` 的 computed 有副作用

```typescript
const outputConfig = computed<ExcelOutputConfig>(() => {
  if (!store.output) {
    store.setOutput({ plugin: 'excel', config: { ... } })  // ← computed 中修改状态
  }
  return store.output!.config as ExcelOutputConfig
})
```

Vue 的 `computed` 不应有副作用（修改 store 状态）。这会导致：
- 严格模式下警告
- 不可预测的执行时机
- SSR 兼容性问题

**建议**：将初始化逻辑移到 `onMounted` 或 `watch` 中。

---

##### P1-4: `requirements.txt` 引用了不存在的 Git 仓库

```
pipeforge @ git+https://github.com/lixinyuan/pipeforge.git
```

PipeForge 的代码在本项目的 `src/pipeforge/` 下，不是独立的 Git 仓库。这个依赖无法安装。

**建议**：改为本地路径引用 `pipeforge @ file:///${PROJECT_ROOT}/src/pipeforge`，或直接在 `pyproject.toml` 中用 `sys.path` 引入。

---

##### P1-5: `static/assets/` 中有大量重复的构建产物

目录中有 **约 170 个 JS 文件**，是多次 `vite build` 的产物（每次构建生成新 hash）。没有清理旧版本，导致：
- `static/` 目录体积膨胀
- SPA 路由可能匹配到旧版本文件

**建议**：在 `vite build` 前清理 `static/` 目录，或使用 `emptyOutDir` 配置。

---

#### P2 — 建议优化

##### P2-1: `canProceed` 的 Step 3 校验只检查 SQL 非空

```typescript
if (currentStep.value === 3) return processor.value.sql.trim().length > 0
```

但设计文档要求 Step 3 还需要 output_tables 非空。当前用户可以不填 output_tables 就进入下一步。

**建议**：改为 `processor.value.sql.trim().length > 0 && processor.value.outputTables.length > 0`。

---

##### P2-2: `excel_reader.py` 的 `read_excel_info` 接受 `file_like` 参数但 `pipeline.py` 传入文件路径字符串

```python
# excel_reader.py
def read_excel_info(file_like, sheet_name=None, max_sample_rows=10):
    wb = openpyxl.load_workbook(file_like, read_only=True)

# pipeline.py
def infer_input(input_name, req):
    path = os.path.join(UPLOAD_DIR, req.file_id)
    with open(path, "rb") as f:
        info = read_excel_info(f)  # 传入文件对象 ✓
```

`pipeline.py` 正确地打开了文件再传入。但 `api/preview.py` 也调用了 `read_excel_info(path)`，直接传入路径字符串。openpyxl 的 `load_workbook` 也能接受路径字符串，所以不会报错，但与函数签名 `file_like` 的语义不一致。

**建议**：统一参数类型，要么都传路径字符串，要么都传文件对象。

---

##### P2-3: `api/preview.py` 直接接受 `dict` 而非 Pydantic 模型

```python
@router.post("/file")
async def preview_file(req: dict):
    file_id = req.get("file_id", "")
```

其他 API 端点都使用 Pydantic 模型做请求校验，唯独 preview 用了裸 `dict`，失去了类型校验和文档生成能力。

**建议**：定义 `PreviewRequest(BaseModel)` 模型。

---

##### P2-4: 前端 `useAiSuggest.ts` 的 `accept()` 只修改本地状态，不更新 store

```typescript
function accept() { if (suggestion.value) suggestion.value.status = 'accepted' }
```

这修改的是 composable 内部的 `suggestion` ref，不是 store 的 `aiSuggestions`。而 `SqlEditorTab.vue` 的 `onAcceptSuggestion` 读取的是 `store.aiSuggestions['sql']`。两者不是同一个对象。

**建议**：`accept()` 应该同步更新 store，或统一使用 store 管理 AI 建议状态。

---

##### P2-5: `goToStep` 没有防跳步校验

```typescript
function goToStep(n: number) { if (n <= currentStep.value || n <= 5) currentStep.value = n }
```

条件 `n <= currentStep.value || n <= 5` 意味着任何 n ≤ 5 都可以跳转（因为 `n <= 5` 总是先满足）。用户可以直接跳到 Step 5 而不完成前面的步骤。

**建议**：改为 `if (n >= 1 && n <= currentStep.value + 1 && n <= 5)`。

---

#### P3 — 微小问题

##### P3-1: `tmp/uploads/` 目录有 32 个文件未被清理

文件上传后没有自动清理机制（设计文档说 24h 自动清理，但代码中没有实现）。

##### P3-2: `configforge/tests/` 有 10 个测试文件但未验证是否可运行

##### P3-3: `demo/screenshots/` 有 12 张截图，建议 gitignore

---

## 四、设计层面问题

### 4.1 PipeForge 设计文档迭代充分

经历了 v0.1 ~ v0.6 共 6 轮审核，48 个问题全部修复，终版零缺陷。设计质量高。

### 4.2 ConfigForge 设计文档迭代充分

经历了 v1.0 ~ v1.3 共 4 轮审核，从 15 个问题降到 0 个。设计质量高。

### 4.3 设计与实现的偏差

| 偏差 | 设计 | 实现 | 严重性 |
|------|------|------|--------|
| 向导步骤数 | 4 步（Step 3 含 Tab） | 5 步（拆成 Step 3 + Step 4） | P0 |
| output_tables 推断 | 用户手动填写或 AI 建议 | 自动从 FROM 提取（错误） | P0 |
| YAML 生成 | 后端 `/api/wizard/generate` | 前端字符串拼接 | P1 |
| AI 建议采纳 | 更新 store 并反映到 UI | composable 和 store 状态不同步 | P2 |

---

## 五、代码质量评估

### PipeForge（后端引擎）

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | ⭐⭐⭐⭐⭐ | 三层分离，插件化，可扩展 |
| 代码质量 | ⭐⭐⭐⭐ | 清晰规范，少量风格不统一 |
| 测试覆盖 | ⭐⭐⭐⭐ | 67 个测试，覆盖核心路径 |
| 可维护性 | ⭐⭐⭐⭐⭐ | 代码结构清晰，易读易改 |

### ConfigForge 后端（FastAPI）

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | ⭐⭐⭐⭐ | 分层清晰，API 设计合理 |
| 代码质量 | ⭐⭐⭐ | preview 用裸 dict，requirements 引用不存在仓库 |
| 测试覆盖 | ⭐⭐⭐ | 有 10 个测试文件，未验证 |
| 可维护性 | ⭐⭐⭐⭐ | 结构清晰，但 Generator 模式未完全落地 |

### ConfigForge 前端（Vue 3）

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | ⭐⭐⭐⭐ | Composables + Pinia + Router 组织合理 |
| 代码质量 | ⭐⭐⭐ | computed 有副作用、YAML 拼接格式错误、goToStep 无防跳步 |
| 测试覆盖 | ⭐⭐ | 只有 1 个 store 测试文件 |
| 可维护性 | ⭐⭐⭐⭐ | 组件拆分合理，类型定义完整 |

---

## 六、问题优先级汇总

| 优先级 | 编号 | 问题 | 所属 |
|--------|------|------|------|
| **P0** | P0-1 | 向导从 4 步变 5 步，与设计文档不一致 | ConfigForge 前端 |
| **P0** | P0-2 | output_tables 从 FROM 提取的是源表名而非输出表名 | ConfigForge 前端 |
| **P0** | P0-3 | output_tables 双重自动推断逻辑重复 | ConfigForge 前端 |
| **P1** | P1-1 | YamlPreview 前端拼接而非调用后端 API | ConfigForge 前端 |
| **P1** | P1-2 | YamlPreview output_tables 格式错误（join 而非 v-for） | ConfigForge 前端 |
| **P1** | P1-3 | OutputConfigTab computed 有副作用 | ConfigForge 前端 |
| **P1** | P1-4 | requirements.txt 引用不存在的 Git 仓库 | ConfigForge 后端 |
| **P1** | P1-5 | static/assets/ 有 170 个旧构建产物未清理 | ConfigForge 构建 |
| **P2** | P2-1 | canProceed Step 3 不校验 output_tables | ConfigForge 前端 |
| **P2** | P2-2 | excel_reader 参数类型不一致 | ConfigForge 后端 |
| **P2** | P2-3 | preview API 用裸 dict 而非 Pydantic 模型 | ConfigForge 后端 |
| **P2** | P2-4 | useAiSuggest.accept() 不同步 store | ConfigForge 前端 |
| **P2** | P2-5 | goToStep 无防跳步校验 | ConfigForge 前端 |
| **P3** | P3-1 | tmp/uploads/ 32 个文件未清理 | 运维 |
| **P3** | P3-2 | configforge/tests/ 未验证 | ConfigForge 后端 |
| **P3** | P3-3 | demo/screenshots/ 建议 gitignore | 项目规范 |

---

## 七、总结

### 工程亮点

1. **PipeForge 完成度高**：核心功能完整可用，67 测试全通过，设计文档经过 6 轮审核零缺陷
2. **ConfigForge 设计充分**：设计文档经过 4 轮审核，接口契约、数据流、错误处理都考虑周到
3. **前后端分离合理**：FastAPI + Vue 3，API 设计清晰，前端 Composable 模式成熟
4. **类型安全**：后端 Pydantic 模型 + 前端 TypeScript 类型定义完整

### 核心风险

1. **设计与实现脱节**：ConfigForge 的 3 个 P0 问题都是实现偏离设计（5 步 vs 4 步、output_tables 推断逻辑错误、双重推断）
2. **前端质量待提升**：computed 副作用、YAML 拼接错误、防跳步缺失等基础问题
3. **后端接口未被使用**：`/api/wizard/generate` 已实现但前端未调用

### 建议优先级

1. **修复 3 个 P0**：合并 Step 3/4 为 Tab 分栏、修正 output_tables 推断逻辑、移除重复推断
2. **修复 5 个 P1**：调用后端 YAML API、修正 YAML 格式、消除 computed 副作用、修复依赖引用、清理构建产物
3. **PipeForge 可直接交付使用**
