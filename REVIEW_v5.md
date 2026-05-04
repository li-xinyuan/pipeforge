# PipeForge 设计文档 v0.5 Review

> 审核文档: DESIGN_v5.md (文档 v0.5 / 产品 v0.1)  
> 对比基线: REVIEW_v4.md (v0.4 审核)  
> 审核日期: 2026-05-03

---

## 一、v0.4 问题修复情况：逐项核验

| # | v0.4 问题 | v0.5 修复位置 | 修复内容 | 结果 |
|---|----------|-------------|---------|------|
| P1-1 | §4.6「SQL执行阶段报错」与 §3.5「输出错误」矛盾 | §4.6 注释 | 改为「会在运行时 **Output 阶段**报错（source_table 在数据库中不存在）」 | ✅ 已解决 |
| P1-2 | read_excel_rows 双类型返回值与 execute 代码矛盾 | §3.3、决策 #21 | 重新设计为返回 `(columns: list[str], rows: Iterator[tuple])` 元组；execute 代码改为先 `create_table(columns)` 再迭代 `rows` 插入 | ✅ 已解决 |
| P2-1 | 参数注入方案 B 默认值 `str=""` vs `str\|None=None` 矛盾 | §3.3 | 统一为 `file: str \| None = None`，移除 `str = ""`；步骤 1 描述「此时 `file` 字段为 None」 | ✅ 已解决 |
| P2-2 | openpyxl read_only 能否读取样式/列宽需验证 | §6、§6.1、§7、§9、§11 | **改为普通模式读取模板**：§6「Excel 读」改为 `openpyxl（普通模式）`；§6.1 步骤 1 改为 `load_workbook(filename)` 无 `read_only=True`，流程图标注「阶段 1 (普通模式)」；新增注释说明模板数据量极小、内存开销可控 | ✅ 已解决 |
| P2-3 | `required_params() → list[dict]` 结构未定义 | §3.4 | 新增 `RequiredParam` Pydantic 模型（`key`/`label`/`description`）+ 示例返回值；类图注释改为 `list[RequiredParam]` | ✅ 已解决 |
| P2-4 | 实例化流程 comment「仅 InputPlugin 特有」与代码不一致 | §3.3 | 注释改为「人类可读名称（来自配置的 name 字段）」，移除限制性说明 | ✅ 已解决 |
| P3-1 | read_excel_rows 双类型迭代器标注问题 | §3.3 | 因改为 `(columns, rows)` 元组返回，类型不再混合，问题自然消除 | ✅ 已解决 |
| P3-2 | §6 技术选型缺少 read_only 限制说明 | §6 | 改为普通模式后不再适用，且新注释已说明选择理由 | ✅ 已解决 |

### 结论

**v0.4 复审中提出的 8 个问题（2 P1 + 4 P2 + 2 P3）在 v0.5 中全部得到解决。** 其中 P2-2 的解决方式尤其值得肯定——设计者没有盲目保留 `read_only`，而是基于「模板只含表头行、数据量极小」的实际情况，直接改用普通模式读取，从根源消除了风险。

---

## 二、v0.5 新发现的问题

### P2 — 建议优化

#### P2-1: Processor YAML 中 `sql` 字段嵌套层级与 Input/Output 不一致（§4.1）

对比三段配置的插件专属参数位置：

```yaml
# Input —— 插件专属配置嵌套在 config: 下
inputs:
  - name: 人员明细
    plugin: excel
    table: person_detail      # 引擎级字段
    param_key: person_file    # 引擎级字段
    config:                   # ← 插件专属
      sheet: 人员列表

# Processor —— 插件专属配置（sql）在顶层，与引擎字段平级
processors:
  - name: 数据合并与统计
    plugin: sql
    output_tables: [...]      # 引擎级字段
    sql: |                    # ← 插件专属，但在顶层，没有 config: 嵌套
      CREATE TABLE ...

# Output —— 插件专属配置嵌套在 config: 下
output:
  plugin: excel
  config:                     # ← 插件专属
    template: ...
    sheet: ...
    source_table: ...
```

Input 和 Output 的插件专属字段都嵌套在 `config:` 块下，唯独 Processor 的 `sql` 直接放在顶层。这不一致，会导致：
- Pydantic 模型设计时三种配置的结构模式不统一
- 新人阅读配置示例时会困惑为什么 processor 的特殊规则不一样

**建议**：将 `sql` 也放入 `config:` 块下：

```yaml
processors:
  - name: 数据合并与统计
    plugin: sql
    output_tables:
      - report_data
    config:
      sql: |
        CREATE TABLE report_data AS ...
```

或者如果认为 `sql` 本身就是唯一的处理器配置且足够简洁不想嵌套，那至少在文档中加一句说明为什么 processor 的配置风格不同于 input/output。

---

#### P2-2: §4.2 关键字段表缺少 `processors[].sql` 字段说明

§4.2 关键字段表中列出了 `processors[].output_tables`，但没有列出 `processors[].sql`。相比之下，同表中 Input 的 `config.sheet` 和 Output 的各种 config 子字段都有说明。

**建议**：补充一行 `processors[].sql` 的说明。

---

#### P2-3: Output 插件没有 `name` 字段，引擎 pseudocode 中 `config.name` 会出错（§3.3）

§3.3「插件实例化流程」伪代码：

```python
plugin.label = config.name  # 人类可读名称（来自配置的 name 字段）
```

这段代码在 Input 和 Processor 的场景下正确（两者配置中都有 `name` 字段），但 Output 配置中**没有** `name` 字段：

```yaml
output:
  plugin: excel
  config:
    template: ...
```

如果引擎对 Output 也执行同样的赋值逻辑，`config.name` 会抛出 `AttributeError`。

**建议**：
- 伪代码中增加对 Output 的处理判断（如 `if hasattr(config, "name")`）
- 或在 Plugin 实例化章节说明「Output 插件的 label 为空字符串」
- 或在 Output 配置中增加 `name` 字段保持一致性

---

### P3 — 微小问题

#### P3-1: 「插件实例化流程」只展示了 Input 的处理（§3.3）

§3.3 的伪代码只展示了 `"input"` 类型的插件实例化流程。Processor 和 Output 的实例化虽然类似（不需要 `table_name` 注入），但作为完整的「流程」说明，没有显式涵盖三种情况是一个小缺口。

**建议**：简单补充一句「Processor 和 Output 的实例化流程与 Input 相同，仅不注入 `table_name`」。

---

#### P3-2: `resolved_config` 的构建与参数注入章节缺少显式衔接（§3.3）

「插件实例化流程」伪代码末尾是：

```python
plugin.execute(context, resolved_config)
```

而「参数注入机制」章节描述了 `config.file` 如何被注入。但两节之间没有交叉引用——读者读到 `resolved_config` 时不知道它来自参数注入步骤。

**建议**：在 pseudocode 中增加一行注释 `# resolved_config 已通过参数注入机制完成 file 字段的赋值`，或在参数注入机制章节末尾加一句「上述步骤完成后得到 `resolved_config`，传入 `plugin.execute()`」。

---

#### P3-3: 错误分类表中「输入错误」纳入了「首行为空」（§3.5）

§3.5 错误分类：输入错误新增了「首行为空」。而 §3.3 数据读取规范中说「如果首行为空，报输入错误」。两处一致 ✓。但考虑到「首行为空」的检测时机是在读取输入数据时（非配置阶段），归类为「输入错误」是正确的。

这一点本身没有问题，值得作为审核注释标注出来（无操作项）。

---

## 三、总体评价

### 迭代趋势

| 版本 | 问题数 | 说明 |
|------|--------|------|
| v0.1 → v0.2 | 修复 10，新增 14 | 快速成熟 |
| v0.2 → v0.3 | 修复 14，新增 11 | 细节打磨 |
| v0.3 → v0.4 | 修复 11，新增 8 | 开始收敛 |
| v0.4 → v0.5 | **修复 8，新增 5** | 稳定收敛 |

问题数量持续减少，严重级别已无 P0/P1，全部为 P2/P3 级别的优化建议。

### 当前版本评估

**v0.5 已经可以进入实现阶段。** 新发现的 5 个问题全部是 P2/P3 级别，不影响核心架构和实现路径：

- P2-1/P2-2：YAML 配置结构可以边实现边统一
- P2-3：Output 插件 label 赋值是代码实现细节，不可能写错

**建议**：可以直接基于 v0.5 开始实现 v0.1 MVP，P2 问题在实现过程中顺便修正即可。

### 五轮审核统计

| 版本 | 累计修复 | P0 | P1 | P2 | P3 |
|------|---------|----|----|----|-----|
| v0.1 | — | 3 | 5 | 2 | 0 |
| v0.2 | 10 | 3 | 5 | 6 | 0 |
| v0.3 | 24 | 0 | 3 | 6 | 2 |
| v0.4 | 35 | 0 | 2 | 4 | 2 |
| v0.5 | **43** | **0** | **0** | **3** | **2** |

### 新问题优先级汇总

| 优先级 | 编号 | 问题 | 类型 |
|--------|------|------|------|
| **P2** | P2-1 | Processor YAML 中 `sql` 字段未嵌套在 `config:` 下，与 Input/Output 不一致 | 结构不一致 |
| **P2** | P2-2 | §4.2 关键字段表缺少 `processors[].sql` 字段说明 | 文档缺失 |
| **P2** | P2-3 | Output 插件无 `name` 字段，引擎 pseudocode 中 `config.name` 会出错 | 边界情况 |
| **P3** | P3-1 | 插件实例化 pseudocode 只展示了 Input，未涵盖全部三种类型 | 文档覆盖 |
| **P3** | P3-2 | `resolved_config` 与参数注入章节缺少显式交叉引用 | 文档衔接 |
