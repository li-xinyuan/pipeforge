# ConfigForge 功能演进全面测试报告

> 日期：2026-06-06
> 测试范围：Phase 1（检查点规则扩展）→ Phase 2（配置版本管理）→ Phase 3（执行历史）→ Phase 4（数据库输出）
> 测试环境：macOS / Python 3.13.3 / Node.js / Vue 3 + Vitest + vue-tsc

---

## 一、测试总览

| 测试类别 | 通过 | 失败 | 总计 | 通过率 |
|----------|------|------|------|--------|
| 后端 pytest（全量） | 327 | 13 | 340 | 96.2% |
| 前端 vitest（全量） | 124 | 0 | 124 | 100% |
| 前端 vue-tsc 类型检查 | 0 error | - | - | 100% |
| **合计** | **451** | **13** | **464** | **97.2%** |

---

## 二、后端测试详细结果

### 2.1 全量 pytest 结果

```
327 passed, 13 failed, 1 warning in 1.24s
```

### 2.2 失败测试清单

| # | 测试文件 | 测试用例 | 失败原因 | 根因分类 | 所属阶段 |
|---|----------|----------|----------|----------|----------|
| 1 | `tests/test_csv_output.py` | `test_custom_encoding` | `ValueError: column_name '姓名' is not a valid SQL identifier` | safe_identifier 不支持中文列名 | 历史遗留 |
| 2 | `tests/test_engine_multiproc.py` | `test_two_processors_chain` | `ValueError: column_name '姓名' is not a valid SQL identifier` | 同上 | 历史遗留 |
| 3 | `tests/test_excel_input.py` | `test_execute_writes_to_db` | `ValueError: column_name '姓名' is not a valid SQL identifier` | 同上 | 历史遗留 |
| 4 | `tests/test_integration.py` | `test_end_to_end` | `ValueError: column_name '工号' is not a valid SQL identifier` | 同上 | 历史遗留 |
| 5 | `tests/test_integration.py` | `test_join_pipeline` | `ValueError: column_name '工号' is not a valid SQL identifier` | 同上 | 历史遗留 |
| 6 | `tests/test_integration.py` | `test_empty_output` | `ValueError: column_name '工号' is not a valid SQL identifier` | 同上 | 历史遗留 |
| 7 | `tests/test_integration.py` | `test_csv_input_loads_data` | `ValueError: column_name '姓名' is not a valid SQL identifier` | 同上 | 历史遗留 |
| 8 | `tests/test_integration.py` | `test_pipeline_to_csv_output` | `ValueError: column_name '工号' is not a valid SQL identifier` | 同上 | 历史遗留 |
| 9 | `tests/test_sql_processor.py` | `test_execute_creates_table` | `AssertionError: <sqlite3.Row> != ('1', 'Alice')` | row_factory=Row 导致返回类型不匹配 | 历史遗留 |
| 10 | `tests/test_sql_processor.py` | `test_jinja2_template_rendering` | `AssertionError: <sqlite3.Row> != ('1', 'Alice')` | 同上 | 历史遗留 |
| 11 | `tests/test_sqlite.py` | `test_insert_and_query` | `AssertionError: [<sqlite3.Row>] != [('1', 'Alice')]` | 同上 | 历史遗留 |
| 12 | `tests/test_sqlite.py` | `test_execute_returning_rows` | `AssertionError: [<sqlite3.Row>] != [('1', 'Alice')]` | 同上 | 历史遗留 |
| 13 | `configforge/tests/api/test_config_versions.py` | `test_diff_between_versions` | `ModuleNotFoundError: No module named 'deepdiff'` | deepdiff 依赖未安装 | Phase 2 |

### 2.3 失败根因分析

#### 根因 A：`safe_identifier()` 不支持中文列名（8 个失败）

**位置**：`src/pipeforge/core/sqlite.py` 第 9 行

**现状**：
```python
_SQL_ID_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")
```

**问题**：正则仅允许 ASCII 字母/数字/下划线，中文字符（如 `姓名`、`工号`）被拒绝。但 SQLite 完全支持中文标识符（用双引号包裹），且项目实际业务数据大量使用中文列名。

**影响范围**：所有使用中文列名的 Excel/CSV 输入插件测试全部失败，这是核心功能阻塞问题。

**修复方向**：将正则改为支持 Unicode 字母，如 `r"^[\w][\w]{0,63}$"`（Python 3 的 `\w` 包含 Unicode 字母和数字）。

#### 根因 B：`sqlite3.Row` vs `tuple` 类型不匹配（4 个失败）

**位置**：`src/pipeforge/core/sqlite.py` 第 34 行

**现状**：
```python
self._conn.row_factory = sqlite3.Row
```

**问题**：`row_factory = sqlite3.Row` 使 `query()` 返回 `sqlite3.Row` 对象而非 `tuple`，但测试用例使用 `==` 直接比较 `Row` 和 `tuple`，导致 `AssertionError`。`Row` 对象支持按列名访问（如 `row["name"]`），但不等于同值的 `tuple`。

**影响范围**：仅影响 4 个测试用例的断言方式，不影响实际功能。

**修复方向**：二选一——
- (a) 修改测试断言：`assert tuple(rows[0]) == ("1", "Alice")` 或 `assert rows[0]["id"] == "1"`
- (b) 修改 `query()` 返回类型：去掉 `row_factory`，返回原生 `tuple`（但会破坏按列名访问的现有代码）

#### 根因 C：`deepdiff` 依赖未安装（1 个失败）

**位置**：`configforge/api/configs.py` 第 423 行

**现状**：代码中 `from deepdiff import DeepDiff`，但 `deepdiff` 未在 `pyproject.toml` / `requirements.txt` 中声明。

**问题**：Phase 2 版本对比功能使用了 `deepdiff` 库，但依赖未安装。

**修复方向**：在 `pyproject.toml` 的 `dependencies` 中添加 `deepdiff`。

---

## 三、各阶段专项测试结果

### Phase 1：检查点规则扩展

| 测试文件 | 通过 | 失败 | 总计 |
|----------|------|------|------|
| `tests/test_checkpoints.py` | 9 | 0 | 9 |
| `configforge/tests/test_checkpoints.py` | 20 | 0 | 20 |
| **合计** | **29** | **0** | **29** |

**详细用例**：

| 用例 | 结果 |
|------|------|
| RowCountExecutor - count_in_range | PASSED |
| RowCountExecutor - count_below_min | PASSED |
| RowCountExecutor - count_above_max | PASSED |
| RowCountExecutor - warn_does_not_block | PASSED |
| RowCountExecutor - empty_table_defaults | PASSED |
| ExecuteChecks - collects_all_results | PASSED |
| ExecuteChecks - unknown_rule_type_raises | PASSED |
| ExecuteChecks - empty_checkpoints | PASSED |
| ExecuteChecks - result_has_timestamp | PASSED |
| NullRateRule - pass_under_threshold | PASSED |
| NullRateRule - fail_over_threshold | PASSED |
| NullRateRule - empty_table_no_division_by_zero | PASSED |
| UniquenessRule - pass_all_unique | PASSED |
| UniquenessRule - fail_duplicate_exists | PASSED |
| UniquenessRule - null_values_excluded | PASSED |
| ValueRangeRule - pass_all_in_range | PASSED |
| ValueRangeRule - fail_out_of_range | PASSED |
| ValueRangeRule - pass_no_bounds_set | PASSED |
| ValueRangeRule - min_only | PASSED |
| CustomSqlRule - pass_comparison_holds | PASSED |
| CustomSqlRule - fail_comparison_violated | PASSED |
| CustomSqlRule - all_six_comparison_operators | PASSED |
| CustomSqlRule - ddl_blocked | PASSED |
| CustomSqlRule - empty_sql_skips | PASSED |
| CustomSqlRule - no_expected_value_passes | PASSED |
| EnumCheckRule - pass_all_in_allowed | PASSED |
| EnumCheckRule - fail_value_not_allowed | PASSED |
| EnumCheckRule - empty_allowed_skips | PASSED |
| EnumCheckRule - over_900_values_rejected | PASSED |

**Phase 1 结论**：全部 29 个测试通过，5 种新检查点规则执行器功能完整，包括：
- CustomSqlRule 支持 6 种比较运算符（<, <=, ==, !=, >, >=）
- UniquenessRule 正确排除 NULL 值
- EnumCheckRule 超 900 枚举值拒绝执行
- DDL 注入拦截正常工作

### Phase 2：配置版本管理

| 测试文件 | 通过 | 失败 | 总计 |
|----------|------|------|------|
| `configforge/tests/api/test_config_versions.py` | 7 | 1 | 8 |

**详细用例**：

| 用例 | 结果 |
|------|------|
| first_save_has_current_version_1 | PASSED |
| second_save_creates_version_history | PASSED |
| list_versions | PASSED |
| get_specific_version | PASSED |
| rollback_creates_new_version | PASSED |
| diff_between_versions | **FAILED**（deepdiff 未安装） |
| invalid_config_id_returns_400 | PASSED |
| nonexistent_config_returns_200_empty_list | PASSED |

**Phase 2 结论**：7/8 通过。唯一失败是 `deepdiff` 依赖未安装，安装后即可通过。核心功能（版本创建、版本列表、回滚追加式、版本获取）均正常。

### Phase 3：执行历史

| 测试文件 | 通过 | 失败 | 总计 |
|----------|------|------|------|
| `configforge/tests/test_models_wizard.py` | 15 | 0 | 15 |
| `configforge/tests/api/test_connections.py` | 11 | 0 | 11 |
| `configforge/tests/services/test_connection_store.py` | 11 | 0 | 11 |

**Phase 3 结论**：关联测试全部通过。ExecutionRecord 模型含 `config_version` 字段，执行历史 API 端点已实现。

### Phase 4：数据库输出

| 测试文件 | 通过 | 失败 | 总计 |
|----------|------|------|------|
| `tests/test_config_models.py` | 38 | 0 | 38 |
| `configforge/tests/test_models_wizard.py`（含 DatabaseOutputConfig） | 15 | 0 | 15 |

**Phase 4 结论**：DatabaseOutputConfig 模型测试通过，OutputTarget 联合类型包含 database 选项。DatabaseOutputPlugin 无 `_resolve_connection` 方法，符合设计。

---

## 四、前端测试详细结果

### 4.1 vitest 全量结果

```
19 test files, 124 tests passed, 0 failed, duration 2.18s
```

| 测试文件 | 通过 | 失败 |
|----------|------|------|
| AiChatPanel.test.ts | 7 | 0 |
| AiInlineTip.test.ts | 5 | 0 |
| CheckpointSection.test.ts | 7 | 0 |
| ColumnMapping.test.ts | 6 | 0 |
| ConnectionManager.test.ts | 7 | 0 |
| DatabaseForm.test.ts | 9 | 0 |
| ExportActions.test.ts | 4 | 0 |
| InputSourceCard.test.ts | 6 | 0 |
| ProcessorCard.test.ts | 6 | 0 |
| PythonProcessorContent.test.ts | 7 | 0 |
| SceneInfoForm.test.ts | 6 | 0 |
| WizardProgress.test.ts | 7 | 0 |
| WizardStepCard.test.ts | 6 | 0 |
| YamlPreview.test.ts | 2 | 0 |
| useConfigApi.test.ts | 10 | 0 |
| useErrorHandler.test.ts | 5 | 0 |
| useFileUpload.test.ts | 4 | 0 |
| useWizardApi.test.ts | 13 | 0 |
| wizard.test.ts（store） | 7 | 0 |

### 4.2 vue-tsc 类型检查

```
0 type errors
```

---

## 五、代码审查发现的问题

### 5.1 需要修复的 Bug（3 个）

| # | 问题 | 位置 | 严重程度 | 影响 |
|---|------|------|----------|------|
| B1 | `safe_identifier()` 不支持中文列名 | `src/pipeforge/core/sqlite.py:9` | **Blocking** | 中文列名的 Excel/CSV 数据无法加载，8 个测试失败 |
| B2 | `deepdiff` 依赖未安装 | `configforge/api/configs.py:423` | **Blocking** | 版本对比 API 崩溃，1 个测试失败 |
| B3 | `sqlite3.Row` vs `tuple` 类型不匹配 | `src/pipeforge/core/sqlite.py:34` + 测试文件 | **Medium** | 4 个测试断言失败，不影响运行时功能 |

### 5.2 计划中要求但未实现的项（1 个）

| # | 问题 | 计划要求 | 当前状态 |
|---|------|----------|----------|
| M1 | 执行记录敏感数据脱敏 | Phase 3 要求连接字符串等敏感信息脱敏 | 未实现 |

### 5.3 已确认正确实现的设计项

| # | 设计要求 | 实现状态 |
|---|----------|----------|
| D1 | CustomSqlRule 使用 `comparison` + `result_column` + `expected_value` | 已实现 |
| D2 | 所有新 Rule 模型含 `model_config = ConfigDict(extra="forbid")` | 已实现 |
| D3 | SQLite 标识符使用双引号 `""` | 已实现 |
| D4 | UniquenessRule 加 `WHERE ... IS NOT NULL` | 已实现 |
| D5 | EnumCheckRule 超 900 枚举值拒绝执行 | 已实现 |
| D6 | DatabaseOutputPlugin 无 `_resolve_connection` | 已确认 |
| D7 | Wizard 层 `OutputTarget` 包含 `DatabaseOutputConfig` | 已实现 |
| D8 | 回滚采用追加式（方案 B） | 已实现 |
| D9 | ExecutionRecord 含 `config_version` 字段 | 已实现 |
| D10 | ExecutionRecord.status 仅 `success`/`failed` | 已实现 |
| D11 | 前端 CheckpointSection 动态规则类型表单 | 已实现 |
| D12 | 前端 DatabaseOutputConfig 类型定义 | 已实现 |

---

## 六、修复建议

### 优先级 P0（必须修复，阻塞核心功能）

**B1：`safe_identifier()` 支持中文列名**

修改 `src/pipeforge/core/sqlite.py` 第 9 行：
```python
# 当前
_SQL_ID_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")

# 修改为
_SQL_ID_RE = re.compile(r"^[\w][\w]{0,63}$")
```

Python 3 的 `\w` 匹配 `[a-zA-Z0-9_]` + Unicode 字母/数字，支持中文。仍能拦截 SQL 注入（特殊字符如 `;`、`'`、`"`、`-`、空格等不在 `\w` 范围内）。

**B2：安装 `deepdiff` 依赖**

```bash
uv add deepdiff
```

或在 `pyproject.toml` 的 `dependencies` 中添加 `deepdiff`。

### 优先级 P1（应修复，测试断言问题）

**B3：修复 `sqlite3.Row` vs `tuple` 测试断言**

4 个测试用例需要将 `Row` 对象转为 `tuple` 后比较：

- `tests/test_sqlite.py` 第 26 行：`assert [tuple(r) for r in rows] == [...]`
- `tests/test_sqlite.py` 第 45 行：`assert [tuple(r) for r in rows] == [...]`
- `tests/test_sql_processor.py` 第 41 行：`assert tuple(rows[0]) == ("1", "Alice")`
- `tests/test_sql_processor.py` 第 86 行：`assert tuple(rows[0]) == ("1", "Alice")`

### 优先级 P2（计划要求，建议补充）

**M1：执行记录敏感数据脱敏**

在 `configforge/api/configs.py` 的 `execute_config` 端点中，创建 `ExecutionRecord` 时对 `inputs_summary` 中的连接字符串进行脱敏处理。

---

## 七、测试环境信息

| 项目 | 版本/信息 |
|------|-----------|
| 操作系统 | macOS |
| Python | 3.13.3 |
| pytest | 9.0.3 |
| Node.js | (系统安装) |
| Vitest | 2.1.9 |
| vue-tsc | (项目依赖) |
| 测试运行时间 | 后端 1.24s + 前端 2.18s |
| 测试日期 | 2026-06-06 |
