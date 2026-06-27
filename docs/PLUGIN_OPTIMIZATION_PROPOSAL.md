# 插件系统优化技术方案

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.0 |
| 创建日期 | 2026-06-27 |
| 状态 | 待审核 |
| 审核人 | （待指定） |
| 关联任务 | T-5E-05 已知限制后续优化 |
| 前置条件 | T-5E-05 本地插件系统已完成（commit c68faf6） |

---

## 1. 背景与目标

### 1.1 当前状态

T-5E-05「本地插件系统」已完成以下工作：
- 插件自动加载机制（`pkgutil.iter_modules` 替代手动 import）
- `Plugin.config_schema()` 暴露 JSON Schema（Pydantic `model_json_schema`）
- `PluginRegistry.list_all()` 返回插件元数据
- `GET /api/plugins` 端点支持按类型过滤

全量测试 1000 passed, 31 skipped，无回归。

### 1.2 遗留的三个已知限制

| 编号 | 限制 | 影响 | 紧急度 |
|---|---|---|---|
| ① | 前端尚未实现基于 schema 的动态表单渲染 | 新增插件需前端硬编码表单 | P2 |
| ② | configforge 与 pipeforge 双轨配置模型未合并 | 翻译层脆弱，字段静默丢失 | P1 |
| ③ | json/xml/parquet/api "幽灵插件"问题 | 用户配置后执行崩溃 | P0 |

### 1.3 文档目标

本文档对三个限制进行深度分析，提出多种候选方案，给出推荐方案及详细执行步骤，供团队审核后实施。

---

## 2. 三个限制的关联性分析

三个限制并非独立问题，而是同一架构债务的三个表现面：

```
限制③幽灵插件 ──── 导致 ──→ /api/plugins 只返回 3/7 输入类型
     │                          ↓
     │                      限制①动态表单无 schema 可用
     │                          ↑
     ↓                          │
限制②双轨模型 ──── 导致 ──→ yaml_builder 翻译层崩溃
     │                          │
     └── cfg.sheet AttributeError 是③的直接表现
```

**关键结论**：逐个解决会事倍功半，必须协同设计。双轨模型是根因，幽灵插件是症状，动态表单受阻是后果。

---

## 3. 限制③：幽灵插件优化方案（P0 最紧急）

### 3.1 问题详述

configforge 声明支持 7 种输入源（excel/csv/database/json/xml/parquet/api），但 pipeforge 只实现 3 种（excel/csv/database）。用户配置 json/xml/parquet/api 输入源后，执行时三层连环崩溃：

| 层 | 失败点 | 错误信息 |
|---|---|---|
| 1. yaml_builder | `cfg.sheet`（else 分支当 excel 处理） | `AttributeError: 'JsonInputConfig' object has no attribute 'sheet'` |
| 2. pipeforge config | `InputSpec.config` 联合类型不含 Json | Pydantic 校验失败 |
| 3. PluginRegistry | `get("json", "input")` | `PluginNotFoundError` |

**用户影响**：配置到第 5 步点击执行才崩溃，错误信息对非技术用户完全不可理解。影响所有执行路径（execute/dry-run/stream）、定时任务、失败通知、AI 自愈诊断。

### 3.2 候选方案对比

| 方案 | 做法 | 工作量 | 用户体验 | 技术债 |
|---|---|---|---|---|
| A. 全实现 | 4 个新 InputPlugin + config 模型 + yaml_builder | 大（1-2周） | 完美 | 消除 |
| B. UI 灰显 | 前端 disabled + "仅预览"标签 | 小（几小时） | 损失预览能力 | 转移 |
| C. reader 适配器 | 通用 ReaderBackedPlugin 包装现有 reader | 中（3-5天） | 完美 | 消除 |
| D. 执行前校验 | _prepare_execution 抛友好 ValueError | 小（半天） | 第5步才报错 | 不消除 |
| B+D 组合 | UI 灰显 + 已存在配置兜底校验 | 小（1天） | 可接受 | 控制 |

### 3.3 方案选择理由

**方案 A 的隐藏成本**：configforge 的 reader 目前只有 `read_info`（返回样本），没有"全量读取"接口。实现 InputPlugin 需要新增全量读取逻辑，与 reader 的"轻量预览"设计冲突。4 个插件 × 全量读取 + 测试 = 实际工作量被低估。

**方案 C 的关键优势**：configforge 的 `json_reader.py` 已用 `ijson` 流式解析、`xml_reader.py` 用 `iterparse`、`parquet_reader.py` 用 pyarrow batch 迭代——这些流式原语天然适合全量加载。只需为每个 reader 新增 `iter_xxx_rows() -> Iterator[tuple]`，再用一个通用 `ReaderBackedInputPlugin` 包装。复用已有解析逻辑，避免重复实现。

**方案 B+D 的止血价值**：当前用户配置 json/xml/parquet/api 后到第 5 步才崩溃，错误信息不可理解。B+D 能在 1 天内消除"配置完才崩溃"的糟糕体验。

**api 输入的特殊性**：分页（offset/cursor）、SSRF 防护、超时、连接复用——比文件读取复杂得多。建议 api 输入延后到 v2.0.0，第一阶段只处理 json/xml/parquet。

### 3.4 推荐方案：分阶段执行

#### 第一阶段（1天）：B+D 止血

**目标**：消除"配置完才崩溃"的糟糕体验，用户看到清晰提示。

**执行步骤**：

1. **前端 InputSourceList.vue**：将 json/xml/parquet/api 4 个卡片改为 disabled，加 "仅预览" 标签（仿照 PDF/PPT 卡片样式）
   - 文件：`configforge-web/src/components/step2/InputSourceList.vue`
   - 验证：4 种类型卡片不可点击，显示"仅预览"标签

2. **后端 _prepare_execution**：在 `build_yaml` 之前校验输入类型
   - 文件：`configforge/core/pipeline.py` 的 `_prepare_execution` 方法
   - 逻辑：遍历 `state.inputs`，对 `plugin not in {"excel", "csv", "database"}` 抛出 `ValueError("输入源 'xxx' 当前仅支持预览，暂不可执行")`
   - 将 `ValueError` 纳入 `_USER_ERRORS`（`execution_service.py:33`），返回 422 而非 500
   - 验证：执行含 json 输入的 pipeline 返回 422 + 友好错误信息

3. **前端 InputSourceHeader.vue**：对已存在的 json/xml/parquet/api 输入源卡片头部加 warning tag "仅预览"
   - 文件：`configforge-web/src/components/step2/InputSourceHeader.vue`
   - 验证：已有幽灵类型输入源显示 warning 标签

**验证标准**：
- [ ] 新建输入源时 json/xml/parquet/api 卡片不可选
- [ ] 已存在的幽灵类型输入源显示"仅预览"标签
- [ ] 执行含幽灵类型的 pipeline 返回 422 + 友好错误信息
- [ ] 现有 1000 个测试无回归

#### 第二阶段（3-5天）：C 实现 reader 适配器

**目标**：json/xml/parquet 输入源可完整执行 pipeline。

**执行步骤**：

1. **为 reader 新增全量读取接口**
   - 文件：`configforge/services/json_reader.py`、`xml_reader.py`、`parquet_reader.py`
   - 新增函数：`iter_json_rows(file_content, flatten_separator) -> Iterator[tuple]`、`iter_xml_rows(...)`、`iter_parquet_rows(...)`
   - 返回：列名列表 + 行迭代器（`Iterator[tuple]`）
   - 验证：单元测试验证全量读取正确性

2. **新建 ReaderBackedInputPlugin 通用适配器**
   - 文件：`src/pipeforge/plugins/input/_reader_backed.py`
   - 设计：接收 plugin_name + reader 模块引用，`execute` 时调用 reader 的 `iter_rows` 全量加载到 SQLite
   - 注册：`@register_plugin("json", "input")` 等指向适配器
   - 验证：`PluginRegistry.get("json", "input")` 返回适配器类

3. **pipeforge config 模型扩展**
   - 文件：`src/pipeforge/config/models.py`
   - 新增：`JsonInputConfig`、`XmlInputConfig`、`ParquetInputConfig`
   - 修改：`InputSpec.config` 联合类型加入 3 种新 config
   - 验证：YAML 含 `type: json` 时能正确加载

4. **yaml_builder 补全分支**
   - 文件：`configforge/services/yaml_builder.py`
   - 修改：if/elif 补全 json/xml/parquet 分支，不再落入 else 当 excel
   - 验证：生成含 json 输入的 YAML 能被 pipeforge 正确加载

5. **_prepare_execution 文件后缀修复**
   - 文件：`configforge/core/pipeline.py` 第 252 行
   - 修改：json/xml/parquet 文件保留原后缀，不强制改名为 .csv
   - 验证：上传 .json 文件后执行 pipeline 不因后缀问题失败

6. **端到端测试**
   - 新增：`tests/test_json_input.py`、`test_xml_input.py`、`test_parquet_input.py`
   - 验证：上传 json/xml/parquet 文件 → 配置输入源 → 执行 pipeline → 数据正确写入 SQLite

**验证标准**：
- [ ] json/xml/parquet 输入源可完整执行 pipeline
- [ ] 全量数据正确加载（无内存溢出，使用流式 Iterator）
- [ ] 现有 1000 个测试无回归
- [ ] 新增 15+ 个插件测试全过

#### 第三阶段（延后 v2.0.0）：api 输入插件

**延后理由**：api 输入涉及分页（offset/cursor）、SSRF 防护、超时控制、连接复用，复杂度远高于文件读取。建议单独评估安全性后实现。

---

## 4. 限制②：双轨配置模型优化方案（P1 技术债）

### 4.1 问题详述

configforge 和 pipeforge 各有一套配置模型，通过 `yaml_builder.py`（95 行）翻译。已发现 8 个具体 bug：

| # | 问题 | 严重性 |
|---|---|---|
| 1 | yaml_builder json/xml/parquet/api 落入 else 当 excel | 高（P0） |
| 2 | database output 的 batch_size/create_table_if_not_exists 静默丢失 | 中 |
| 3 | SceneInfo.tags round-trip 丢失 | 低 |
| 4 | configforge 无 tables/sql 互斥校验，pipeforge 有 | 中 |
| 5 | ColumnMappingItem.source 无非空校验 | 低 |
| 6 | file_id → config.file 桥接无类型保证 | 中 |
| 7 | ProcessorConfig 空占位符翻译时失败 | 中 |
| 8 | InputSpec.plugin 是 str 非 Literal | 低 |

### 4.2 根因：编辑态 vs 执行态的语义分裂

| 维度 | configforge（编辑态） | pipeforge（执行态） |
|---|---|---|
| 必填性 | 全字段可空（wizard 占位符） | 关键字段必填（强校验） |
| 命名 | camelCase alias（前端友好） | snake_case（CLI 友好） |
| 类型集合 | 7 种输入 | 3 种输入 |
| 独有字段 | file_id, connection_id, query_type, tags | file |
| 处理器结构 | 单一平铺模型 | 鉴别联合嵌套 |

### 4.3 候选方案对比

| 方案 | 核心思路 | 优点 | 缺点 |
|---|---|---|---|
| A. 维持现状+修 bug | 只修 8 个 bug，保留翻译层 | 零迁移成本 | 债务不减少 |
| B. configforge 复用 pipeforge | 删除 configforge 模型，直接 import | 消除重复 | alias/必填性/类型集合冲突 |
| C. 提取 loose 基础模型 | pipeforge 新增全可空+alias 基类，两侧继承 | 单一数据源 | pipeforge 需重构 |
| D. configforge 继承 pipeforge | configforge 模型继承 pipeforge 扩展 | 减少重复 | Pydantic 继承+alias 有坑 |
| E. 契约测试 | 不合并，加 round-trip 自动化校验 | 低侵入 | 不减少重复 |
| F. 代码生成 | 从 pipeforge 模型生成 configforge 模型 | 单一数据源 | 生成器复杂 |

### 4.4 方案选择理由

**方案 B 不可行**：configforge 需要 `file_id`（上传文件引用）、`connection_id`（连接管理器 ID）、`query_type`（UI 状态），这些是 wizard 特有概念。pipeforge 的 `connection_string` 是执行时才解析的。强行合并会导致 wizard 模型被执行细节污染。

**方案 C 的关键洞察**：configforge 和 pipeforge 的差异本质是"同一个字段的两种校验强度"。`CsvInputConfig.delimiter` 在两侧都有且默认 ","——字段定义相同，只是必填性不同。提取 loose 基类（全可空+alias），pipeforge strict 模型继承并添加必填约束，是语义最清晰的方案。

**方案 E 的止血价值**：在未合并前，契约测试能自动捕获翻译层遗漏。每个插件类型构造 configforge 模型 → yaml_builder → pipeforge load → 字段 round-trip 断言。投入小，回报高，应立即做。

**CheckRule 已是成功先例**：configforge 已直接 import `pipeforge.config.models.CheckRule`，证明跨层复用可行。DatabaseOutputConfig 字段完全对齐（仅 alias 差异），应作为第二个复用目标。

### 4.5 推荐方案：三步走

#### 第一步（1天）：E 契约测试 + 修 bug

**目标**：用自动化测试锁定翻译层行为，修复已知 bug。

**执行步骤**：

1. **新建契约测试**
   - 文件：`configforge/tests/test_yaml_builder_contract.py`
   - 逻辑：对每个插件类型，构造 configforge 模型实例 → `build_yaml` → pipeforge `load_yaml_config` → 字段 round-trip 断言
   - 覆盖：csv/excel/database input + sql/python processor + csv/excel/database output
   - 验证：任何字段丢失/类型不匹配立即测试失败

2. **修复 yaml_builder bug #1**
   - 文件：`configforge/services/yaml_builder.py`
   - 修改：json/xml/parquet/api 分支抛 `ValueError`（配合限制③第一阶段），不再落入 else
   - 验证：json 输入生成 YAML 时抛友好错误

3. **修复 yaml_builder bug #2**
   - 文件：`configforge/services/yaml_builder.py`
   - 修改：database output 分支补全 `batch_size`、`create_table_if_not_exists` 字段输出
   - 验证：用户自定义 batch_size 不再静默丢失

4. **修复 yaml_builder bug #7**
   - 文件：`configforge/services/yaml_builder.py`
   - 修改：processor 翻译前检查 `proc.name` 和 `proc.plugin`，空占位符抛 `ValueError`
   - 验证：未完成的 processor 翻译时给出清晰错误

**验证标准**：
- [ ] 契约测试覆盖所有 8 个插件类型
- [ ] bug #1#2#7 修复，契约测试全过
- [ ] 现有 1000 个测试无回归

#### 第二步（3天）：C 提取 loose 基础模型

**目标**：消除字段定义重复，单一数据源。

**执行步骤**：

1. **pipeforge 新增 loose 模型模块**
   - 文件：`src/pipeforge/config/models_loose.py`
   - 设计：全字段可空 + camelCase alias（`populate_by_name=True`）
   - 包含：`LooseCsvInputConfig`、`LooseExcelInputConfig`、`LooseDbInputConfig`、`LooseSqlProcessorConfig`、`LoosePythonProcessorConfig`、`LooseCsvOutputConfig`、`LooseExcelOutputConfig`、`LooseDatabaseOutputConfig`、`LooseColumnMapping`

2. **pipeforge 现有 strict 模型继承 loose**
   - 文件：`src/pipeforge/config/models.py`
   - 修改：strict 模型继承 loose 并添加必填约束 + 校验器
   - 验证：pipeforge CLI 行为不变，现有 168 个测试全过

3. **configforge 复用 loose 模型**
   - 文件：`configforge/models/wizard.py`
   - 修改：删除自己的 InputConfig/OutputConfig/ColumnMapping，import loose 模型
   - 保留：wizard 特有字段（file_id、connection_id、query_type、tags）通过 wrapper 或 mixin 扩展
   - 验证：configforge API 行为不变，现有测试全过

4. **yaml_builder 简化**
   - 文件：`configforge/services/yaml_builder.py`
   - 修改：用 `model_dump(exclude={"file_id", "connection_id", ...})` 替代显式 dict 构造
   - 验证：生成的 YAML 与之前一致

**验证标准**：
- [ ] pipeforge 168 个测试全过（strict 模型行为不变）
- [ ] configforge 测试全过（API 行为不变）
- [ ] yaml_builder 代码量减少 50%+
- [ ] 契约测试全过

#### 第三步（长期）：完全合并

等 pipeforge 补齐 7 种输入后，评估 configforge 直接复用 strict 模型。此步骤不在本次方案范围内。

---

## 5. 限制①：前端动态表单优化方案（P2 体验提升）

### 5.1 问题详述

后端 `GET /api/plugins` 已返回 config_schema，但前端完全未消费。所有表单仍是按插件硬编码的 `v-if` 分支。新增插件需修改 8 处代码（插件类、__init__.py、config 模型、wizard 模型、yaml_builder、前端类型、前端 store、前端表单组件）。

### 5.2 核心难点：schema 表达力不足

Pydantic `model_json_schema()` 只产出 type/default/enum/required/min/max，不携带：

| 缺失信息 | 例子 | 影响 |
|---|---|---|
| widget 类型 | sql 字段需要 CodeEditor 而非 textarea | 无法区分代码编辑器 |
| 异步选项来源 | sheet 选项来自 fetchPreview | 无法表达依赖 |
| 可见性条件 | writeMode==='upsert' → 显示 primaryKeyColumns | 无法表达联动 |
| i18n label | "分隔符" vs "delimiter" | 无法国际化 |
| 跨字段依赖 | 选 connection → 加载 tables → 加载 columns | 无法表达级联 |

### 5.3 字段类型分布

| 类型 | 占比 | 可通用渲染 | Naive UI 组件 |
|---|---|---|---|
| text/number/boolean/enum | ~60% | 是 | NInput/NInputNumber/NCheckbox/NSelect |
| 代码编辑器（sql/script） | ~10% | 否 | CodeEditor (命名 widget) |
| 文件上传（file/template） | ~10% | 否 | NUpload + preview (命名 widget) |
| 连接选择器（connectionId） | ~5% | 否 | ConnectionManager (命名 widget) |
| key-value 编辑器（headers/params） | ~5% | 是 | NDynamicInput |
| 列映射（columns） | ~5% | 否 | ColumnMappingEditor (命名 widget) |
| 检查规则（checkpoints） | ~5% | 否 | CheckpointSection (命名 widget) |

**结论**：60% 可通用渲染，40% 需命名 widget。纯 schema 驱动不可行，混合方案是务实选择。

### 5.4 候选方案对比

| 方案 | 核心思路 | 优点 | 缺点 |
|---|---|---|---|
| A. 纯 schema 驱动 | Pydantic Field(json_schema_extra) 注入 x-ui-* | 单一数据源 | 后端污染 UI 元数据 |
| B. 前端 widget 覆盖表 | 前端维护 plugin → widget map | 后端纯净 | 双重维护 |
| C. 混合方案 | 通用字段按 schema 自动渲染 + 特殊字段命名 widget | 平衡 | 复杂度中等 |
| D. 代码生成 | 从 schema 生成 Vue 组件 | 自动化 | 生成器复杂 |
| E. 不做动态表单 | 保留硬编码，只做类型安全校验 | 零工作量 | 不解决核心问题 |

### 5.5 方案选择理由

**方案 A 的后端污染问题**：在 Pydantic Field 中注入 `x-ui-widget: code-editor` 会让 pipeforge（CLI 框架）沾染 UI 关注点。但如果 `json_schema_extra` 只在 configforge 侧的 loose 模型添加（见限制②方案 C），pipeforge strict 模型保持纯净，这个担忧可化解。

**方案 C 的具体设计**：

```
通用字段（schema 自动渲染）:
  string  → NInput
  integer → NInputNumber (min/max from schema)
  boolean → NCheckbox
  enum    → NSelect (options from schema)
  kv-pair → NDynamicInput

命名 widget（x-ui-widget 引用）:
  code-editor        → CodeEditor (language=sql/python)
  file-upload        → FileUploadSection
  connection-selector→ ConnectionManager
  column-mapping     → ColumnMappingEditor
  checkpoint-rules   → CheckpointSection
  filename-template  → FilenameTemplateEditor

可见性条件（x-ui-visible）:
  "writeMode === 'upsert'" → primaryKeyColumns 显示

异步选项（x-ui-options-from）:
  "fetchPreview.sheets" → sheet 选项动态加载
  "fetchTables(connectionId)" → tables 选项动态加载
```

**类型安全策略**：保留 `types/wizard.ts` 的判别联合作为类型层，动态表单在已窄化的 config 类型内渲染字段。用 `openapi-typescript` 从 `/api/plugins` 生成 schema 类型，与手写类型交叉校验。

### 5.6 推荐方案：渐进式三阶段

#### 第一阶段（2天）：基础设施

**目标**：建立动态表单渲染能力，消除前端硬编码默认值。

**执行步骤**：

1. **新建 usePluginSchema composable**
   - 文件：`configforge-web/src/composables/usePluginSchema.ts`
   - 逻辑：调用 `GET /api/plugins`，缓存结果，提供 `getSchema(plugin, type)` 方法
   - 验证：能正确获取 8 个插件的 schema

2. **新建 SchemaForm 通用组件**
   - 文件：`configforge-web/src/components/common/SchemaForm.vue`
   - 逻辑：接收 schema + modelValue，按字段类型自动渲染通用 widget
   - 支持：string/integer/number/boolean/enum/kv-pair
   - 验证：能渲染 csv input 的 delimiter/encoding/has_header 字段

3. **新建 widgetRegistry**
   - 文件：`configforge-web/src/composables/widgetRegistry.ts`
   - 逻辑：注册命名 widget，SchemaForm 通过 `x-ui-widget` 引用
   - 验证：`getWidget('code-editor')` 返回 CodeEditor 组件

4. **默认值从 schema.default 派生**
   - 修改：`wizardInputs.ts` 的 `addInput` 从 schema 读取默认值
   - 验证：新增 csv 输入源时 delimiter 默认为 schema 中的 ","

**验证标准**：
- [ ] SchemaForm 能渲染通用字段
- [ ] widgetRegistry 能注册/获取命名 widget
- [ ] 默认值从 schema 派生，无前端硬编码

#### 第二阶段（3天）：迁移简单插件

**目标**：csv/excel 插件表单改用 SchemaForm，删除硬编码 v-if 分支。

**执行步骤**：

1. **csv input 迁移**
   - 修改：`FileInputForm.vue` 删除 csv 的 v-if 分支，改用 SchemaForm
   - 验证：csv 输入源表单行为不变

2. **excel input 迁移**
   - 修改：`FileInputForm.vue` 删除 excel 的 v-if 分支
   - sheet 字段：注册为命名 widget（选项从 fetchPreview 动态加载）
   - 验证：excel 输入源表单行为不变

3. **csv/excel output 迁移**
   - 修改：`FileOutputForm.vue` 删除 v-if 分支，改用 SchemaForm
   - filename 字段：注册为命名 widget（filename-template）
   - 验证：输出配置表单行为不变

**验证标准**：
- [ ] csv/excel 表单用 SchemaForm 渲染
- [ ] FileInputForm/FileOutputForm 代码量减少 50%+
- [ ] 前端 e2e 测试全过

#### 第三阶段（5天）：迁移复杂插件

**目标**：database/processor 插件表单改用 SchemaForm + 命名 widget。

**执行步骤**：

1. **connection-selector widget**
   - 注册：ConnectionManager 作为命名 widget
   - 修改：`DatabaseForm.vue`、`DatabaseOutputForm.vue` 改用 SchemaForm
   - 验证：连接选择、测试连通行为不变

2. **code-editor widget**
   - 注册：CodeEditor 作为命名 widget
   - 修改：`SqlProcessorContent.vue`、`PythonProcessorContent.vue` 改用 SchemaForm
   - 验证：SQL/Python 编辑、模板、dry-run 行为不变

3. **column-mapping widget**
   - 注册：ColumnMappingEditor 作为命名 widget
   - 修改：`OutputConfigTab.vue` 改用 SchemaForm
   - 验证：列映射行为不变

4. **checkpoint-rules widget**
   - 注册：CheckpointSection 作为命名 widget
   - 验证：检查规则配置行为不变

**验证标准**：
- [ ] 所有插件表单用 SchemaForm + 命名 widget 渲染
- [ ] 前端 e2e 测试全过
- [ ] 新增插件只需后端注册，前端自动渲染（验证：创建临时插件，前端能渲染表单）

---

## 6. 综合优先级与实施路径

### 6.1 优先级矩阵

| 问题 | 紧急度 | 影响面 | 工作量 | 优先级 |
|---|---|---|---|---|
| ③幽灵插件 止血（B+D） | P0（用户可见崩溃） | 所有执行路径 | 1天 | 立即做 |
| ②双轨模型 契约测试+修 bug | P1（静默丢失配置） | batch_size 等 | 1天 | 立即做 |
| ③幽灵插件 reader 适配器 | P2 | 4 种输入类型 | 3-5天 | 短期做 |
| ①动态表单 基础设施 | P2 | 前端体验 | 2天 | 短期做 |
| ②双轨模型 提取 loose | P3 | 架构债 | 3天 | 中期做 |
| ①动态表单 迁移复杂插件 | P3 | 前端体验 | 5天 | 中期做 |

### 6.2 推荐实施顺序（协同设计）

```
Week 1: 止血 + 基础
  Day 1: ③B+D（UI 灰显 + 执行前校验）
       + ②E（契约测试框架）
       + 修复 ②bug#1#2#7（yaml_builder 三处）
  Day 2-3: ①基础设施（SchemaForm + widgetRegistry）
         + ③C json/xml/parquet reader 适配器开始

Week 2: 核心实现
  Day 4-5: ③C reader 适配器完成 + pipeforge config 扩展
  Day 6-7: ①迁移 csv/excel 插件到动态表单

Week 3: 深化
  Day 8-10: ②C 提取 loose 基础模型
  Day 11-13: ①迁移 database/processor 插件
  Day 14: api 输入插件实现（或延后 v2.0.0）
```

### 6.3 协同设计的关键考量

1. **③和②必须同步**：yaml_builder 的修复（②bug#1）与幽灵插件止血（③B+D）必须在同一天完成，否则用户仍会看到 AttributeError
2. **①依赖②的 loose 模型**：动态表单的 schema 来源应是 loose 模型（含 alias），而非 strict 模型。建议①基础设施在②loose 模型之后做
3. **③的 reader 适配器复用②的 loose 模型**：新增的 JsonInputConfig 等应直接定义为 loose 模型，避免重复定义

---

## 7. 风险评估与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| reader 全量读取内存溢出 | 中 | 执行崩溃 | 用 Iterator 流式 + batch size 限制 |
| Pydantic 继承 alias 冲突 | 中 | 模型加载失败 | 先做 spike 验证，CheckRule 已验证可行 |
| 前端动态表单类型安全退化 | 低 | 编译期丢失保护 | 保留判别联合 + openapi-typescript 交叉校验 |
| api 输入 SSRF 漏洞 | 高 | 安全风险 | 延后到 v2.0.0 + 加 URL 白名单 |
| 契约测试维护成本 | 低 | 测试拖慢 CI | 只在 PR 变更相关文件时运行 |
| reader 适配器性能不达标 | 低 | 大文件执行慢 | 基准测试 + 与 csv 插件对比 |
| loose 模型 alias 影响 CLI | 中 | pipeforge CLI 输出变化 | strict 模型 `model_dump(by_alias=False)` |

---

## 8. 审核清单

请审核人重点关注以下问题：

### 8.1 方案可行性

- [ ] 限制③的 B+D 止血方案是否可行？UI 灰显是否会损失过多功能？
- [ ] 限制③的 C reader 适配器方案是否比 A 全实现更优？reader 的流式原语是否确实可复用？
- [ ] 限制②的 C 提取 loose 模型方案是否比 B 直接复用更合理？Pydantic 继承是否有已知坑？
- [ ] 限制①的 C 混合方案（60% 通用 + 40% 命名 widget）是否务实？是否有更好的替代方案？

### 8.2 优先级与排期

- [ ] Week 1 的 Day 1 同时做 ③B+D + ②E + 修 bug，工作量是否合理？
- [ ] ③的 reader 适配器（3-5天）和 ①的动态表单（2周）是否应并行？
- [ ] api 输入延后 v2.0.0 是否可接受？

### 8.3 风险与缓解

- [ ] reader 全量读取的内存风险是否需更详细的基准测试计划？
- [ ] Pydantic loose 模型继承是否需先做技术 spike？
- [ ] 前端动态表单的类型安全退化是否可接受？

### 8.4 遗留问题

- [ ] api 输入的 SSRF 防护方案是否需单独设计文档？
- [ ] loose 模型是否应放在 pipeforge 还是独立包？
- [ ] 契约测试是否应纳入 CI 必须通过的门槛？

---

## 附录 A：相关文件索引

### 幽灵插件（限制③）
- 声明：`configforge/models/wizard.py`（InputSource.plugin Literal，第 84 行）
- 崩溃点：`configforge/services/yaml_builder.py`（else 分支 cfg.sheet，第 27 行）
- reader 实现：`configforge/services/{json,xml,parquet,api}_reader.py`
- pipeforge 缺失：`src/pipeforge/plugins/input/`（仅 csv/excel/database）
- pipeforge config：`src/pipeforge/config/models.py`（InputSpec.config 联合类型，第 61 行）

### 双轨模型（限制②）
- configforge 模型：`configforge/models/wizard.py`
- pipeforge 模型：`src/pipeforge/config/models.py`
- 翻译层：`configforge/services/yaml_builder.py`（95 行）
- 执行桥接：`configforge/core/pipeline.py`（_prepare_execution，第 136 行）
- 已复用先例：`configforge/models/wizard.py` 第 5 行 `from pipeforge.config.models import CheckRule`

### 动态表单（限制①）
- 后端 API：`configforge/api/plugins.py`（GET /api/plugins）
- 后端 schema：`src/pipeforge/plugins/base.py`（config_schema 方法）
- 前端硬编码表单：`configforge-web/src/components/step2/FileInputForm.vue` 等
- 前端类型：`configforge-web/src/types/wizard.ts`（判别联合）
- 前端 store：`configforge-web/src/stores/wizardInputs.ts`（addInput 硬编码默认值）
- UI 框架：Naive UI（无内置 schema 驱动表单组件）

---

## 附录 B：字段差异对照表（configforge vs pipeforge）

### 输入配置

| 字段 | configforge | pipeforge | 差异 |
|---|---|---|---|
| file | 缺失 | str \| None = None | pipeforge 独有 |
| connection_id | str="", alias=connectionId | 缺失 | configforge 独有 |
| query_type | Literal["table","sql"]="table" | 缺失 | configforge 独有 |
| has_header | True, alias=hasHeader | True, 无 alias | alias 差异 |
| tables/sql 互斥校验 | 无 | 有 | 校验差异 |

### 输出配置

| 字段 | configforge | pipeforge | 差异 |
|---|---|---|---|
| 全部字段 | 字段名一致 | 字段名一致 | — |
| alias | 全套 camelCase alias | 无 alias | alias 差异 |
| batch_size | ge=1, le=100000 | ge=1, le=100000 | 一致 |
| yaml_builder 输出 | 静默丢失 batch_size/create_table_if_not_exists | — | Bug #2 |

### 处理器配置

| 维度 | configforge | pipeforge | 差异 |
|---|---|---|---|
| 结构 | 单一 ProcessorConfig（sql/script 平铺） | ProcessorSpec + 鉴别联合 | 结构差异 |
| 空占位符 | 允许 | 不允许 | 校验语义差异 |

---

*本文档基于 T-5E-05 完成后的代码状态（commit c68faf6）编写，全量测试 1000 passed, 31 skipped。*
