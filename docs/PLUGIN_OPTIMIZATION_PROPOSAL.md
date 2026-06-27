# 插件系统优化技术方案

| 项目 | 内容 |
|---|---|
| 文档版本 | v2.0 |
| 创建日期 | 2026-06-27 |
| 修订日期 | 2026-06-27（根据审核报告 `PLUGIN_PROPOSAL_REVIEW.md` 修订） |
| 状态 | 审核通过（有条件），可进入实施 |
| 审核报告 | `docs/PLUGIN_PROPOSAL_REVIEW.md`（v1.0 审核结论：有条件通过） |
| 关联任务 | T-5E-05 已知限制后续优化 |
| 前置条件 | T-5E-05 本地插件系统已完成（commit c68faf6） |

**v2.0 修订摘要**（响应审核报告）：
- 修正 2 项事实错误：①ijson 可选依赖处理策略未明确 ②`_USER_ERRORS` 已含 ValueError 的重复描述
- 补充 5 项内容：①api_reader.py 现状 ②loose 模型技术 spike 前置 ③SchemaForm v-model 数据流设计 ④工期上调（简单插件 3→4 天，复杂插件 5→7-8 天）⑤实施顺序由并行改为串行
- 新增 4 项风险评估
- 新增 6.4 节「Reader 驱动模型生成」轻量化备选方案

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

**4 个幽灵输入源的 reader 现状**（`configforge/services/`，响应审核报告 4.2）：

| Reader | 文件 | 现有能力 | 流式原语 | 全量读取接口 |
|---|---|---|---|---|
| json_reader | `json_reader.py` | `read_json_info` 返回 columns+sample_rows | `ijson.items()` 流式（**ijson 可选，未装时 fallback 到 `json.loads` 全量加载**） | 无 |
| xml_reader | `xml_reader.py` | `read_xml_info` 返回 columns+sample_rows | `ET.iterparse(events=("end",))` 流式 | 无 |
| parquet_reader | `parquet_reader.py` | `read_parquet_info` 返回 columns+sample_rows | `pf.iter_batches(batch_size=100)` 流式 | 无 |
| api_reader | `api_reader.py` | `read_api_info` 返回 columns+sample_rows | httpx 分页（offset/none，max_pages=10） | 无 |

**关键观察**：
- 4 个 reader 都只提供「轻量预览」（max_sample_rows=10），没有「全量读取」接口
- json/xml/parquet 的流式原语天然适合全量加载，只需新增 `iter_xxx_rows() -> Iterator[tuple]`
- **api_reader 已实现分页逻辑**（`pagination` 参数支持 none/offset，`max_pages=10`，`page_size=100`），但涉及网络请求，全量读取的复杂度远高于文件读取（详见 3.4 第三阶段）
- **ijson 依赖问题**：`pyproject.toml` 的 `dependencies` 未声明 ijson，`json_reader.py` 用 `try/except ImportError` 处理。无 ijson 时 `read_json_info` fallback 到 `json.loads`（全量加载到内存），违背流式设计意图。本方案第二阶段将明确处理此依赖（见 3.4 第二阶段步骤 1）

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
   - **注（响应审核报告 2.3）**：`ValueError` 已在 `_USER_ERRORS` 中（`execution_service.py:33`：`_USER_ERRORS = (ValueError, SyntaxError, TimeoutError, PipelineTimeoutError)`），无需重复添加，直接抛出即可返回 422
   - 验证：执行含 json 输入的 pipeline 返回 422 + 友好错误信息

3. **前端 InputSourceHeader.vue**：对已存在的 json/xml/parquet/api 输入源卡片头部加 warning tag "仅预览"
   - 文件：`configforge-web/src/components/step2/InputSourceHeader.vue`
   - 新增 `isPreviewOnly` computed（响应审核报告 3.2）：基于 `props.plugin` 是否在 `["json", "xml", "parquet", "api"]` 中判断，区分「已存在的幽灵输入源」和「正常输入源」
   - 验证：已有幽灵类型输入源显示 warning 标签，正常类型不显示

**验证标准**：
- [ ] 新建输入源时 json/xml/parquet/api 卡片不可选
- [ ] 已存在的幽灵类型输入源显示"仅预览"标签
- [ ] 执行含幽灵类型的 pipeline 返回 422 + 友好错误信息
- [ ] 现有 1000 个测试无回归

#### 第二阶段（4-5天）：C 实现 reader 适配器

**目标**：json/xml/parquet 输入源可完整执行 pipeline。

**执行步骤**：

1. **为 reader 新增全量读取接口 + ijson 依赖处理**
   - 文件：`configforge/services/json_reader.py`、`xml_reader.py`、`parquet_reader.py`
   - 新增函数：`iter_json_rows(file_content, flatten_separator) -> Iterator[tuple]`、`iter_xml_rows(...)`、`iter_parquet_rows(...)`
   - 返回：列名列表 + 行迭代器（`Iterator[tuple]`）
   - **ijson 依赖处理（响应审核报告 3.2 + 7）**：
     - 方案 A（推荐）：将 ijson 从可选依赖提升为必需依赖，在 `pyproject.toml` 的 `dependencies` 中添加 `ijson>=3.2`
     - 方案 B（备选）：`iter_json_rows` 在 `_HAS_IJSON=False` 时抛 `RuntimeError("ijson 未安装，无法流式解析大 JSON 文件，请 pip install ijson")`，拒绝退化为全量加载
     - **本方案采用 A**，理由：ijson 是纯 Python 库无 C 依赖，安装成本低；流式解析是 reader 适配器的核心价值，不应有降级路径
   - 验证：单元测试验证全量读取正确性；无 ijson 环境下 `iter_json_rows` 行为符合方案 A 或 B 的预期

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
   - **注**：也可采用 6.4 节的「Reader 驱动模型生成」轻量化备选方案，跳过专属 config 类型定义

4. **yaml_builder 补全分支**
   - 文件：`configforge/services/yaml_builder.py`
   - 修改：if/elif 补全 json/xml/parquet 分支，不再落入 else 当 excel
   - 验证：生成含 json 输入的 YAML 能被 pipeforge 正确加载

5. **_prepare_execution 文件后缀修复**（响应审核报告 4.3，已验证存在）
   - 文件：`configforge/core/pipeline.py` 第 252 行
   - 现状（已核查）：`dst_name = inp.file_id + (".xlsx" if inp.plugin == "excel" else ".csv")` — 非 xlsx/csv 文件被强制改名为 .csv
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

#### 第一步（1.5天）：E 契约测试 + 修 bug

**目标**：用自动化测试锁定翻译层行为，修复已知 bug。

**执行步骤**：

1. **新建契约测试**
   - 文件：`configforge/tests/test_yaml_builder_contract.py`
   - 逻辑：对每个插件类型，构造 configforge 模型实例 → `build_yaml` → pipeforge `load_yaml_config` → 字段 round-trip 断言
   - 覆盖：csv/excel/database input + sql/python processor + csv/excel/database output
   - **alias 差异测试（响应审核报告 3.3 补充建议）**：configforge camelCase alias 与 pipeforge snake_case 的转换是关键测试点。测试用例需覆盖：
     - configforge 用 alias 输入（`{"hasHeader": true}`）→ yaml_builder → pipeforge 用 snake_case 读取（`has_header=True`）
     - 反向：pipeforge `model_dump(by_alias=False)` → configforge 用 alias 加载
   - 验证：任何字段丢失/类型不匹配/alias 转换错误立即测试失败

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

#### 第二步（3.5天：0.5 天 spike + 3 天实施）：C 提取 loose 基础模型

**目标**：消除字段定义重复，单一数据源。

**执行步骤**：

0. **技术 spike（0.5 天，前置，响应审核报告 3.3 + 8.3）**
   - 目标：验证 Pydantic 继承 + alias 的行为符合预期，降低 Phase 2 实施风险
   - spike 对象：`DatabaseOutputConfig`（字段完全对齐，仅 alias 差异，是最佳验证目标）
   - 验证点：
     - `populate_by_name=True` + 继承链下，alias 解析是否正确
     - strict 子类添加必填约束时，loose 父类的可空字段是否被正确覆盖
     - `model_dump(by_alias=True)` 和 `model_dump(by_alias=False)` 在继承链下的输出
     - `model_json_schema()` 在继承链下是否合并父子的 `json_schema_extra`
   - 产出：spike 报告（pass/fail + 发现的坑），若 fail 则回退到方案 A（维持现状+修 bug）或采用 6.4 备选方案
   - 验证：spike 通过后才进入步骤 1

1. **pipeforge 新增 loose 模型模块**
   - 文件：`src/pipeforge/config/models_loose.py`（**放置位置决策，响应审核报告 8.4**：放在 pipeforge 而非独立包，理由：pipeforge 是数据的 single source of truth，configforge 已有 `from pipeforge.config.models import CheckRule` 的先例）
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
   - **SchemaForm v-model 数据流设计（响应审核报告 3.4 补充建议）**：
     - **问题**：config 是嵌套的鉴别联合类型（`InputSource.config` 是 `CsvInputConfig | ExcelInputConfig | ...`），SchemaForm 如何与父组件的 `input.config` 保持双向绑定？
     - **设计**：
       - SchemaForm 接收 `modelValue: Record<string, unknown>` + `schema: JsonSchema`，emit `update:modelValue`
       - 父组件（如 `FileInputForm.vue`）负责鉴别联合的窄化：根据 `input.plugin` 选择对应 schema，将 `input.config` 作为 modelValue 传入
       - SchemaForm 内部按 schema 字段路径（如 `delimiter`、`sheet`）emit 局部更新 `{ ...modelValue, [field]: newValue }`
       - 父组件用窄化后的类型断言更新 `input.config`，保留 `wizard.ts` 判别联合的类型安全
     - **PoC 验证**：第一阶段先用 csv（最简单配置类型）做 PoC，确认 v-model 双向绑定在鉴别联合下工作正常，再进入第二阶段
   - 验证：能渲染 csv input 的 delimiter/encoding/has_header 字段

3. **新建 widgetRegistry**
   - 文件：`configforge-web/src/composables/widgetRegistry.ts`
   - 逻辑：注册命名 widget，SchemaForm 通过 `x-ui-widget` 引用
   - 验证：`getWidget('code-editor')` 返回 CodeEditor 组件

4. **默认值从 schema.default 派生**
   - 修改：`wizardInputs.ts` 的 `addInput` 从 schema 读取默认值
   - 验证：新增 csv 输入源时 delimiter 默认为 schema 中的 ","

5. **异步选项支持（响应审核报告 3.4，从 Phase 2 前移到 Phase 1）**
   - 理由：excel 的 sheet 字段选项来自 `fetchPreview`，若 Phase 1 不支持异步选项，Phase 2 迁移 excel 时会被阻塞
   - 设计：SchemaForm 支持 `x-ui-options-from` 扩展字段，引用父组件提供的异步 loader（如 `fetchPreview.sheets`、`fetchTables(connectionId)`）
   - widgetRegistry 新增 `registerAsyncOptionsLoader(name, loader)` 注册异步选项源
   - 验证：SchemaForm 能渲染一个 mock 的异步选项字段（如从 setTimeout 返回选项列表）

**验证标准**：
- [ ] SchemaForm 能渲染通用字段
- [ ] SchemaForm v-model 在鉴别联合下双向绑定工作正常（csv PoC）
- [ ] widgetRegistry 能注册/获取命名 widget
- [ ] 异步选项支持可用（`x-ui-options-from`）
- [ ] 默认值从 schema 派生，无前端硬编码

#### 第二阶段（4天）：迁移简单插件

**目标**：csv/excel 插件表单改用 SchemaForm，删除硬编码 v-if 分支。

**工期上调说明（响应审核报告 3.4）**：原估 3 天，审核建议 4 天。上调理由：excel sheet 字段的异步选项加载需在第一阶段已支持，但迁移时需对接真实的 `fetchPreview` API，含错误处理和 loading 状态。

**执行步骤**：

1. **csv input 迁移**
   - 修改：`FileInputForm.vue` 删除 csv 的 v-if 分支，改用 SchemaForm
   - 验证：csv 输入源表单行为不变

2. **excel input 迁移**
   - 修改：`FileInputForm.vue` 删除 excel 的 v-if 分支
   - sheet 字段：注册为命名 widget，通过 `x-ui-options-from: "fetchPreview.sheets"` 引用第一阶段实现的异步选项加载器
   - 验证：excel 输入源表单行为不变，sheet 选项从 fetchPreview 动态加载

3. **csv/excel output 迁移**
   - 修改：`FileOutputForm.vue` 删除 v-if 分支，改用 SchemaForm
   - filename 字段：注册为命名 widget（filename-template）
   - 验证：输出配置表单行为不变

**验证标准**：
- [ ] csv/excel 表单用 SchemaForm 渲染
- [ ] FileInputForm/FileOutputForm 代码量减少 50%+
- [ ] 前端 e2e 测试全过

#### 第三阶段（7-8天）：迁移复杂插件

**目标**：database/processor 插件表单改用 SchemaForm + 命名 widget。

**工期上调说明（响应审核报告 3.4）**：原估 5 天，审核建议 7-8 天。上调理由：4 个复杂 widget（ConnectionManager/CodeEditor/ColumnMappingEditor/CheckpointSection）都是成熟组件，迁移到 widget 注册模式需重构其 props 接口以适配 SchemaForm 的命名 widget 协议。

**执行步骤**：

1. **connection-selector widget（2 天）**
   - 注册：ConnectionManager 作为命名 widget
   - 修改：`DatabaseForm.vue`、`DatabaseOutputForm.vue` 改用 SchemaForm
   - 复杂度：连接选择 → 测试连通 → 加载 tables → 加载 columns 的级联，需通过 `x-ui-options-from` + `x-ui-visible` 表达级联依赖
   - 验证：连接选择、测试连通行为不变

2. **code-editor widget（1.5 天）**
   - 注册：CodeEditor 作为命名 widget
   - 修改：`SqlProcessorContent.vue`、`PythonProcessorContent.vue` 改用 SchemaForm
   - 复杂度：SQL 模板变量、dry-run 集成需通过 `x-ui-actions` 扩展字段表达
   - 验证：SQL/Python 编辑、模板、dry-run 行为不变

3. **column-mapping widget（2 天）**
   - 注册：ColumnMappingEditor 作为命名 widget
   - 修改：`OutputConfigTab.vue` 改用 SchemaForm
   - 复杂度：source/target 配对、类型映射需自定义 widget 协议
   - 验证：列映射行为不变

4. **checkpoint-rules widget（1.5 天）**
   - 注册：CheckpointSection 作为命名 widget
   - 复杂度：动态规则增删、AND/OR 逻辑需自定义 widget 协议
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
| ②双轨模型 契约测试+修 bug | P1（静默丢失配置） | batch_size 等 | 1.5天 | 立即做 |
| ③幽灵插件 reader 适配器 | P2 | 4 种输入类型 | 4-5天 | 短期做 |
| ①动态表单 基础设施 | P2 | 前端体验 | 2天 | 短期做 |
| ②双轨模型 提取 loose（含 spike） | P3 | 架构债 | 3.5天 | 中期做 |
| ①动态表单 迁移简单插件 | P3 | 前端体验 | 4天 | 中期做 |
| ①动态表单 迁移复杂插件 | P3 | 前端体验 | 7-8天 | 中期做 |
| **合计** | — | — | **23-25天** | — |

**工期调整说明（响应审核报告第五节）**：v1.0 估算 18-22 天，v2.0 上调至 23-25 天（+15-20%）。主要上调项：①简单插件 3→4 天，①复杂插件 5→7-8 天，②契约测试 1→1.5 天，②loose 模型新增 0.5 天 spike。

### 6.2 推荐实施顺序（串行，响应审核报告 6.2）

**调整理由（响应审核报告）**：v1.0 的 Week 1 同时做止血 + 契约测试 + 动态表单基础设施，3 个工作流并行对单人开发上下文切换成本高。v2.0 改为串行，且动态表单在 loose 模型就绪后开发可避免返工。

```
Week 1: 止血 + 契约测试（P0/P1 集中精力）
  Day 1:   ③B+D（UI 灰显 + 执行前校验）— P0 止血优先
  Day 2-3: ②E 契约测试 + 修 bug #1#2#7（含 alias 差异测试）

Week 2: reader 适配器 + loose 模型 spike
  Day 4:   ②C loose 模型技术 spike（0.5 天）+ ③C reader 全量读取接口开始
  Day 5-7: ③C reader 适配器完成（含 ijson 依赖提升）+ pipeforge config 扩展 + yaml_builder 补全

Week 3: loose 模型实施 + 动态表单基础设施
  Day 8-10: ②C 提取 loose 基础模型（spike 通过后实施）
  Day 11-12: ①动态表单基础设施（SchemaForm + widgetRegistry + 异步选项支持）

Week 4: 动态表单迁移
  Day 13-16: ①迁移 csv/excel 简单插件（4 天）
  Day 17-23: ①迁移 database/processor 复杂插件（7 天）
  Day 24: api 输入插件实现（或延后 v2.0.0）
```

### 6.3 协同设计的关键考量

1. **③和②必须同步**：yaml_builder 的修复（②bug#1）与幽灵插件止血（③B+D）必须在 Week 1 完成，否则用户仍会看到 AttributeError
2. **①依赖②的 loose 模型，但可过渡**（响应审核报告 4.1）：
   - **问题**：v1.0 在 Week 1 Day 2-3 安排动态表单基础设施，但 loose 模型在 Week 3 才完成。SchemaForm 的 schema 来源基于什么？
   - **过渡策略**：
     - Week 3 Day 11-12 的 SchemaForm 使用当前 `GET /api/plugins` 返回的 strict 模型 schema 进行开发
     - Week 3 Day 8-10 loose 模型完成后，SchemaForm 切换 schema 来源（应该是无感切换，因为字段定义相同，仅 alias 差异）
     - 风险：strict 模型 schema 的字段名是 snake_case，loose 模型是 camelCase alias。若 SchemaForm 用字段名作为 modelValue 的 key，切换时需统一为 alias
     - 缓解：SchemaForm 第一阶段就用 `model_dump(by_alias=True)` 的输出作为 modelValue，确保字段名一致
3. **③的 reader 适配器复用②的 loose 模型**：新增的 JsonInputConfig 等应直接定义为 loose 模型，避免重复定义
4. **契约测试纳入 CI 门槛**（响应审核报告 8.4）：契约测试的目标是「翻译层任何修改立即发现字段丢失」，应在 CI 的 test job 中必须通过

### 6.4 备选方案：Reader 驱动模型生成（响应审核报告 6.1）

审核报告提出了一个未在 v1.0 候选列表中的方案，值得作为 ③Phase 2 的轻量化备选：

**核心思路**：跳过手动定义 JsonInputConfig/XmlInputConfig/ParquetInputConfig，利用 reader 已有的列信息（`columns: list[ColumnInfo]`）和样本行（`sample_rows`）。

**具体做法**：
1. **ReaderBackedInputPlugin 直接接收原始文件 + 少量配置参数**：无需新增复杂的 Pydantic 模型
2. **yaml_builder 使用通用的 `file` 输入类型**：pipeforge 的 `InputSpec` 已支持 `file` 字段，json/xml/parquet 通过 file 路径读取，无需新增 config 类型
3. **reader 在运行时推断列信息**：json/xml/parquet 的配置字段实际上非常少（json 只有 `flattenSeparator`，xml 只有 `rowElement`，parquet 无特殊字段），大部分配置信息由 reader 从文件推断

**优点**：
- 减少 50% 的模型定义工作量
- 避免 pipeforge config 联合类型膨胀（不新增 JsonInputConfig 等）
- yaml_builder 改动更小（统一走 file 路径）

**缺点**：
- 类型安全性略降（json/xml/parquet 配置没有专属类型校验）
- reader 适配器需自行管理配置参数解析（不能依赖 Pydantic 校验）

**适用场景**：若 ②loose 模型提取的 spike 失败（Pydantic 继承+alias 有不可解的坑），可退回此方案作为 ③Phase 2 的实现路径。

**决策点**：在 ③Phase 2 实施时，根据 ②loose 模型 spike 的结果决定：
- spike 通过 → 采用 v2.0 主方案（新增 loose JsonInputConfig 等）
- spike 失败 → 采用 6.4 备选方案（Reader 驱动模型生成）

---

## 7. 风险评估与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| reader 全量读取内存溢出 | 中 | 执行崩溃 | 用 Iterator 流式 + batch size 限制；100MB JSON 文件基准测试 |
| Pydantic 继承 alias 冲突 | 中 | 模型加载失败 | **0.5 天技术 spike 前置验证**（响应审核报告），CheckRule 已验证可行；spike 失败则退回 6.4 备选方案 |
| 前端动态表单类型安全退化 | 低 | 编译期丢失保护 | 保留判别联合 + openapi-typescript 交叉校验 |
| api 输入 SSRF 漏洞 | 高 | 安全风险 | 延后到 v2.0.0 + 加 URL 白名单 + 独立安全设计文档 |
| 契约测试维护成本 | 低 | 测试拖慢 CI | 只在 PR 变更相关文件时运行；纳入 CI 必须通过门槛 |
| reader 适配器性能不达标 | 低 | 大文件执行慢 | 基准测试 + 与 csv 插件对比 |
| loose 模型 alias 影响 CLI | 中 | pipeforge CLI 输出变化 | strict 模型 `model_dump(by_alias=False)` |
| **ijson 未安装导致 iter_json_rows 退化为全量加载**（响应审核报告 7） | 中 | 大文件 OOM | **将 ijson 提升为必需依赖**（`pyproject.toml` dependencies 添加 `ijson>=3.2`），或 `iter_json_rows` 在无 ijson 时抛 `RuntimeError` 拒绝降级 |
| **SchemaForm v-model 嵌套鉴别联合绑定失效**（响应审核报告 7） | 中 | 表单数据丢失 | Phase 1 先用 csv（最简单配置类型）做 PoC 验证；PoC 失败则评估是否退回硬编码表单 |
| **yaml_builder 简化（model_dump(exclude=...)）遗漏字段**（响应审核报告 7） | 中 | 配置静默丢失 | 依赖 Phase 1 的契约测试兜底；契约测试覆盖所有 8 个插件类型的 round-trip |
| **`_USER_ERRORS` 重复添加 ValueError**（响应审核报告 7，已修正） | 极低 | 无影响 | v2.0 已删除「将 ValueError 纳入 _USER_ERRORS」描述，代码现状已含 ValueError |

---

## 8. 审核清单

> v2.0 注：本节为 v1.0 审核清单，审核报告（`PLUGIN_PROPOSAL_REVIEW.md`）已全部回答。以下保留原问题并标注审核结论。

### 8.1 方案可行性

- [x] 限制③的 B+D 止血方案是否可行？UI 灰显是否会损失过多功能？
  **审核结论**：✅ 可行。UI 灰显会暂时损失 json/xml/parquet/api 的预览能力（约 5% 用户场景），属于可接受的暂时性功能降级。
- [x] 限制③的 C reader 适配器方案是否比 A 全实现更优？reader 的流式原语是否确实可复用？
  **审核结论**：✅ 是。通用 ReaderBackedPlugin 避免 4 个重复插件类，工作量少 50%+。
- [x] 限制②的 C 提取 loose 模型方案是否比 B 直接复用更合理？Pydantic 继承是否有已知坑？
  **审核结论**：✅ 是。但需 0.5 天技术 spike 验证（v2.0 已纳入 Phase 2 步骤 0）。
- [x] 限制①的 C 混合方案（60% 通用 + 40% 命名 widget）是否务实？是否有更好的替代方案？
  **审核结论**：✅ 务实。60/40 比例基于实际字段类型统计，命名 widget 模式已被业界验证。

### 8.2 优先级与排期

- [x] Week 1 的 Day 1 同时做 ③B+D + ②E + 修 bug，工作量是否合理？
  **审核结论**：⚠️ 偏紧。v2.0 已调整为 Day 1 集中做 ③B+D，Day 2-3 做 ②E + 修 bug（串行）。
- [x] ③的 reader 适配器（3-5天）和 ①的动态表单（2周）是否应并行？
  **审核结论**：单人开发建议串行（v2.0 已调整为 4 周串行），双人可并行。
- [x] api 输入延后 v2.0.0 是否可接受？
  **审核结论**：✅ 可接受。api 输入的复杂度（分页/认证/SSRF/超时）应单独评估。

### 8.3 风险与缓解

- [x] reader 全量读取的内存风险是否需更详细的基准测试计划？
  **审核结论**：✅ 已有流式支持，内存风险可控。建议对 100MB JSON 文件做一次基准测试（v2.0 已纳入风险缓解措施）。
- [x] Pydantic loose 模型继承是否需先做技术 spike？
  **审核结论**：✅ 必须做。v2.0 已纳入 Phase 2 步骤 0（0.5 天 spike，用 DatabaseOutputConfig 验证）。
- [x] 前端动态表单的类型安全退化是否可接受？
  **审核结论**：✅ 可接受。保留 `wizard.ts` 判别联合 + `openapi-typescript` 生成的 schema 类型做交叉校验。

### 8.4 遗留问题

- [x] api 输入的 SSRF 防护方案是否需单独设计文档？
  **审核结论**：✅ 是。建议在 v2.0.0 前编写独立的 `API_INPUT_SECURITY.md`。
- [x] loose 模型是否应放在 pipeforge 还是独立包？
  **审核结论**：建议放在 `src/pipeforge/config/models_loose.py`，pipeforge 是 single source of truth。v2.0 已采纳（4.5 第二步步骤 1）。
- [x] 契约测试是否应纳入 CI 必须通过的门槛？
  **审核结论**：✅ 是。v2.0 已纳入 6.3 协同设计关键考量第 4 条。

---

## 附录 A：相关文件索引

### 幽灵插件（限制③）
- 声明：`configforge/models/wizard.py`（InputSource.plugin Literal，第 84 行）
- 崩溃点：`configforge/services/yaml_builder.py`（else 分支 cfg.sheet，第 27 行）
- reader 实现：`configforge/services/{json,xml,parquet,api}_reader.py`
  - **api_reader.py 现状（响应审核报告 4.2）**：已有 `read_api_info(url, method, headers, params, body, data_path, pagination, page_size, max_pages, max_sample_rows)`，支持 offset/none 分页、max_pages=10、page_size=100。涉及网络请求，全量读取复杂度远高于文件读取，延后到 v2.0.0
- pipeforge 缺失：`src/pipeforge/plugins/input/`（仅 csv/excel/database）
- pipeforge config：`src/pipeforge/config/models.py`（InputSpec.config 联合类型，第 61 行）
- 文件后缀强制改名（响应审核报告 4.3，已验证）：`configforge/core/pipeline.py` 第 252 行 `dst_name = inp.file_id + (".xlsx" if inp.plugin == "excel" else ".csv")`
- ijson 可选依赖：`configforge/services/json_reader.py` 第 3-8 行 `try/except ImportError`；`pyproject.toml` dependencies 未声明 ijson

### 双轨模型（限制②）
- configforge 模型：`configforge/models/wizard.py`
- pipeforge 模型：`src/pipeforge/config/models.py`
- 翻译层：`configforge/services/yaml_builder.py`（95 行）
- 执行桥接：`configforge/core/pipeline.py`（_prepare_execution，第 136 行）
- 已复用先例：`configforge/models/wizard.py` 第 5 行 `from pipeforge.config.models import CheckRule`
- `_USER_ERRORS` 现状（响应审核报告 2.3）：`configforge/services/execution_service.py` 第 33 行 `_USER_ERRORS = (ValueError, SyntaxError, TimeoutError, PipelineTimeoutError)` — 已含 ValueError
- loose 模型目标位置（v2.0 决策，响应审核报告 8.4）：`src/pipeforge/config/models_loose.py`

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
*v2.0 根据 `PLUGIN_PROPOSAL_REVIEW.md` 审核报告修订，所有审核意见已通过代码库事实核查验证。*
