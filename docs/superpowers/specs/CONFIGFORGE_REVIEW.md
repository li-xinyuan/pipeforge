# ConfigForge 设计文档审核

> 审核文档: docs/superpowers/specs/2026-05-04-configforge-design.md  
> 对照基线: PipeForge DESIGN_v7.md + 实际代码 (models.py / pipeline.yaml)  
> 审核日期: 2026-05-03

---

## 一、与 PipeForge 的接口契约问题

### P0-1: §3.3 数据流中 `inputs[].config.columns` 不存在

§3.3 步骤间数据流：

```
inputs: [
  {
    name, type, plugin, table, paramKey,
    config: { sheet },
    columns: [...]          ← ❌ InputSpec 没有 columns 字段
  }
]
```

对照 PipeForge 实际代码 [models.py](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/config/models.py)：

```python
class InputSpec(BaseModel):
    name: str
    plugin: str
    table: str
    param_key: str
    config: ExcelInputConfig   # 只有 sheet 字段，没有 columns

class ExcelInputConfig(BaseModel):
    file: str | None = None
    sheet: str = "Sheet1"
```

**`columns` 字段属于 `OutputSpec.config.columns`（`ExcelOutputConfig`），不属于 Input。** 这是一个根本性的数据模型错误——如果按此数据流实现，生成的 YAML 配置将无法通过 PipeForge 的 Pydantic 校验。

**建议**：将 `columns` 从 inputs 移到 output 部分：

```
inputs: [
  { name, plugin, table, param_key, config: { sheet } }
]
output: {
  plugin, config: { template, sheet, filename, columns: [...] }
}
```

---

### P0-2: §3.3 数据流使用 camelCase，与 PipeForge YAML 规范不一致

§3.3 中：

```
paramKey        ← 实际应为 param_key
outputTables    ← 实际应为 output_tables
uploadedFiles   ← 实际应为 uploaded_files
```

PipeForge 的 YAML 配置使用 **snake_case**（与 Pydantic 模型一致），参见 [pipeline.yaml](file:///Users/lixinyuan/code/CCTEST/demo/pipeline.yaml)：

```yaml
param_key: person_file
output_tables:
  - monthly_report
```

ConfigForge 生成的 YAML 必须使用 snake_case，否则 PipeForge 无法解析。数据流图作为接口定义，应该使用与最终产物一致的命名规范。

**建议**：§3.3 数据流中所有字段名改为 snake_case，与 PipeForge YAML 保持一致。

---

### P0-3: §9 接口契约中 `SceneConfig` 定义与实际代码不一致

§9 附录：

```python
class SceneConfig(BaseModel):
    scene: SceneMeta
    inputs: list[InputSpec]          # ← 缺少默认值
    processors: list[ProcessorSpec]  # ← 缺少默认值
    output: OutputSpec | None
```

实际代码 [models.py:92-98](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/config/models.py#L92)：

```python
class SceneConfig(BaseModel):
    scene: SceneMeta
    inputs: list[InputSpec] = []              # 有默认值
    processors: list[ProcessorSpec] = []      # 有默认值
    output: OutputSpec | None = None
```

缺少默认值会导致：没有 inputs/processors 的场景无法创建，这与 PipeForge 的实际行为不符（测试中有 `TestNoInputPipeline`）。

**建议**：§9 补充默认值，与实际代码一致。

---

## 二、文档内部一致性问题

### P1-1: §2.1 与 §7.1 对依赖范围的描述矛盾

§2.1 技术栈：

> 后端: Python FastAPI — **复用 PipeForge 的 Pydantic 模型和 openpyxl 能力**

§7.1 决策：

> ConfigForge **不依赖 PipeForge 的运行时**（engine/sqlite/registry），**只依赖 pipeforge.config.models 包**做配置校验。

如果只依赖 `config.models` 包，就不能「复用 openpyxl 能力」（openpyxl 不在 models 包里）。ConfigForge 自己需要用 openpyxl 来读取用户上传的 Excel 文件、生成模板文件，这个依赖是 ConfigForge 自己的，不是从 PipeForge 复用的。

**建议**：§2.1 改为「复用 PipeForge 的 Pydantic 配置模型作为接口契约，openpyxl 为 ConfigForge 自身依赖」。

---

### P1-2: §6.4 WizardState 使用 `Map<string, File>` 不可序列化

§6.4 Pinia Store：

```typescript
uploadedFiles: Map<string, File>
aiSuggestions: Map<string, any>
```

**问题 1**：Pinia 不推荐在 state 中使用 `Map`——`Map` 不是响应式的（Vue 3 的 `reactive()` 对 Map 的支持有限）。应使用 `Record<string, File>` 或 `ref<Map>` 配合 `markRaw`。

**问题 2**：`File` 对象无法序列化为 JSON。但 §5.2 中 `/api/wizard/generate` 的请求体是 `WizardState`——如果整个 state 作为请求体发送，`File` 对象会导致序列化失败。

**建议**：
- `uploadedFiles` 改为 `Record<string, string>` 存储文件路径（文件先上传到服务器，返回路径引用）
- 或将文件上传与 WizardState 分离：文件通过独立 API 上传，state 只存服务器返回的 file_id
- `aiSuggestions` 改为 `Record<string, AiSuggestion>` 并定义具体类型

---

### P1-3: §5.2 API 中 `source_id` 未定义

`/api/wizard/infer-input/{source_id}` 中的 `source_id` 是什么？

- 不是 InputSpec 的字段（InputSpec 有 `name`、`table`、`param_key`，没有 `id`）
- 不是 WizardState 的字段
- 没有在任何地方定义这个标识符的生成规则

**建议**：明确 `source_id` 的来源。建议使用 `input_index`（列表下标）或 `input_name`（InputSpec.name），与 PipeForge 的数据模型对齐。

---

### P1-4: Step 3 职责过重——合并了 Processor + Output

4 步向导中：
- Step 1: 场景信息（1 个表单）
- Step 2: 数据源配置（N 个输入源卡片）
- **Step 3: SQL 编写 + AI 生成 + 列映射 + 输出配置**（至少 4 个独立交互区域）
- Step 4: 预览导出

Step 3 承载了两个完全不同的概念（处理器逻辑 + 输出格式），且交互密度远高于其他步骤。用户在 Step 3 的工作量可能是其他步骤的 3-4 倍。

**建议**：
- 方案 A：拆分为 5 步向导（Step 3: 处理器 / Step 4: 输出 / Step 5: 预览）
- 方案 B：保持 4 步但在 Step 3 内部分为两个 Tab（「SQL 处理」和「输出配置」）

---

## 三、技术可行性问题

### P1-5: `ConfigGenerator.infer_config(file_path)` 接口过于文件中心化

基类定义：

```python
@abstractmethod
def infer_config(self, file_path: str) -> C:
```

但并非所有输入源都基于文件：
- `DatabaseInputGenerator`：需要连接字符串，不是文件路径
- `ApiInputGenerator`：需要 URL + 认证信息，不是文件路径

当前接口强制所有 Generator 接受 `file_path`，对非文件类型的输入源不适用。

**建议**：改为更通用的接口：

```python
@abstractmethod
def infer_config(self, source: dict) -> C:
    """从数据源信息推断配置。source 的结构由子类定义。"""
```

或使用策略模式，让每个 Generator 定义自己的 source 类型。

---

### P1-6: 缺少 AI API Key 管理方案

文档多次提到「AI 辅助」「调用 LLM API」，但完全没有涉及：
- API Key 存储在哪里？（环境变量？配置文件？前端传入？）
- 支持哪些 LLM 提供商？（OpenAI？Anthropic？本地模型？）
- API 调用失败时的降级策略？（ConfigForge 是否可以在无 AI 模式下使用？）
- 本地优先原则下，API Key 是否会发送到外部？

§1.2 说「本地优先，不上传文件到外部服务」，但 AI 调用必然会将文件内容（列名、样例数据）发送到 LLM API。这与「本地优先」原则存在张力。

**建议**：
- 增加「AI 配置」章节：API Key 管理、支持的 LLM 提供商、降级策略
- 明确说明：AI 建议功能需要网络连接，文件元数据（列名、前 N 行）会发送到 LLM API
- 提供无 AI 模式（纯手动配置）作为降级方案

---

## 四、缺失项

### P2-1: 缺少错误处理策略

PipeForge 设计文档花了大量篇幅定义错误分类和处理策略。ConfigForge 作为 Web 应用，错误场景更多：
- 文件上传失败（大小超限、格式不支持）
- AI API 调用超时/失败
- 生成的 YAML 校验不通过
- 生成的 SQL 语法错误
- 前后端通信失败

**建议**：增加错误处理章节，至少覆盖：前端错误展示策略、后端错误码规范、AI 降级方案。

---

### P2-2: 缺少会话/状态持久化方案

用户在 4 步向导中填写了大量数据。如果：
- 浏览器崩溃？
- 用户误刷新页面？
- 用户想保存草稿稍后继续？

当前设计没有涉及任何持久化方案。Pinia store 默认是内存态，刷新即丢失。

**建议**：
- 使用 `pinia-plugin-persistedstate` 将 store 持久化到 localStorage
- 或提供「保存草稿」功能，将 WizardState 存储到后端

---

### P2-3: 缺少文件上传大小限制

§5.2 API 中有文件上传端点，但没有提到：
- 最大文件大小限制
- 支持的文件格式白名单
- 大文件的分片上传策略

**建议**：增加文件上传规范（如最大 50MB、仅 .xlsx/.xls/.csv）。

---

### P2-4: 缺少部署方案

文档描述了开发模式（localhost:5173 + localhost:8000），但没有说明：
- 生产模式如何部署？（Nginx 反代？FastAPI 挂载静态文件？）
- §2.3 目录结构中有 `static/` 目录（Vue 构建产物），但 `server.py` 如何挂载未说明
- 是否支持 Docker 部署？

**建议**：增加部署章节，至少说明生产模式的启动方式。

---

### P2-5: 目录结构中已包含未实现的 Generator 文件

§2.3 目录结构列出了：

```
generators/input/csv_input.py
generators/input/database_input.py
generators/input/pdf_input.py
generators/input/ppt_input.py
generators/output/csv_output.py
generators/output/database_output.py
generators/output/pdf_output.py
generators/output/ppt_output.py
```

但版本路线图显示这些要到 v0.3~v0.6 才实现。在 v0.1 的目录结构中列出未实现的文件会误导实现者。

**建议**：v0.1 目录结构只列出实际要实现的文件，v0.3+ 的文件在各自版本规划中描述。

---

### P2-6: 缺少测试策略

PipeForge 有 67 个测试用例。ConfigForge 作为 Web 应用，测试策略更复杂（前端测试 + 后端测试 + E2E 测试），但文档完全没有涉及。

**建议**：增加测试策略章节：
- 后端：pytest + httpx（FastAPI 测试客户端）
- 前端：Vitest + Vue Test Utils
- E2E：Playwright（可选）

---

## 五、总体评价

### 优点

1. **定位清晰**：ConfigForge 与 PipeForge 的职责划分（配置创建 vs 配置执行）非常明确
2. **4 步向导设计**：用户体验路径直观，每步有明确的 AI 触发点
3. **扩展矩阵**：插件矩阵 + discriminated union + 策略模式的扩展机制设计合理
4. **前端架构**：Composables + Pinia + 按步骤分目录的组织方式成熟
5. **页面布局**：4 个步骤的线框图详细且可执行

### 问题汇总

| 优先级 | 编号 | 问题 | 类型 |
|--------|------|------|------|
| **P0** | P0-1 | §3.3 inputs 包含 columns 字段，但 columns 属于 output | 接口错误 |
| **P0** | P0-2 | 数据流使用 camelCase，与 PipeForge YAML 的 snake_case 不一致 | 命名规范 |
| **P0** | P0-3 | §9 SceneConfig 缺少默认值，与实际代码不一致 | 接口不一致 |
| **P1** | P1-1 | §2.1 与 §7.1 对依赖范围描述矛盾 | 文档矛盾 |
| **P1** | P1-2 | Pinia state 使用 Map + File，不可序列化/不响应式 | 技术问题 |
| **P1** | P1-3 | API 中 source_id 未定义 | 接口缺失 |
| **P1** | P1-4 | Step 3 职责过重（Processor + Output 合并） | 设计问题 |
| **P1** | P1-5 | infer_config(file_path) 对非文件输入源不适用 | 接口设计 |
| **P1** | P1-6 | 缺少 AI API Key 管理和降级方案 | 设计缺失 |
| **P2** | P2-1 | 缺少错误处理策略 | 设计缺失 |
| **P2** | P2-2 | 缺少会话/状态持久化方案 | 设计缺失 |
| **P2** | P2-3 | 缺少文件上传大小限制 | 需求缺失 |
| **P2** | P2-4 | 缺少部署方案 | 设计缺失 |
| **P2** | P2-5 | v0.1 目录结构包含未实现的文件 | 文档误导 |
| **P2** | P2-6 | 缺少测试策略 | 设计缺失 |

### 建议

**3 个 P0 问题必须在实现前修复**——它们涉及 ConfigForge 与 PipeForge 的接口契约，如果按错误的数据模型实现，生成的 YAML 将无法被 PipeForge 执行。6 个 P1 问题建议在实现前明确方案。P2 问题可以在实现过程中逐步补充。
