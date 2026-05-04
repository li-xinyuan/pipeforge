# PipeForge 设计文档 v0.4 Review

> 审核文档: DESIGN_v4.md (文档 v0.4 / 产品 v0.1)  
> 对比基线: REVIEW_v3.md (v0.3 审核)  
> 审核日期: 2026-05-03

---

## 一、v0.3 问题修复情况：逐项核验

### P1 问题

| # | v0.3 问题 | v0.4 修复位置 | 修复内容 | 结果 |
|---|----------|-------------|---------|------|
| P1-1 | 两阶段写入丢失非表头模板属性 | §6.1 步骤3/7、§4.5 | 新增「读取并恢复 sheet 级属性」：`column_dimensions`（列宽）、`freeze_panes`（冻结窗格）；§4.5 模板规范分为三档：**会保留**（列宽/冻结窗格）、**不保证保留**（打印设置/标签颜色/缩放）、**不支持**（合并单元格/数据验证） | ✅ 已解决 |
| P1-2 | `param_key` → `config.file` 注入机制未描述 | §3.3 | 新增「参数注入机制」完整章节：明确 YAML 中 `config` 不含 `file` 字段；描述引擎四步处理（加载→取值→注入→调用）；提供方案 A/B 对比；**选定方案 B**（`file: str \| None = None`，引擎校验后注入） | ✅ 已解决 |
| P1-3 | `read_excel_rows` 行为未定义 | §3.3 | 新增「数据读取规范」：**首行**返回列名列表（引擎据此 CREATE TABLE），**第 2 行起**返回数据元组（INSERT 写入）；首行为空则报配置错误；决策 #21 | ✅ 已解决 |

### P2 问题

| # | v0.3 问题 | v0.4 修复位置 | 修复内容 | 结果 |
|---|----------|-------------|---------|------|
| P2-1 | `{{date:YYYYMM}}` 非 strftime | §4.1、§4.3 | 改为标准 Python strftime 格式：`{{date:%Y%m}}` → `202405`；默认 `{{date:%Y%m%d}}` | ✅ 已解决 |
| P2-2 | 输出目录路径未指定 | §4.1、§4.2、§4.3 | 新增 `output_dir` 字段，默认 `./output/`，不存在时引擎自动创建；§4.3 明确「完整路径 = `{output_dir}/{filename}`」 | ✅ 已解决 |
| P2-3 | SQL 无变量替换限制未标注 | §9 | Processor 行加注「**SQL 中不支持变量替换，所有条件需硬编码**」 | ✅ 已解决 |
| P2-4 | `tables_created` 数据来源 | §3.3、决策 #20 | 注释明确「执行 SQL 后从 `sqlite_master` 查询得到」；§11 步骤 7 同步 | ✅ 已解决 |
| P2-5 | PluginFactory 流程未描述 | §3.2、§3.3、决策 #19 | 工厂模式描述从「PluginFactory 创建」改为「引擎通过 PluginRegistry 获取→实例化→注入属性」；新增「插件实例化流程」节给出伪代码；**决策 #19：明确不使用独立 PluginFactory 类** | ✅ 已解决 |
| P2-6 | output_tables 声明错误路径缺失 | §3.5 | 输出错误新增「source_table 在数据库中不存在（可能因为 processor SQL 实际创建的表名与 output_tables 声明不一致）」 | ✅ 已解决 |

### P3 问题

| # | v0.3 问题 | v0.4 修复位置 | 修复内容 | 结果 |
|---|----------|-------------|---------|------|
| P3-1 | 「打开新 workbook」措辞 | §6.1 | 改为「创建新 workbook」；具体步骤 4 为「`Workbook(write_only=True)` 创建新文件」 | ✅ 已解决 |
| P3-2 | `params` 类型标注不一致 | §3.4 | `execute(params: dict)` → `execute(params: dict[str, str])`，与 §3.3 一致 | ✅ 已解决 |

### 结论

**v0.3 复审中提出的 11 个问题（3 P1 + 6 P2 + 2 P3）在 v0.4 中全部得到解决。** 尤其值得肯定的是 P1-1（列宽/冻结窗格保留）和 P1-2（参数注入机制）两个问题，解决得非常具体，已经到了可以对着写代码的程度。

---

## 二、v0.4 新发现的问题

### P1 — 重要问题

#### P1-1: §4.6 错误阶段描述与 §3.5 矛盾（自相矛盾）

§4.6 表名冲突检测末尾注释：

> 如果声明与实际 SQL 不符，会在运行时 **SQL 执行阶段报错**。

但 §3.5 刚刚针对此问题做了修正——这种情况属于 **输出错误**（「source_table 在数据库中不存在」），不是「SQL 执行阶段」错误。原因很清楚：如果声明了 `output_tables: [report_data]` 但实际 SQL 创建的是 `report`，SQLite **不会报错**（SQL 语法正确，表创建成功），真正的错误发生在 Output 阶段尝试读取不存在的 `report_data` 表时。

这是 v0.4 自己的修复（§3.5）和 §4.6 残留旧描述之间的内部矛盾。

**建议**：§4.6 注释改为：「如果声明与实际 SQL 不符，会在运行时 Output 阶段报错（source_table 在数据库中不存在）」。

---

#### P1-2: `read_excel_rows` 双类型返回值与 Input 插件代码矛盾（§3.3）

§3.3「数据读取规范」定义：

> - 第一次迭代（首行）：返回列名列表 `["姓名", "部门", ...]`
> - 后续迭代（第 2 行起）：返回数据元组 `("张三", "技术部", ...)`

但同一节中 Input 插件 execute 的代码是：

```python
def execute(self, context: Context, config: ExcelInputConfig) -> None:
    with context.db.transaction():
        for row in read_excel_rows(config.file, config.sheet):
            context.db.insert_row(self.table_name, row)
```

如果把这段代码和「数据读取规范」放在一起理解，结果是：**首行「列名列表」也会被 `insert_row` 当作数据插入 SQLite**——这就把表头当成了数据行。这与「引擎据此 CREATE TABLE」的说法矛盾。

要么：
- `read_excel_rows` 的首次迭代由引擎单独消费（创建表），插件只消费后续迭代（此时代码应调整）
- 要么代码中的 `execute` 需要显式处理首行（跳过或用于建表）

两种方案都没在当前代码片段中体现。

**建议**：
- 将 `read_excel_rows` 设计为返回 `(columns: list[str], rows: Iterator[tuple])` 的元组，由引擎和插件分别消费
- 或在 Input 插件的 execute 伪代码中体现建表逻辑（首行判断 + CREATE TABLE + 后续 INSERT）

---

### P2 — 建议优化

#### P2-1: 参数注入「方案 B」默认值描述自相矛盾（§3.3）

§3.3「参数注入机制」中方案 B 出现了两个不同的默认值：

> 方案 B（可选字段）：Pydantic 模型中 `file: str = ""`

> MVP 采用 **方案 B**：`file` 字段默认为空字符串，标记为可选（`str | None = None`）

`str = ""` 和 `str | None = None` 是两种不同的类型定义：
- `str = ""`：类型是 `str`，默认值是空字符串（不可为 None）
- `str | None = None`：类型是 `str | None`（Optional），默认值是 None

虽然不影响理解，但需要在最终版中统一。

**建议**：统一为 `file: str | None = None`（与「标记为可选」语义一致，且引擎注入前为 None 比空字符串更明确表示「尚未注入」）。

---

#### P2-2: openpyxl `read_only=True` 能否读取样式和列宽需验证（§6.1）

§6.1 两阶段写入在步骤 1 中使用 `load_workbook(filename, read_only=True)`，然后步骤 2 读取表头单元格的 `font`/`fill`/`border`/`alignment`/`number_format`，步骤 3 读取 `column_dimensions`。

**技术风险**：openpyxl 的 `read_only=True` 模式是专门为跳过样式解析而设计的，目的是加速大数据文件的读取。在这个模式下：
- 单元格的 `font`/`fill`/`border`/`alignment`/`number_format` **可能**返回默认对象而非模板中实际设置的样式
- `column_dimensions` **可能**不可用

如果 read_only 模式下无法获取真实样式，整个两阶段写入方案需要调整为「放弃样式保留」或「使用普通模式读取（牺牲内存/速度）」。

**建议**：在实现前用一个真实模板做验证测试，确认 read_only 模式下能否正确获取样式和列宽。如果不行，备选方案可以是「先用普通模式读模板（MVP 数据规模下内存可控），再用 write_only 写输出」。

---

#### P2-3: `required_params()` 返回的 `list[dict]` 结构未定义（§3.4）

§3.4 类图中 CLI 层和引擎层都有：

```
required_params() → list[dict]
```

但从 v0.3 到 v0.4，`dict` 的结构一直没有被定义。这是一个 CLI 和引擎之间的**接口契约**，缺失这个定义意味着前后端对接时需要额外沟通。

例如，list 中的每个 dict 应该包含什么？
```python
# 推测的结构（未确认）
{"key": "person_file", "label": "人员明细", "description": "请上传人员明细Excel文件"}
```

**建议**：在 §3.4 中明确 dict 结构，或给出 `RequiredParam` Pydantic model 定义。

---

#### P2-4: §3.3「插件实例化流程」伪代码 comment 与代码不一致

```python
plugin.label = config.name  # 人类可读名称（仅 InputPlugin 特有）
```

注释说「仅 InputPlugin 特有」，但代码对 processor 也执行了同样的赋值（processor 配置中也有 `name` 字段为「数据合并与统计」）。实际的「例外」是 Output 插件（因为没有 `name` 字段），所以注释应该是「**Output 除外**」或不做限制性描述。

当前注释可能误导实现者：以为 processor 也不该设置 label，但实际上 processor 有 label 是合理的（便于日志/错误信息）。

**建议**：注释改为「人类可读名称（来自配置的 name 字段）」即可，不做限制性声明。

---

### P3 — 微小问题

#### P3-1: `read_excel_rows` 双类型返回值在 Python 层面的类型标注问题

如果 `read_excel_rows` 是单一迭代器，第一个元素是 `list[str]` 而后续是 `tuple`，类型签名会比较奇怪。这不影响 MVP 实现，但建议在代码注释中说明迭代器的类型切换逻辑，避免协作者困惑。

---

#### P3-2: §6 技术选型表「Excel 读」理由中的「流式逐行读取，内存可控」描述

当前描述只讲了读的性能优势，没有提 read_only 模式的限制（如样式可能不可用）。建议添加一句约束说明。

---

## 三、总体评价

### 迭代趋势

从 v0.1 到 v0.4，这个设计文档经历了四轮审核迭代：

| 版本 | 问题数 | 状态 |
|------|--------|------|
| v0.1 → v0.2 | 修复 10 个，新增 14 个 | 快速成熟期 |
| v0.2 → v0.3 | 修复 14 个，新增 11 个 | 细节打磨期 |
| v0.3 → v0.4 | 修复 11 个，新增 7 个 | 收敛期 |

问题数量在持续下降，问题严重性从 P0 为主降到以 P2/P3 为主，说明设计在稳定收敛。

### 当前版本评估

**v0.4 已经非常接近「可进入实现」的状态。** 2 个 P1 问题都是**文档内部不一致**（非设计缺陷），可以快速修正：
- P1-1：改一句话（§4.6 注释）
- P1-2：调整伪代码示例，让 read_excel_rows 的用法和规范匹配

建议修正后即可进入实现，P2/P3 在实现中边做边澄清。

### 新问题优先级汇总

| 优先级 | 编号 | 问题 | 类型 |
|--------|------|------|------|
| **P1** | P1-1 | §4.6 说错误在「SQL执行阶段」但 §3.5 正确归类为「输出错误」 | 文档矛盾 |
| **P1** | P1-2 | read_excel_rows 双类型返回值与 Input 插件 execute 代码不一致 | 代码/规范矛盾 |
| **P2** | P2-1 | 参数注入方案 B 默认值 `str=""` vs `str\|None=None` 两处不同 | 文档不一致 |
| **P2** | P2-2 | openpyxl read_only 模式能否读取样式/列宽需验证 | 技术风险 |
| **P2** | P2-3 | `required_params() → list[dict]` dict 结构未定义 | 接口缺失 |
| **P2** | P2-4 | 实例化流程 comment 说 label「仅 InputPlugin 特有」但代码也对 processor 赋值 | comment/代码不一致 |
| **P3** | P3-1 | read_excel_rows 双类型迭代器的类型标注建议补充 | 代码规范 |
| **P3** | P3-2 | §6 技术选型表可补充 read_only 模式限制说明 | 文档补充 |
