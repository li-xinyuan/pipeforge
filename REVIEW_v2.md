# PipeForge 设计文档 v0.2 Review

> 审核文档: DESIGN\_v2.md (v0.2)\
> 对比基线: REVIEW\.md (v0.1 审核)\
> 审核日期: 2026-05-03

***

## 一、v0.1 问题修复情况：逐项核验

| #   | v0.1 问题                     | v0.2 修复位置   | 修复内容                                                                               | 结果    |
| --- | --------------------------- | ----------- | ---------------------------------------------------------------------------------- | ----- |
| 1.1 | AI 定位矛盾                     | §2.1、§2.2   | 新增「用户角色」表（创建者 vs 执行者）；明确划分「配置创建（可借助 AI）」和「配置执行（纯 CLI）」两个独立阶段                       | ✅ 已解决 |
| 1.2 | 缺少用户画像                      | §2.1        | 表格定义两个角色：技能要求 + 做的事；决策 #10 同步更新                                                    | ✅ 已解决 |
| 1.3 | 缺少非功能性需求                    | §7          | 新增非功能性需求表：数据规模 ≤10万行、性能 ≤3秒、内存 ≤50MB、临时文件策略                                        | ✅ 已解决 |
| 2.1 | 责任链模式与 MVP 不匹配              | §3.2        | 从设计模式表中移除责任链；添加说明"v0.2+ 预留，processors 已设计为列表"；决策 #14                               | ✅ 已解决 |
| 2.2 | 表名冲突                        | §4.4        | 新增三项校验规则：inputs 表名互异、不与 processor CREAT TABLE 冲突、source\_table 必须存在                | ✅ 已解决 |
| 2.3 | Plugin `config: dict` 无类型安全 | §3.3        | 改为泛型 `Generic[C]` + Pydantic `config_model()`；execute 签名改为 `config: C`；附完整代码示例     | ✅ 已解决 |
| 2.4 | 缺少错误处理策略                    | §3.5        | 新增完整章节：错误分类表（4 类）、失败后行为、事务策略、调试支持                                                  | ✅ 已解决 |
| 2.5 | result: dict 无结构            | §3.3        | 改为 `ExecutionResult` + `InputStats` / `ProcessorStats` / `OutputStats` Pydantic 模型 | ✅ 已解决 |
| 3.1 | 列映射健壮性                      | §4.2、§4.3   | columns 改为 `source → target` 显式映射；明确四规则：列缺失→启动报错、顺序从左到右、从第 2 行写数据                  | ✅ 已解决 |
| 3.2 | SQL 注入风险                    | §8、§9、§12   | 明确 v0.2+「安全变量 vs 用户输入变量转义」策略，有具体方案而非仅提风险                                           | ✅ 已解决 |
| 3.3 | 版本兼容策略                      | §4.6        | 新增：`extra="ignore"` 忽略未知字段 + version 字段标记 + 未来自动迁移方案                               | ✅ 已解决 |
| 4.1 | pandas 依赖过重                 | §6          | pandas 从技术选型表移除；加注说明用 openpyxl + sqlite3 executemany；决策 #11                        | ✅ 已解决 |
| 4.2 | Jinja2 场景不清                 | §6          | Jinja2 从技术选型表移除；加注说明移入 v0.2+；§9 v0.2+ 计划中列出                                        | ✅ 已解决 |
| 5.1 | 章节编号跳跃                      | §10、§11、§12 | 现在是连续编号：9(版本规划)→10(决策记录)→11(实现计划)→12(已解决事项)                                        | ✅ 已解决 |
| 5.2 | 待明确事项后置                     | §12         | 所有原待明确事项已决策并分布到各章节；§12 列出决议供追溯                                                     | ✅ 已解决 |

### 结论

**v0.1 复审中提出的 10 个问题（6 类 × 15 子项）在 v0.2 中全部得到解决。** 设计者在每个问题上都给出了具体方案而非笼统回应，质量较高。

***

## 二、v0.2 新发现的问题

### P0 — 阻断性问题

#### P0-1: 列缺失校验时机错误（§4.3 与执行流程矛盾）

§4.3 原文：

> `source` 列必须在 `source_table` 的查询结果中存在，否则 **启动阶段报错终止**

**问题**：`source_table`（如 `report_data`）是由 Processor 在运行时通过 `CREATE TABLE report_data AS SELECT ...` 创建的，在「启动阶段」（配置加载时）这个表根本不存在于 SQLite 中。因此，`source` 列的校验 **不可能在启动阶段完成**，只能发生在 Processor 执行之后、Output 写入之前的运行时阶段。

这属于设计文档中的事实错误——宣称了一个不可能做到的校验时机。

**建议**：将 source 列校验的时机改为「Processor 执行完成后、Output 写入前」，不要宣称是「启动阶段」。

***

#### P0-2: 配置校验需要解析 SQL 但无方案（§4.4 规则 2/3）

§4.4 列出三项校验规则，其中：

- 规则 2：`inputs[].table` 不与 processor 中 `CREATE TABLE` 的表名冲突
- 规则 3：`output.config.source_table` 必须存在于 processor 创建的表中

**问题**：执行这两条规则的前提是——在配置加载阶段，引擎能够识别出 Processor 的 SQL 中创建了哪些表。这要求引擎具备 SQL 解析能力（从 SQL 文本中提取 `CREATE TABLE xxx AS` 语句中的表名）。文档完全没有描述：

- 用什么方式解析 SQL？（正则？sqlparse 库？sqlite3 的 `explain`？）
- 如果 SQL 中有多条 CREATE TABLE 语句怎么办？
- 如果 SQL 语法复杂（子查询、CTE 中包含 CREATE）怎么处理？
- 解析失败时属于「配置错误」还是「处理错误」？

**建议**：

- 明确 SQL 解析方案（建议用 `sqlparse` 或内置 sqlite3 的 schema query）
- 或者改为执行后校验：executor 执行完 SQL 后查询 `sqlite_master` 对比验证
- 在错误分类表中增加一行说明 SQL 解析失败属于「配置错误」

***

#### P0-3: openpyxl 模板样式保留与性能目标矛盾（§6 + §7 + 决策 #8）

三处设计之间存在根本矛盾：

| 要求         | 来源       | 含义                                         |
| ---------- | -------- | ------------------------------------------ |
| 保留模板样式     | 决策 #8、§6 | 必须使用 openpyxl 普通模式（不能使用 `write_only=True`） |
| 1 万行 ≤ 3 秒 | §7 性能目标  | 读 + SQL + 写总计 3 秒内完成                       |
| 内存 ≤ 50MB  | §7 内存目标  | 整体内存占用 ≤ 50MB                              |

**问题**：

- openpyxl 的 `write_only=True` 模式下才能高效写入，但该模式 **无法保留模板样式**
- 普通模式（保留样式）对每个单元格单独设置样式，写入 1 万行数据的耗时远超 3 秒（实测通常 20\~60 秒）
- 普通模式下 openpyxl 将整个 workbook 加载到内存，加上数据本身，10 万行场景下很容易超过 50MB

这是一个设计层面的取舍问题：要么降性能目标，要么放弃模板样式保留（改用纯数据输出 + 外部样式预设）。

**建议**：

- 给出 openpyxl 普通模式的基准测试数据来支撑性能目标
- 或明确承认性能目标仅适用于纯数据写入（不含样式保留）
- 或考虑替代方案：使用 xlsxwriter（速度更快但格式不同）或分两步（先写数据，再用 openpyxl 套样式）

***

### P1 — 重要问题

#### P1-1: `ExcelInputPlugin.table_name` 属性来源未定义（§3.3 代码示例）

§3.3 中 `ExcelInputPlugin.execute()` 第 135 行：

```python
def execute(self, context: Context, config: ExcelInputConfig) -> None:
    df = read_excel(config.file, config.sheet)
    context.db.insert_table(self.table_name, df)  # ← self.table_name 从哪来？
```

`table_name` 既不在 `Plugin` 基类中定义，也不在 `ExcelInputConfig` 中定义。实际来源是 YAML 配置中 `inputs[].table` 字段，但它如何注入到插件实例中的机制完全没有描述。

**建议**：

- 在 Plugin 基类中增加 `table_name: str` 属性，由引擎在实例化后注入
- 或通过 Context 传递（`context.current_input_table`）
- 在文档中明确注入时机和机制

***

#### P1-2: `register_plugin` 装饰器未定义（§3.3 vs §3.4）

§3.3 代码中使用了：

```python
@register_plugin("excel", "input")
class ExcelInputPlugin(InputPlugin):
```

但 §3.4 类图中 `PluginRegistry` 的方法签名是：

```
register(name, plugin_type, cls)
get(name, plugin_type) → Plugin 实例
```

**问题**：

- `register_plugin` 装饰器的函数签名、返回值、实现逻辑均未定义
- §3.4 中 `register(name, plugin_type, cls)` 是一个普通方法，但装饰器模式的调用方式是 `register_plugin(name, type)(cls)`，两者不匹配
- 如果 `register_plugin("excel", "input")` 返回一个 decorator，那么它和 `PluginRegistry.register` 的关系是什么？

**建议**：

- 明确 `register_plugin` 是 `PluginRegistry` 的类方法还是模块级函数
- 给出装饰器的伪代码实现
- 统一 §3.3 和 §3.4 中的接口描述

***

#### P1-3: 输出写入哪个 Sheet 未明确（§4.1、§4.3）

§4.3 说「数据行从模板的第 2 行开始写入」，但完全没有指定写入模板的哪个 Sheet。

**场景**：一个模板 .xlsx 文件可能有多个 Sheet（如「报表」「说明」「数据源」），引擎如何知道数据写入哪个 Sheet？

**建议**：

- 在 Output config 中增加 `sheet` 字段，指定目标 Sheet 名称（默认为第一个 Sheet）
- 对应的，§4.3 中 target 列的「模板文件首行列头」校验也应明确是「目标 Sheet 的首行」

***

#### P1-4: 输出文件命名规则未定义（§4.5 示例）

§4.5 的 CLI 输出示例显示：

```
输出: ./output/人员月报_202405.xlsx
```

但 `_202405` 这个日期后缀从哪来？配置文件里没有定义输出文件名规则。

**建议**：

- 在 Output config 中增加 `filename` 字段，支持模板变量（如 `人员月报_{{date:YYYYMM}}.xlsx`）
- 或至少给出默认命名规则（如 `{scene.name}_{timestamp}.xlsx`）

***

#### P1-5: 参数收集的 I/O 边界不清晰（§3.4 + §4.5）

§3.4 引擎类图中：

```
├── collect_params() → list[str]  # 收集所有 param_key
```

但 §4.5 展示了两种参数获取方式：

1. **交互式引导**：引擎在终端提示用户输入文件路径
2. **命令行传参**：`--param person_file=./data/persons.xlsx`

**问题**：

- `collect_params()` 返回 `list[str]` 是 param\_key 名称列表，还是已解析的参数值？
- 交互式引导中，谁负责终端 I/O？引擎做 `input()` 调用？还是 CLI 层做？
- 如果是引擎做 I/O，引擎就和终端耦合了，不符合分层架构
- 如果是 CLI 做 I/O，参数应该在进入引擎 `execute()` 之前已经解析完毕，那引擎的 `collect_params()` 不该返回列表，而应返回已填充的 params dict

**建议**：

- 明确职责边界：CLI 负责参数收集（无论交互式还是命令行），引擎只接受已解析的 `params: dict`
- 将 `collect_params()` 移到 CLI 层或改为 `required_params() → list[str]` 仅声明需要哪些参数
- 或者改为策略模式：引擎持有一个 `ParamResolver` 接口，CLI 提供实现

***

### P2 — 建议优化

#### P2-1: 列映射示例冗余无意义（§4.1）

YAML 示例中所有 `source` 和 `target` 值完全相同：

```yaml
columns:
  - source: 姓名
    target: 姓名
  - source: 部门
    target: 部门
```

这无法展示 `source → target` 映射的核心价值——列重命名。读者看到会困惑："既然一样，为什么要分开写？"

**建议**：至少让一对映射展示重命名功能，例如：

```yaml
  - source: 出勤天数
    target: 本月出勤天数
```

***

#### P2-2: InputPlugin / OutputPlugin / ProcessorPlugin 基类未定义（§3.3 + §5）

§3.3 只定义了泛型基类 `Plugin[C]`，§5 包结构中提到了 `plugins/base.py`（抽象基类 + 泛型 + Pydantic Config），但三个子类型接口完全没有出现：

- `InputPlugin`：输入特有的生命周期？（如 `validate_source()`）
- `ProcessorPlugin`：处理特有的接口？（如 `get_output_tables()`）
- `OutputPlugin`：输出特有的接口？（如 `get_required_columns()`）

§3.4 类图中引擎直接调用 `input_plugin.execute()`、`processor_plugin.execute()`、`output_plugin.execute()`，它们看起来用的是同一个签名，那为什么需要三种类型？

**建议**：明确三个子类型的差异化接口（如果有的话），或说明 MVP 阶段它们就是 `Plugin` 的别名，不需要额外方法。

***

#### P2-3: 缺少 openpyxl 特有异常的处理说明（§3.5）

§3.5 的错误分类表没有覆盖 openpyxl 可能抛出的特定异常：

- Excel 文件有密码保护 → `openpyxl.utils.exceptions.InvalidFileException`
- 模板中有合并单元格覆盖了数据写入区域
- .xls 旧格式文件 → openpyxl 不支持（只支持 .xlsx）
- 模板文件被其他程序占用 → `PermissionError`

**建议**：在输入/输出错误分类中补充至少「文件格式不支持」和「文件被占用」两种情况。

***

#### P2-4: openpyxl 读取模式未指定（§6）

§6 说 openpyxl「可逐行读取避免大内存」，但没有提需要设置 `read_only=True` 模式才能实现真正流式读取。默认模式下 `iter_rows()` 仍然会将整个 sheet 加载到内存。

**建议**：明确在 Input 插件实现中使用 `load_workbook(filename, read_only=True)` + `iter_rows()` 的组合，并说明此模式的限制（如无法获取部分单元格属性）。

***

#### P2-5: 文档版本号与产品版本号混淆

- 文档头声明 `版本: v0.2`
- §9 版本规划中列出 `v0.1 MVP` 和 `v0.2+ 后续迭代`
- 这意味着文档 v0.2 对应的是产品 v0.1

读者容易困惑：这文档到底描述的是产品 v0.1 还是 v0.2？

**建议**：文档版本和产品版本使用不同编号体系，或明确标注「本文档对应产品版本 v0.1」。

***

#### P2-6: 模板文件内容要求未说明（§4.1、§4.3）

§4.3 说「数据行从模板的第 2 行开始写入（第 1 行为表头，保持不变）」但未说明：

- 模板中如果第 2 行之后有已有数据（如示例数据行、公式、汇总行），行为是什么？覆盖还是追加？
- 如果模板的列数多于 columns 配置，多余的列怎么处理？
- 模板是否可以有图表、数据验证规则、条件格式？

**建议**：增加「模板规范」说明，明确模板应只包含一行表头，第 2 行起为空，无图表/公式/数据验证。

***

## 三、总结

### 修复质量评价

v0.2 的设计者对 v0.1 审核意见的采纳非常认真，所有 10 个问题都有实质性修复而非敷衍。特别是：

- 用户角色/阶段划分（§2）设计得很清晰
- 泛型 Plugin 设计（§3.3）很有工程感
- 错误处理策略（§3.5）覆盖全面
- 表名冲突检测（§4.4）考虑周全

### 新问题优先级汇总

| 优先级    | 编号   | 问题                                        | 类型    |
| ------ | ---- | ----------------------------------------- | ----- |
| **P0** | P0-1 | 列缺失校验时机错误（声称启动阶段但做不到）                     | 事实错误  |
| **P0** | P0-2 | SQL 解析方案缺失，「知道 processor 创建了哪些表」无机制       | 设计缺失  |
| **P0** | P0-3 | openpyxl 模板样式保留与性能/内存目标矛盾                 | 设计矛盾  |
| **P1** | P1-1 | `self.table_name` 属性来源未定义                 | 代码缺陷  |
| **P1** | P1-2 | `register_plugin` 装饰器未定义，与 registry 接口不匹配 | 接口不一致 |
| **P1** | P1-3 | 输出写入哪个 Sheet 未指定                          | 需求缺失  |
| **P1** | P1-4 | 输出文件命名规则未定义                               | 需求缺失  |
| **P1** | P1-5 | 参数收集的 I/O 边界不清晰，引擎与 CLI 职责模糊              | 架构边界  |
| **P2** | P2-1 | 列映射示例冗余无意义                                | 文档优化  |
| **P2** | P2-2 | 三种 Plugin 子类型接口未定义                        | 接口缺失  |
| **P2** | P2-3 | openpyxl 特有异常处理未覆盖                        | 异常路径  |
| **P2** | P2-4 | openpyxl read\_only 模式未指定                 | 实现细节  |
| **P2** | P2-5 | 文档版本 vs 产品版本号混淆                           | 文档规范  |
| **P2** | P2-6 | 模板文件内容要求未说明                               | 需求缺失  |

