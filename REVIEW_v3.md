# PipeForge 设计文档 v0.3 Review

> 审核文档: DESIGN_v3.md (文档 v0.3 / 产品 v0.1)  
> 对比基线: REVIEW_v2.md (v0.2 审核)  
> 审核日期: 2026-05-03

---

## 一、v0.2 问题修复情况：逐项核验

### P0 问题

| # | v0.2 问题 | v0.3 修复位置 | 修复内容 | 结果 |
|---|----------|-------------|---------|------|
| P0-1 | 列缺失校验时机错误（声称启动阶段但做不到） | §4.4 | 改为「**在 Processor 执行完成后、Output 写入前**报错」；§3.5 输出错误新增「目标列在查询结果中缺失」；决策 #12「运行时校验列存在性」 | ✅ 已解决 |
| P0-2 | SQL 解析方案缺失 | §4.1、§4.2、§4.6 | Processor 配置新增 `output_tables` 字段（显式声明创建的表名）；§4.6 三条校验规则改为基于 `output_tables` 做纯静态检查；增加说明「避免 SQL 解析」；决策 #16 | ✅ 已解决 |
| P0-3 | openpyxl 样式保留与性能矛盾 | §6.1 | 新增「两阶段写入」方案：read_only 读表头样式 → write_only 写新文件（表头带样式 + 数据行无样式）；性能目标调整为 ≤5 秒；决策 #17 | ✅ 已解决 |

### P1 问题

| # | v0.2 问题 | v0.3 修复位置 | 修复内容 | 结果 |
|---|----------|-------------|---------|------|
| P1-1 | `self.table_name` 来源未定义 | §3.3 | 新增 `InputPlugin(Plugin[C], ABC)` 子类，定义 `table_name: str = ""` 属性，注释「由引擎注入」 | ✅ 已解决 |
| P1-2 | `register_plugin` 装饰器未定义 | §3.3 | 给出装饰器完整实现：`register_plugin(name, type)` 返回 decorator，内部委托 `PluginRegistry.register()`；附带 PluginRegistry 完整类定义 | ✅ 已解决 |
| P1-3 | 输出写入哪个 Sheet 未指定 | §4.1、§4.2 | Output config 新增 `sheet` 字段，默认第一个 Sheet；§4.4 校验描述明确「模板目标 Sheet 首行」 | ✅ 已解决 |
| P1-4 | 输出文件命名规则未定义 | §4.1、§4.2、§4.3 | Output config 新增 `filename` 字段；新增 §4.3「输出文件名规则」节，定义三个变量 + 默认规则 | ✅ 已解决 |
| P1-5 | 参数收集 I/O 边界不清晰 | §3.4 | 新增完整三层架构图：CLI Layer → Engine → Plugins；明确「职责边界」说明；§2.2 更新执行描述；§5 更新 cli.py 注释；决策 #18 | ✅ 已解决 |

### P2 问题

| # | v0.2 问题 | v0.3 修复位置 | 修复内容 | 结果 |
|---|----------|-------------|---------|------|
| P2-1 | 列映射示例冗余 | §4.1 | columns 中多对映射展示实际重命名：「部门→所属部门」「出勤天数→本月出勤天数」「考勤状态→状态」 | ✅ 已解决 |
| P2-2 | 三种 Plugin 子类型未定义 | §3.3 | 明确定义 `InputPlugin`、`ProcessorPlugin`、`OutputPlugin` 三个子类，含注释说明 MVP 行为 | ✅ 已解决 |
| P2-3 | openpyxl 特有异常未覆盖 | §3.5、§4.5 | 输入错误新增「.xls 格式不支持」「文件被占用」「密码保护」；§4.5 模板规范声明「仅支持 .xlsx」和不支持场景 | ✅ 已解决 |
| P2-4 | openpyxl read_only 未指定 | §6、§6.1 | 技术选型表明确标注 `read_only=True`；§6.1 流程中显式使用 | ✅ 已解决 |
| P2-5 | 文档版本 vs 产品版本混淆 | 文档头 | 新增「对应产品版本: v0.1 (MVP)」与「文档版本: v0.3」双行标注 | ✅ 已解决 |
| P2-6 | 模板文件内容要求未说明 | §4.4、§4.5 | 新增 §4.5「模板规范」节（6 条规范）；§4.4 新增「第 2 行起已有数据会被覆盖」说明 | ✅ 已解决 |

### 结论

**v0.2 复审中提出的 14 个问题（3 P0 + 5 P1 + 6 P2）在 v0.3 中全部得到解决。** 特别是 P0-2（用 `output_tables` 声明替代 SQL 解析）是比建议方案更优雅的设计，P0-3（两阶段写入）是符合 openpyxl 特性的务实方案。

---

## 二、v0.3 新发现的问题

### P1 — 重要问题

#### P1-1: 两阶段写入丢失模板的非表头属性（§6.1）

§6.1 两阶段写入方案：

```
阶段 1: read_only 读模板 → 提取首行样式（font/fill/border/alignment/number_format）
阶段 2: write_only 创建新 workbook → 写入带样式表头 → 写入数据
```

核心问题：方案创建的是 **新 workbook**，不是修改原模板。这意味着模板中除了表头样式之外的所有属性都会丢失：

| 丢失的内容 | 影响 |
|-----------|------|
| 列宽设置（column_dimensions） | 输出文件列宽变为默认，用户可能看到截断或过宽的列 |
| 行高设置 | 统一变为默认行高 |
| 打印设置（print_area、page_setup） | 打印排版丢失 |
| Sheet 标签颜色 | 丢失 |
| 冻结窗格（freeze_panes） | 丢失 |
| 缩放比例 | 丢失 |

这些是比较常用的 Excel 模板属性，但文档完全没有提及这个限制。

**建议**：
- §4.5 模板规范中增加「仅保留表头单元格样式，列宽/打印设置/冻结窗格等 sheet 级属性不会保留」
- 或考虑在 write_only 阶段补充设置列宽（`ws.column_dimensions['A'].width = ...`），因为列宽可以从 read_only 阶段读取

---

#### P1-2: `param_key` 到 `config.file` 的解析机制未描述（§3.3 + §4.2）

YAML 配置中：

```yaml
inputs:
  - param_key: person_file    # ← 运行时参数名
    config:
      sheet: 人员列表
```

插件配置模型中：

```python
class ExcelInputConfig(BaseModel):
    file: str                  # ← 但这个字段在 YAML 的 config 中不存在
    sheet: str = "Sheet1"
```

问题：`file` 字段的值不是来自 `config.file`，而是来自 `params["person_file"]`。引擎如何将 `param_key` 解析出的文件路径注入到 `config.file`？这个转换步骤在整个设计文档中没有任何描述。

换句话说，当前 YAML 示例中 **config 里没有 file 字段**，但 Pydantic 模型要求 `file: str` 是必填。这要么导致校验失败，要么有一个隐式的注入逻辑没有写出来。

**建议**：
- 在 §3.4 引擎层或 §4.2 中增加说明：「引擎根据 `param_key` 从 `params` 中取值，注入到插件 config 的 `file` 字段」
- 或者修改 YAML 示例，在 config 中使用占位符：`file: "{{person_file}}"`，明确标识这是一个需要替换的变量

---

#### P1-3: `read_excel_rows` 函数行为未定义（§3.3）

Input 插件代码中使用：

```python
for row in read_excel_rows(config.file, config.sheet):
    context.db.insert_row(self.table_name, row)
```

但 `read_excel_rows` 的行为完全未定义：
- 是否包含表头行？（第一行通常是列名，不应作为数据插入）
- 返回值格式是什么？（tuple？dict？）
- 如果包含表头，表头列名如何与 SQLite 表的列对应？

这直接影响 `insert_row` 能否正确工作——如果表头行也被当作数据插入，SQLite 表的 schema 就乱了。

**建议**：
- 明确定义 `read_excel_rows`：第一行返回列名（用于建表），后续行返回数据 tuples
- 或将 Input 插件的 execute 拆分为两步：`create_table_from_header()` → `insert_data_rows()`

---

### P2 — 建议优化

#### P2-1: 日期格式 `{{date:YYYYMM}}` 不是 strftime 格式（§4.3）

§4.3 原文：

> `{{date:FORMAT}}` | 当前日期，按 strftime 格式 | `{{date:YYYYMM}}` → `202405`

问题：`YYYYMM` 不是 Python `strftime` 的有效格式。正确的 strftime 格式是 `%Y%m`。这里使用了一种自创的格式语法。

如果实现时按字面理解「strftime 格式」，写成 `strftime("%Y%m")` 是对的（因为代码里不会写 `"YYYYMM"`），但文档中的示例 `YYYYMM` 会让读者困惑——这到底映射到哪种 strftime 指令？

**建议**：
- 改用标准 strftime 示例：`{{date:%Y%m}}` → `202405`
- 或者明确这是自定义格式（非 strftime），给出完整映射表：`YYYY`→`%Y`、`MM`→`%m`、`DD`→`%d`、`HH`→`%H`、`mm`→`%M`、`SS`→`%S`

---

#### P2-2: 输出目录路径未指定（§4.3 + §4.5）

§4.3 的默认文件名是 `{scene_name}_{date:YYYYMMDD}.xlsx`（如 `人员月报_20240506.xlsx`），但没有指定保存在哪个目录。

§4.5 的 CLI 输出示例显示 `./output/人员月报_202405.xlsx`，暗示默认输出目录是 `./output/`。但这个目录：
- 由谁创建？（引擎还是 CLI？）
- 如果目录不存在，自动创建还是报错？
- 用户能否自定义输出目录？

**建议**：
- 在 Output config 中增加 `output_dir` 字段（默认 `./output/`）
- 或在 §4.3 中明确「输出到当前工作目录下的 `output/` 子目录，自动创建」

---

#### P2-3: Context 中移除了 `variables` 但带来了限制（§3.3）

v0.1 的 Context 有 `variables: dict` 用于流程变量（时间、环境变量），v0.2/v0.3 中移除了。这符合 MVP 定位，但意味着：

- SQL 中无法使用任何动态值（如「只处理本月数据」）
- 输出文件名虽然支持 `{{date:FORMAT}}`，但这仅限于文件名，无法传递到 SQL 中

这是一个已知的设计取舍（MVP 不做变量替换），但建议在受限项中明确标注，避免实现时出现疑问。

**建议**：在 §9 v0.1 MVP 的 Processor 一行加注：「SQL 中不支持变量替换，所有条件需硬编码」。

---

#### P2-4: `ProcessorStats.tables_created` 的数据来源（§3.3 + §4.1）

`ProcessorStats` 有 `tables_created: list[str]` 字段，用于记录处理器创建了哪些表。但这个字段的值从哪来？

- 是读取 Processor 配置的 `output_tables` 声明？
- 还是执行 SQL 后，查询 `sqlite_master` 获取实际创建的表？

如果使用方案 A（读取声明），则当用户声明和实际 SQL 不符时，统计信息会误导。
如果使用方案 B（运行时查询），则更准确但会有轻微性能开销。

两种方案都没有在文档中说明。

**建议**：明确 `tables_created` 的数据来源（建议方案 B，从 `sqlite_master` 查询，可靠且开销可忽略）。

---

#### P2-5: Plugin 实例化工厂未描述（§3.2 + §3.3）

§3.2 提到「工厂模式：PluginFactory 根据配置中的 `plugin` 字段创建对应插件实例」，但文档中没有 PluginFactory 的接口定义。具体来说：
- PluginFactory 如何获取插件 cls？（从 PluginRegistry.get？）
- PluginFactory 如何注入属性（`label`、`table_name`）？
- 这些步骤在引擎的哪个阶段执行？

**建议**：在 §3.3 增加 PluginFactory 的简要描述，或明确说明引擎直接通过 `PluginRegistry.get()` + 手动注入属性完成实例化。

---

#### P2-6: 错误分类表中「处理错误」缺少 `output_tables` 声明错误

§3.5 处理错误示例：「SQL 语法错误、引用的表不存在」。但如果用户声明 `output_tables: [wrong_table]`，而实际 SQL 创建的是其他表，这种情况属于什么错误？

- SQL 语法正确 → 不算「SQL 语法错误」
- 成功执行了 → 不是处理阶段失败
- 但后续 Output 找不到表 → 属于「输出错误」中的「目标列在查询结果中缺失」或「source_table 不存在」

建议在输出错误中补充「source_table 在 SQLite 中不存在」（区别于配置阶段的 source_table 在 output_tables 中不存在）。

**建议**：输出错误示例增加「source_table 在数据库中不存在（可能因为 processor SQL 实际创建的表名与 output_tables 声明不一致）」。

---

### P3 — 微小问题

#### P3-1: §6.1「打开新 workbook」措辞不准确

§6.1 写道：「阶段 2 (write_only): 打开新 workbook」。在 openpyxl write_only 模式下，实际上是 **创建** 新 workbook（`Workbook(write_only=True)`），不是「打开」现有文件。

---

#### P3-2: `Context.params` 的类型标注有差异

§3.3 中 `Context.params` 标注为 `dict[str, str]`，但 §3.4 引擎的 `execute(params: dict)` 只有 `dict` 没有泛型参数。两处不完全一致，建议统一。

---

## 三、总体评价

### 修复质量

v0.3 比 v0.2 又有显著提升。几个亮点决策：
- **P0-2 的 `output_tables` 声明式方案**：比建议的 SQL 解析更简洁、更声明式，且由用户显式承担正确性责任，是好设计
- **P0-3 的两阶段写入**：巧妙地用 read_only + write_only 组合解决了样式保留与性能的矛盾
- **P1-5 的三层架构图**：非常清晰地界定了 CLI / Engine / Plugin 的职责边界

### 当前版本评估

v0.3 已经没有阻断性（P0）问题了。2 个 P1 问题也属于实现前可以快速澄清的设计细节。**建议解决 2 个 P1 问题后即可进入实现阶段**，P2 可以在实现过程中逐步明确。

### 新问题优先级汇总

| 优先级 | 编号 | 问题 | 类型 |
|--------|------|------|------|
| **P1** | P1-1 | 两阶段写入丢失列宽/打印设置等非表头模板属性 | 功能缺失 |
| **P1** | P1-2 | `param_key` → `config.file` 的解析注入机制未描述 | 设计缺失 |
| **P1** | P1-3 | `read_excel_rows` 行为未定义（是否含表头行） | 接口缺失 |
| **P2** | P2-1 | `{{date:YYYYMM}}` 不是 strftime 格式，文档误导 | 文档错误 |
| **P2** | P2-2 | 输出目录路径未指定 | 需求缺失 |
| **P2** | P2-3 | SQL 中无变量替换的限制应明确标注 | 文档补充 |
| **P2** | P2-4 | `ProcessorStats.tables_created` 数据来源未说明 | 设计缺失 |
| **P2** | P2-5 | PluginFactory 实例化流程未描述 | 设计缺失 |
| **P2** | P2-6 | 错误分类中缺少 output_tables 声明与 SQL 不符的错误路径 | 异常路径 |
| **P3** | P3-1 | 「打开新 workbook」措辞应改为「创建」 | 措辞 |
| **P3** | P3-2 | `params` 类型标注两处不一致 | 一致性 |
