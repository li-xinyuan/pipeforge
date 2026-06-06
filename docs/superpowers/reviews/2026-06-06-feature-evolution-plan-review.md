# ConfigForge 功能演进计划审查报告

> 审查对象：`docs/superpowers/plans/2026-06-06-feature-evolution-plan.md`
> 审查日期：2026-06-06
> 审查结论：计划方向正确、细节丰富，存在 3 个会导致 bug 的技术问题需在开发前修正

---

## 总体评估

计划结构完整、覆盖全面，四个阶段（检查点扩展 → 数据库输出 → 执行历史 → 版本管理）均有明确的目标、技术方案、测试计划和交付标准。但发现 3 个会导致 bug 的技术问题、5 个设计层面的建议和 10 个小问题。

---

## 🔴 会导致 Bug 的问题

### 1. SQLite 标识符转义风格不一致

**位置**：Phase 1.3.2 执行器代码

**问题**：计划中所有执行器使用 `[]` 包裹表名/列名：

```python
sql = f"SELECT COUNT(*) AS total, SUM(CASE WHEN [{rule.column}] IS NULL ..."
```

但现有代码库统一使用双引号 `""`：

```python
# sqlite.py 现有代码
f'CREATE TABLE "{safe_name}" ({safe_cols})'

# preview.py 现有代码
safe_name = f'"{safe_table}"'
```

**影响**：虽然 SQLite 兼容 `[]`，但混合使用两种引号风格会导致维护混乱，且双引号才是 SQL 标准。

**修复**：统一使用双引号 `""`。

---

### 2. 数据库输出插件跨层引用

**位置**：Phase 2.2.2 `DatabaseOutputPlugin`

**问题**：`DatabaseOutputPlugin` 位于 PipeForge 层（引擎/插件），但计划让其直接调用 `ConnectionStore`（位于 ConfigForge 层），违反了依赖方向：

```
PipeForge 层（引擎/插件） ← 不应依赖 → ConfigForge 层（API/服务）
```

计划虽然在 2.2.3 提到在 `_prepare_execution()` 中解析连接，但 2.2.2 的插件伪代码仍写了 `_resolve_connection` 方法，暗示插件自己解析连接字符串。

**修复**：删除插件内的 `_resolve_connection`，连接字符串由 `_prepare_execution()` 在插件外部解析后直接写入 `config.connection_string`，插件仅读取该字段。

---

### 3. Wizard 层模型遗漏 `DatabaseOutputConfig`

**位置**：Phase 2.2.1 / `configforge/models/wizard.py`

**问题**：计划修改了 `src/pipeforge/config/models.py` 中的 `OutputConfig` 联合类型，但遗漏了 `configforge/models/wizard.py` 中的对应类型：

```python
# configforge/models/wizard.py 当前：
class OutputTarget(BaseModel):
    plugin: Literal["excel", "csv"] = "excel"  # ← 缺少 "database"
    config: Annotated[ExcelOutputConfig | CsvOutputConfig,  # ← 缺少 DatabaseOutputConfig
           Field(discriminator="type")]
```

**影响**：API 层反序列化会失败——FastAPI 路由接收请求时无法识别 `type: "database"`。

**修复**：`OutputTarget.plugin` 增加 `"database"`，`config` 联合类型增加 `DatabaseOutputConfig`。

---

## 🟡 设计层面的关键建议

### 4. 阶段依赖顺序值得重新考虑

**当前顺序**：

| 阶段 | 方向 | 声称依赖 |
|------|------|---------|
| Phase 1 | 检查点规则扩展 | 无 |
| Phase 2 | 数据库输出 | 无 |
| Phase 3 | 执行历史 | Phase 2 |
| Phase 4 | 配置版本管理 | Phase 3 |

**问题**：声称的两个依赖都是弱依赖。

| 声称依赖 | 理由 | 实际评估 |
|---------|------|---------|
| Phase 3 → Phase 2 | "数据库输出统计更丰富" | 执行历史的核心功能（记录、列表、下载）对文件输出完全有效。数据库输出的统计只是增量字段，不构成硬依赖 |
| Phase 4 → Phase 3 | "共享可追溯基础设施" | 两者都只是存 JSON 文件，不存在共享代码。版本管理实际上更简单 |

**遗漏的真依赖**：执行记录（Phase 3）应该关联"哪个配置版本"产生的。如果 Phase 4 还没做，执行记录的 `config_version` 字段只能留空，后期需要打补丁。

**建议顺序**：

```
Phase 1: 检查点规则扩展 → 独立，最小范围，先跑通
Phase 4: 配置版本管理   → 独立，给 Phase 3 提供版本锚点
Phase 3: 执行历史管理   → 关联 config_version，一步到位
Phase 2: 数据库输出     → 最复杂，最后做，不受前面阻塞
```

---

### 5. 同步执行导致 `status: "running"` 无实际意义

**问题**：Phase 3 的 `ExecutionRecord` 定义了 `status: Literal["running", "success", "failed"]`，同时明确"暂不改为异步"。但同步执行下：

- HTTP 请求阻塞直到管道执行完成
- 从创建 `running` 记录到更新为 `success`/`failed` 是同一线程内连续操作
- 用户永远不会观察到 `running` 状态

**建议**：要么去掉 `running`（仅 `success`/`failed`），要么在计划中标注为"预留，待异步执行后启用"。

---

### 6. `CustomSqlRule` 校验语义过窄

**问题**：当前设计只能做 `实际值 ≤ max_value` 的单边检查：

```python
passed = rule.max_value is None or float(actual_value) <= rule.max_value
```

真实场景中常见需求远不止此：
- `COUNT(*) >= 100`（最少行数检查）
- `SUM(amount) == expected_total`（金额对账）
- `COUNT(*) < 1000`（数据量上限）

**建议**：增加比较运算符字段：

```python
class CustomSqlRule(BaseModel):
    type: Literal["custom_sql"] = "custom_sql"
    sql: str = ""
    result_column: str = "result"     # 重命名，更清晰
    comparison: Literal["<", "<=", "==", "!=", ">", ">="] = "<="
    expected_value: float | None = None
    on_failure: Literal["block", "warn"] = "block"
```

---

### 7. 唯一性检查的 NULL 陷阱

**问题**：计划中的唯一性检查 SQL：

```sql
SELECT COUNT(*) AS total,
       COUNT(DISTINCT [column]) AS distinct_count
FROM [table]
```

SQL 中 `COUNT(DISTINCT)` 将 NULL 视为一个值，但 `COUNT(column)` **不计 NULL**。当列含有大量 NULL 时，`total`（来自 `COUNT(*)`）包含 NULL 行，而 `distinct_count` 的计算方式导致结果永远偏小。

**举例**：
- 1000 行数据，其中 500 行的该列为 NULL，其余 500 行全是不同值
- `total` = 1000
- `distinct_count` = 501（500 个不同非 NULL 值 + 1 个 NULL group）
- `passed` 永远为 `False`，即使非 NULL 值全唯一

**建议**：加 `WHERE column IS NOT NULL`，或至少在文档中明确说明 NULL 的处理行为。

---

### 8. 回滚语义不明确

**问题**：Phase 4 定义了 `POST /api/configs/{id}/versions/{v}/rollback`，但未说明回滚后的版本模型：

- **方案 A（覆盖式）**：v1 直接变为 current，v2/v3 保留但不再是 current。这是"分支"操作，历史变成分叉
- **方案 B（追加式）**：从 v1 复制内容创建 v4 = v1 的内容。线性历史、可逆、更安全

**建议**：采用方案 B。回滚时创建新版本（内容等于目标版本），在 `change_summary` 中自动标注 "回滚自 v1"。这样用户永远可以"回滚的回滚"。

---

## 🟢 小问题清单

| # | 问题 | 位置 | 严重程度 |
|---|------|------|---------|
| 9 | 新 Rule 模型缺少 `model_config = ConfigDict(extra="forbid")`，与近期 Phase 3.1 的修复不一致 | 1.3.1 | 低 |
| 10 | CheckpointSection 单个组件承载 6 种规则的全部模板，预计超过 400 行 | 1.4.3 | 中 |
| 11 | 模板使用了 `NInputNumber` 但未在 import 语句中列出 | 1.4.3 | 低 |
| 12 | `enum_check` 使用参数化 `IN (?, ?, ...)`——SQLite 默认参数上限 999，大量枚举值可能超限 | 1.3.2 | 低 |
| 13 | `enumValuesInput(i)` 函数在模板中被调用但未在脚本中定义 | 1.4.3 | 低 |
| 14 | 列选项从 dry_run 结果获取，用户可能在 dry_run 前配置检查点导致列表为空 | 1.4.4 | 中 |
| 15 | upsert 跨数据库实现被低估——MySQL `ON DUPLICATE KEY`、PG `ON CONFLICT`、SQLite `INSERT OR REPLACE` 语法完全不同 | 2.2.2 | 中 |
| 16 | 执行记录缺少 `config_version` 字段——应在 Phase 3 设计初期就加入 | 3.3 | 中 |
| 17 | 执行历史未提及脱敏需求——连接字符串等敏感信息出现在执行记录中 | 3.3 | 中 |
| 18 | `deepdiff` 是新增 Python 依赖，应在计划中显式声明 | 4.5 | 低 |

---

## ✅ 计划中做得好的地方

- **Pydantic discriminated union** 使用 `Annotated[Union, Field(discriminator="type")]`——完全正确的现代写法，向后兼容旧配置
- **向后兼容**——旧配置中的 `row_count` 规则会被新 Union 类型正确反序列化，无需迁移
- **安全考量**——custom_sql 复用 `_has_ddl()` 做 DDL 拦截，`enum_check` 使用参数化查询，安全护栏到位
- **测试计划**——每阶段都有前端+后端+API 多层测试，用例数量合理，覆盖通过/失败场景
- **风险表**——已识别 6 个关键风险并有缓解措施，展示了防御性思维
- **"不需要改动"清单**（1.3.4）——明确列出不受影响的文件，避免过度修改和范围蔓延
- **文件存储方案一致性**——全阶段继续使用 JSON 文件而非引入数据库依赖，与现有架构对齐
- **枚举禁止过度设计**——明确排除 `duplicate_rate`（与 uniqueness 重叠）和 `referential_integrity`（跨表查询复杂度高），展示良好的 YAGNI 意识

---

## 总结

| 类别 | 数量 | 处理建议 |
|------|------|---------|
| 🔴 会导致 bug | 3 | 开发前必须修正 |
| 🟡 设计建议 | 5 | 讨论后决定是否采纳 |
| 🟢 小问题 | 10 | 实现时顺手处理 |

**最优先行动项**：重新排列阶段顺序——将 Phase 4（版本管理）提到 Phase 3（执行历史）之前，使执行记录从第一天就能关联正确的配置版本号。其余 2 个红色 bug（SQLite 引号、Wizard 模型遗漏）在执行前修正即可。
