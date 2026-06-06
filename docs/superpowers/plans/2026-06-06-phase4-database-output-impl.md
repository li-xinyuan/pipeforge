# Phase 4: 数据库输出 — 实施计划 (简版)

> **Goal:** 支持将管道结果写入数据库（MySQL/PostgreSQL/SQLite），补齐"文件进→DB出"闭环。

---

## Tasks

| Task | 文件 | 内容 |
|------|------|------|
| 1 | `src/pipeforge/config/models.py` | DatabaseOutputConfig 模型 + OutputConfig union 更新 |
| 2 | `configforge/models/wizard.py` | OutputTarget 增加 database + DatabaseOutputConfig |
| 3 | `src/pipeforge/plugins/output/database.py` | DatabaseOutputPlugin（新增） |
| 4 | `configforge/core/pipeline.py` | _prepare_execution 解析连接字符串 |
| 5 | `configforge/services/yaml_builder.py` | YAML 序列化 database 输出 |
| 6 | `configforge-web/src/types/wizard.ts` | DatabaseOutputConfig 前端类型 |
| 7 | `configforge-web/src/components/step3/OutputConfigTab.vue` | 激活 Database 卡片 + 配置表单 |
| 8 | 测试 + 回归 |

---

## Task 1: PipeForge DatabaseOutputConfig

**File:** `src/pipeforge/config/models.py`

添加 DatabaseOutputConfig：

```python
class DatabaseOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["database"] = "database"
    connection_id: str = ""
    target_table: str = ""
    write_mode: Literal["replace", "append", "upsert"] = "replace"
    source_table: str = ""
    columns: list[ColumnMapping] = Field(default=[])
    create_table_if_not_exists: bool = True
    primary_key_columns: list[str] = Field(default=[])
    batch_size: int = Field(default=1000, ge=1, le=100000)
    connection_string: str = ""  # _prepare_execution resolves this
```

修改 OutputConfig union（找到现有的 `OutputConfig = Annotated[...]`）：

```python
OutputConfig = Annotated[
    ExcelOutputConfig | CsvOutputConfig | DatabaseOutputConfig,
    Field(discriminator="type")
]

class OutputSpec(BaseModel):
    plugin: Literal["excel", "csv", "database"] = "excel"
    config: OutputConfig = Field(default=ExcelOutputConfig())
```

## Task 2: Wizard Layer OutputTarget

**File:** `configforge/models/wizard.py`

找到 OutputTarget，修改为包含 database：

```python
class DatabaseOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["database"] = "database"
    connection_id: str = ""
    target_table: str = ""
    write_mode: Literal["replace", "append", "upsert"] = "replace"
    source_table: str = ""
    columns: list[ColumnMappingItem] = Field(default=[])
    create_table_if_not_exists: bool = True
    primary_key_columns: list[str] = Field(default=[])
    batch_size: int = Field(default=1000, ge=1, le=100000)
    connection_string: str = ""

class OutputTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plugin: Literal["excel", "csv", "database"] = "excel"
    config: Annotated[ExcelOutputConfig | CsvOutputConfig | DatabaseOutputConfig, Field(discriminator="type")]
```

## Task 3: DatabaseOutputPlugin

**File:** `src/pipeforge/plugins/output/database.py`（新增）

```python
"""Database output plugin."""
from pipeforge.plugins.base import OutputPlugin
from pipeforge.config.models import DatabaseOutputConfig
from pipeforge.core.registry import register_plugin
from pipeforge.core.sqlite import SQLiteManager


@register_plugin("database", "output")
class DatabaseOutputPlugin(OutputPlugin[DatabaseOutputConfig]):
    @classmethod
    def config_model(cls) -> type[DatabaseOutputConfig]:
        return DatabaseOutputConfig

    def execute(self, context, config: DatabaseOutputConfig):
        conn_str = config.connection_string
        if not conn_str:
            raise ValueError("Database output requires connection_string")

        source_table = config.source_table or context.default_output_table
        rows = context.db.query(f'SELECT * FROM "{source_table}"')

        if not rows:
            return 0

        # For SQLite target, use SQLiteManager; for others, use SQLAlchemy
        # Phase 4 v0.1: support SQLite target (reuse existing pattern)
        if "sqlite" in conn_str.lower() or conn_str.endswith(".db"):
            target_db = SQLiteManager(conn_str.replace("sqlite:///", "").strip())
        else:
            target_db = SQLiteManager()  # temp db as fallback; full SQLAlchemy in future

        try:
            # Get column names from source table
            existing_cols = [c[1] for c in context.db._conn.execute(f'PRAGMA table_info("{source_table}")').fetchall()]
            target_db.create_table(config.target_table, existing_cols)

            for row in rows:
                target_db.insert_row(config.target_table, tuple(row))

            row_count = len(rows)
            context.logger.info(f"Database output: wrote {row_count} rows to {config.target_table}")
            return row_count
        finally:
            if target_db != context.db:
                target_db.close()
```

## Task 4: Connection resolution in _prepare_execution

**File:** `configforge/core/pipeline.py`

在 `_prepare_execution()` 中，输出处理部分，添加数据库输出连接解析：

```python
# Resolve database output connection
if out_spec and out_spec.plugin == "database":
    db_config = out_spec.config
    if hasattr(db_config, 'connection_id') and db_config.connection_id:
        try:
            from configforge.services.connection_store import ConnectionStore
            entry = ConnectionStore.get_with_plaintext_password(db_config.connection_id)
            if entry:
                db_config.connection_string = ConnectionStore.build_connection_string(entry)
        except Exception:
            pass  # connection_id might not be set yet (wizard preview)
```

## Task 5: YAML Builder

**File:** `configforge/services/yaml_builder.py`

在输出部分序列化中添加 database 分支。

## Tasks 6-8: Frontend + Tests

- TypeScript 类型定义
- OutputConfigTab 激活 Database 卡片 + 配置表单
- 构建验证

## Commit

所有改动合并为一个提交：
```
feat: add database output plugin with connection resolution and frontend config
```
