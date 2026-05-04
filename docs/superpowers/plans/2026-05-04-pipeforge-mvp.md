# PipeForge v0.1 MVP 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 PipeForge v0.1 MVP——一个基于 YAML 配置 + SQLite + openpyxl 的 CLI 数据流水线工具。

**Architecture:** 三段式管道（Input → SQLite → SQL Processor → Output），策略模式插件体系（泛型基类 + 注册中心 + 装饰器），CLI-引擎职责分离。所有模块遵循 TDD 开发。

**Tech Stack:** Python 3.10+, Pydantic v2, PyYAML, openpyxl, sqlite3 (内置), click

**Specs:**
- 高阶设计: `DESIGN_v7.md`
- 详细设计: `DETAILED_DESIGN_v2.md`

---

### 文件结构映射

| # | 文件 | 职责 |
|---|------|------|
| 1 | `pyproject.toml` | 项目元数据 + 依赖声明 |
| 2 | `src/pipeforge/plugins/base.py` | Plugin 泛型基类 + InputPlugin/ProcessorPlugin/OutputPlugin 子类 |
| 3 | `src/pipeforge/core/registry.py` | PluginRegistry + register_plugin 装饰器 |
| 4 | `src/pipeforge/config/models.py` | 11 个 Pydantic 配置模型，`extra="forbid"` |
| 5 | `src/pipeforge/core/sqlite.py` | SQLiteManager — 建表/写入/事务/查询 |
| 6 | `src/pipeforge/core/context.py` | Context + ExecutionResult + Stats + Logger |
| 7 | `src/pipeforge/config/__init__.py` | YAML 加载 + 表名冲突检测 + 模板列校验 + 路径解析 |
| 8 | `src/pipeforge/core/engine.py` | PipelineEngine — load_config → required_params → execute |
| 9 | `src/pipeforge/plugins/input/__init__.py` | 显式 import ExcelInputPlugin |
| 10 | `src/pipeforge/plugins/input/excel.py` | Excel 输入插件 + read_excel_rows |
| 11 | `src/pipeforge/plugins/processor/__init__.py` | 显式 import SqlProcessorPlugin |
| 12 | `src/pipeforge/plugins/processor/sql.py` | SQL 处理插件 |
| 13 | `src/pipeforge/plugins/output/__init__.py` | 显式 import ExcelOutputPlugin |
| 14 | `src/pipeforge/plugins/output/excel.py` | Excel 输出插件 + 三阶段写入 + 文件名解析 |
| 15 | `src/pipeforge/cli.py` | CLI 入口 + run 命令 + 错误格式化 |
| 16 | `src/pipeforge/__init__.py` | 顶级导入 |
| 17 | `src/pipeforge/utils/__init__.py` | 辅助函数 |
| 18 | `tests/conftest.py` | 共享 fixtures |
| 19 | `tests/test_*.py` | 10 个测试文件 |

---

### Task 1: 项目骨架 + 依赖声明

**Files:**
- Create: `pyproject.toml`
- Create: `src/pipeforge/__init__.py`
- Create: `src/pipeforge/utils/__init__.py`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pipeforge"
version = "0.1.0"
description = "CLI data pipeline framework — YAML config + SQLite + openpyxl"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "openpyxl>=3.1",
    "click>=8.0",
]

[project.scripts]
pipeforge = "pipeforge.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-mock>=3.0",
]

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: 创建 __init__.py 文件**

```python
# src/pipeforge/__init__.py
"""PipeForge — CLI data pipeline framework."""

__version__ = "0.1.0"
```

```python
# src/pipeforge/utils/__init__.py
"""Utility functions for PipeForge."""
```

- [ ] **Step 3: 安装项目**

Run: `pip install -e ".[dev]"`
Expected: Successfully installed pipeforge

- [ ] **Step 4: 验证安装**

Run: `python -c "import pipeforge; print(pipeforge.__version__)"`
Expected: `0.1.0`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/pipeforge/__init__.py src/pipeforge/utils/__init__.py
git commit -m "feat: add project skeleton with pyproject.toml"
```

---

### Task 2: 插件基类

**Files:**
- Create: `tests/test_plugins_base.py`
- Create: `src/pipeforge/plugins/__init__.py`
- Create: `src/pipeforge/plugins/base.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_plugins_base.py
import pytest
from pydantic import BaseModel

from pipeforge.plugins.base import Plugin, InputPlugin, ProcessorPlugin, OutputPlugin


class FakeConfig(BaseModel):
    value: str


class FakeInputPlugin(InputPlugin):
    @classmethod
    def config_model(cls) -> type[FakeConfig]:
        return FakeConfig

    def execute(self, context, config: FakeConfig) -> None:
        pass


class TestPluginBase:
    def test_plugin_has_name_attribute(self):
        plugin = FakeInputPlugin()
        plugin.name = "test_plugin"
        assert plugin.name == "test_plugin"

    def test_plugin_has_label_attribute(self):
        plugin = FakeInputPlugin()
        plugin.label = "Test Label"
        assert plugin.label == "Test Label"

    def test_input_plugin_has_table_name(self):
        plugin = FakeInputPlugin()
        plugin.table_name = "my_table"
        assert plugin.table_name == "my_table"

    def test_config_model_returns_correct_type(self):
        assert FakeInputPlugin.config_model() == FakeConfig

    def test_cannot_instantiate_abstract_plugin(self):
        with pytest.raises(TypeError):
            Plugin()  # type: ignore

    def test_cannot_instantiate_without_execute(self):
        class BadPlugin(InputPlugin):
            @classmethod
            def config_model(cls) -> type[FakeConfig]:
                return FakeConfig

        with pytest.raises(TypeError):
            BadPlugin()  # type: ignore
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_plugins_base.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现插件基类**

```python
# src/pipeforge/plugins/__init__.py
"""PipeForge plugin system."""
```

```python
# src/pipeforge/plugins/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

C = TypeVar("C", bound=BaseModel)


class Plugin(ABC, Generic[C]):
    """所有插件的抽象基类。name 和 label 由引擎实例化后注入。"""

    @classmethod
    @abstractmethod
    def config_model(cls) -> type[C]:
        """返回该插件的配置 Pydantic 模型。"""
        ...

    @abstractmethod
    def execute(self, context: "Context", config: C) -> None:
        """执行插件逻辑。"""
        ...


class InputPlugin(Plugin[C], ABC):
    """输入插件基类 — table_name 由引擎注入。"""


class ProcessorPlugin(Plugin[C], ABC):
    """处理插件基类 — MVP 与 Plugin 相同，预留扩展。"""


class OutputPlugin(Plugin[C], ABC):
    """输出插件基类 — MVP 与 Plugin 相同，预留扩展。"""
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_plugins_base.py -v`
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_plugins_base.py src/pipeforge/plugins/__init__.py src/pipeforge/plugins/base.py
git commit -m "feat: add plugin abstract base classes with generics"
```

---

### Task 3: 插件注册中心

**Files:**
- Create: `tests/test_registry.py`
- Create: `src/pipeforge/core/__init__.py`
- Create: `src/pipeforge/core/registry.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_registry.py
import pytest
from pydantic import BaseModel

from pipeforge.plugins.base import InputPlugin, ProcessorPlugin, OutputPlugin
from pipeforge.core.registry import PluginRegistry, register_plugin, PluginNotFoundError


class FakeConfig(BaseModel):
    pass


class TestPluginRegistry:
    def test_register_and_get(self):
        @register_plugin("test_excel", "input")
        class TestExcelInput(InputPlugin):
            @classmethod
            def config_model(cls) -> type[FakeConfig]:
                return FakeConfig

            def execute(self, context, config: FakeConfig) -> None:
                pass

        cls = PluginRegistry.get("test_excel", "input")
        assert cls == TestExcelInput

    def test_get_nonexistent_plugin_raises(self):
        with pytest.raises(PluginNotFoundError) as exc:
            PluginRegistry.get("nonexistent", "input")
        assert "nonexistent" in str(exc.value)

    def test_register_duplicate_overwrites(self):
        @register_plugin("dup_plugin", "output")
        class FirstOutput(OutputPlugin):
            @classmethod
            def config_model(cls) -> type[FakeConfig]:
                return FakeConfig

            def execute(self, context, config: FakeConfig) -> None:
                pass

        @register_plugin("dup_plugin", "output")
        class SecondOutput(OutputPlugin):
            @classmethod
            def config_model(cls) -> type[FakeConfig]:
                return FakeConfig

            def execute(self, context, config: FakeConfig) -> None:
                pass

        cls = PluginRegistry.get("dup_plugin", "output")
        assert cls == SecondOutput

    def test_list_by_type(self):
        @register_plugin("list_test", "processor")
        class ListTestProc(ProcessorPlugin):
            @classmethod
            def config_model(cls) -> type[FakeConfig]:
                return FakeConfig

            def execute(self, context, config: FakeConfig) -> None:
                pass

        plugins = PluginRegistry.list_by_type("processor")
        assert "list_test" in plugins
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_registry.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现注册中心**

```python
# src/pipeforge/core/__init__.py
"""PipeForge core engine components."""
```

```python
# src/pipeforge/core/registry.py
from typing import Type

from pipeforge.plugins.base import Plugin


class PluginNotFoundError(Exception):
    """请求的插件未在注册中心中找到。"""
    def __init__(self, name: str, plugin_type: str):
        self.name = name
        self.plugin_type = plugin_type
        super().__init__(f"Plugin '{name}' of type '{plugin_type}' not found in registry")


class PluginRegistry:
    """全局插件注册中心。插件通过 @register_plugin 装饰器注册。"""

    _plugins: dict[tuple[str, str], Type[Plugin]] = {}

    @classmethod
    def register(cls, name: str, plugin_type: str, plugin_cls: Type[Plugin]) -> None:
        cls._plugins[(name, plugin_type)] = plugin_cls

    @classmethod
    def get(cls, name: str, plugin_type: str) -> Type[Plugin]:
        key = (name, plugin_type)
        if key not in cls._plugins:
            raise PluginNotFoundError(name, plugin_type)
        return cls._plugins[key]

    @classmethod
    def list_by_type(cls, plugin_type: str) -> list[str]:
        return [name for (name, ptype) in cls._plugins if ptype == plugin_type]

    @classmethod
    def clear(cls) -> None:
        """清空注册中心（仅供测试使用）。"""
        cls._plugins.clear()


def register_plugin(name: str, plugin_type: str):
    """注册插件到全局注册中心的装饰器。"""
    def decorator(cls: Type[Plugin]) -> Type[Plugin]:
        PluginRegistry.register(name, plugin_type, cls)
        return cls
    return decorator
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_registry.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_registry.py src/pipeforge/core/__init__.py src/pipeforge/core/registry.py
git commit -m "feat: add PluginRegistry with register_plugin decorator"
```

---

### Task 4: Pydantic 配置模型

**Files:**
- Create: `tests/test_config_models.py`
- Create: `src/pipeforge/config/models.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_config_models.py
import pytest
from pydantic import ValidationError

from pipeforge.config.models import (
    SceneMeta,
    ExcelInputConfig,
    InputSpec,
    SqlProcessorConfig,
    ProcessorSpec,
    ColumnMapping,
    ExcelOutputConfig,
    OutputSpec,
    SceneConfig,
)


class TestSceneMeta:
    def test_valid_scene_meta(self):
        meta = SceneMeta(name="人员月报", description="测试场景", version="1.0")
        assert meta.name == "人员月报"
        assert meta.version == "1.0"

    def test_missing_required_name_raises(self):
        with pytest.raises(ValidationError):
            SceneMeta(description="test", version="1.0")

    def test_extra_field_forbidden(self):
        with pytest.raises(ValidationError):
            SceneMeta(name="test", description="test", version="1.0", unknown="bad")


class TestInputSpec:
    def test_valid_input_spec(self):
        spec = InputSpec(
            name="人员明细",
            plugin="excel",
            table="person_detail",
            param_key="person_file",
            config=ExcelInputConfig(sheet="人员列表"),
        )
        assert spec.config.sheet == "人员列表"

    def test_invalid_plugin_name_still_allowed_by_model(self):
        spec = InputSpec(
            name="test",
            plugin="nonexistent",
            table="t",
            param_key="p",
            config=ExcelInputConfig(sheet="s"),
        )
        assert spec.plugin == "nonexistent"


class TestProcessorSpec:
    def test_valid_processor_spec(self):
        spec = ProcessorSpec(
            name="数据合并",
            plugin="sql",
            output_tables=["report_data"],
            config=SqlProcessorConfig(sql="SELECT 1"),
        )
        assert spec.output_tables == ["report_data"]

    def test_empty_output_tables(self):
        spec = ProcessorSpec(
            name="test",
            plugin="sql",
            output_tables=[],
            config=SqlProcessorConfig(sql="SELECT 1"),
        )
        assert spec.output_tables == []


class TestColumnMapping:
    def test_valid_column_mapping(self):
        cm = ColumnMapping(source="姓名", target="员工姓名")
        assert cm.source == "姓名"
        assert cm.target == "员工姓名"

    def test_empty_source_raises(self):
        with pytest.raises(ValidationError):
            ColumnMapping(source="", target="姓名")


class TestSceneConfig:
    def test_full_valid_config(self):
        config = SceneConfig(
            scene=SceneMeta(name="人员月报", description="测试", version="1.0"),
            inputs=[
                InputSpec(
                    name="人员明细",
                    plugin="excel",
                    table="person_detail",
                    param_key="person_file",
                    config=ExcelInputConfig(sheet="人员列表"),
                )
            ],
            processors=[
                ProcessorSpec(
                    name="数据合并",
                    plugin="sql",
                    output_tables=["report_data"],
                    config=SqlProcessorConfig(sql="CREATE TABLE report_data AS SELECT * FROM person_detail"),
                )
            ],
            output=OutputSpec(
                plugin="excel",
                config=ExcelOutputConfig(
                    template="templates/report.xlsx",
                    sheet="报表",
                    source_table="report_data",
                    columns=[ColumnMapping(source="姓名", target="姓名")],
                ),
            ),
        )
        assert config.scene.name == "人员月报"

    def test_empty_inputs_is_valid(self):
        config = SceneConfig(
            scene=SceneMeta(name="test", description="test", version="1.0"),
            inputs=[],
            processors=[
                ProcessorSpec(
                    name="gen",
                    plugin="sql",
                    output_tables=["data"],
                    config=SqlProcessorConfig(sql="CREATE TABLE data AS SELECT 1 AS x"),
                )
            ],
        )
        assert len(config.inputs) == 0

    def test_empty_columns_raises(self):
        with pytest.raises(ValidationError):
            ExcelOutputConfig(
                template="t.xlsx",
                source_table="t",
                columns=[],
            )
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_config_models.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现配置模型**

```python
# src/pipeforge/config/models.py
from pydantic import BaseModel, ConfigDict, field_validator


class SceneMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    version: str = "1.0"


class ExcelInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str | None = None
    sheet: str = "Sheet1"


class InputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    plugin: str
    table: str
    param_key: str
    config: ExcelInputConfig


class SqlProcessorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sql: str


class ProcessorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    plugin: str
    output_tables: list[str] = []
    config: SqlProcessorConfig


class ColumnMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    target: str

    @field_validator("source")
    @classmethod
    def source_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source column name must not be empty")
        return v


class ExcelOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template: str
    sheet: str = "Sheet1"
    output_dir: str = "./output/"
    source_table: str
    filename: str | None = None
    columns: list[ColumnMapping]

    @field_validator("columns")
    @classmethod
    def columns_not_empty(cls, v: list[ColumnMapping]) -> list[ColumnMapping]:
        if len(v) == 0:
            raise ValueError("columns must not be empty — at least one column mapping is required")
        return v


class OutputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin: str
    config: ExcelOutputConfig


class SceneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene: SceneMeta
    inputs: list[InputSpec] = []
    processors: list[ProcessorSpec] = []
    output: OutputSpec | None = None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_config_models.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_config_models.py src/pipeforge/config/models.py
git commit -m "feat: add Pydantic config models with extra=forbid"
```

---

### Task 5: SQLite 管理器

**Files:**
- Create: `tests/test_sqlite.py`
- Create: `src/pipeforge/core/sqlite.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_sqlite.py
import sqlite3
import os

import pytest

from pipeforge.core.sqlite import SQLiteManager


class TestSQLiteManager:
    @pytest.fixture
    def db(self):
        manager = SQLiteManager()
        yield manager
        manager.close()

    def test_create_table(self, db):
        db.create_table("users", ["id", "name", "age"])
        tables = db.list_tables()
        assert "users" in tables

    def test_insert_and_query(self, db):
        db.create_table("users", ["id", "name"])
        with db.transaction():
            db.insert_row("users", ("1", "Alice"))
            db.insert_row("users", ("2", "Bob"))
        rows = db.query("SELECT * FROM users ORDER BY id")
        assert rows == [("1", "Alice"), ("2", "Bob")]

    def test_transaction_rollback(self, db):
        db.create_table("users", ["id", "name"])
        try:
            with db.transaction():
                db.insert_row("users", ("1", "Alice"))
                raise RuntimeError("forced error")
        except RuntimeError:
            pass
        rows = db.query("SELECT * FROM users")
        assert len(rows) == 0

    def test_execute_returning_rows(self, db):
        db.create_table("users", ["id", "name"])
        with db.transaction():
            db.insert_row("users", ("1", "Alice"))
        db.execute("CREATE TABLE copy AS SELECT * FROM users")
        rows = db.query("SELECT * FROM copy")
        assert rows == [("1", "Alice")]

    def test_table_exists(self, db):
        db.create_table("users", ["id"])
        assert db.table_exists("users") is True
        assert db.table_exists("nonexistent") is False

    def test_db_file_exists(self, db):
        assert os.path.exists(db.path)

    def test_close_and_remove(self, db):
        path = db.path
        assert os.path.exists(path)
        db.close()
        db.remove()
        assert not os.path.exists(path)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_sqlite.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 SQLite 管理器**

```python
# src/pipeforge/core/sqlite.py
import sqlite3
import tempfile
import os
from contextlib import contextmanager


class SQLiteManager:
    """管理 SQLite 临时数据库的创建、写入、查询和清理。"""

    def __init__(self):
        fd, self.path = tempfile.mkstemp(suffix=".db", prefix="pipeforge_")
        os.close(fd)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("PRAGMA journal_mode=WAL")

    def create_table(self, table_name: str, columns: list[str]) -> None:
        cols_def = ", ".join(f'"{c}" TEXT' for c in columns)
        self._conn.execute(f'CREATE TABLE "{table_name}" ({cols_def})')
        self._conn.commit()

    def insert_row(self, table_name: str, row: tuple) -> None:
        placeholders = ", ".join("?" for _ in row)
        self._conn.execute(
            f'INSERT INTO "{table_name}" VALUES ({placeholders})', row
        )

    def query(self, sql: str) -> list[tuple]:
        return self._conn.execute(sql).fetchall()

    def execute(self, sql: str) -> None:
        self._conn.executescript(sql)
        self._conn.commit()

    @contextmanager
    def transaction(self):
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def list_tables(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]

    def table_exists(self, table_name: str) -> bool:
        return table_name in self.list_tables()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def remove(self) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_sqlite.py -v`
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_sqlite.py src/pipeforge/core/sqlite.py
git commit -m "feat: add SQLiteManager with transaction support"
```

---

### Task 6: 执行上下文

**Files:**
- Create: `tests/test_context.py`
- Create: `src/pipeforge/core/context.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_context.py
from pipeforge.core.context import Context, ExecutionResult, InputStats, ProcessorStats, OutputStats, Logger


class TestContext:
    def test_context_creation(self):
        ctx = Context(
            db=None,  # type: ignore
            params={"person_file": "/tmp/test.xlsx"},
            yaml_dir="/pipelines",
            scene_name="人员月报",
        )
        assert ctx.params["person_file"] == "/tmp/test.xlsx"
        assert ctx.yaml_dir == "/pipelines"
        assert ctx.scene_name == "人员月报"
        assert isinstance(ctx.result, ExecutionResult)
        assert isinstance(ctx.logger, Logger)

    def test_context_output_path_default(self):
        ctx = Context(
            db=None,  # type: ignore
            params={},
            yaml_dir="/pipelines",
            scene_name="人员月报",
        )
        assert ctx.output_path is None


class TestExecutionResult:
    def test_result_initial_state(self):
        result = ExecutionResult()
        assert result.inputs == {}
        assert result.processors == []
        assert result.output is None

    def test_result_record_input(self):
        result = ExecutionResult()
        result.inputs["person"] = InputStats(name="人员明细", rows_loaded=100, elapsed_ms=1500.0)
        assert result.inputs["person"].rows_loaded == 100


class TestLogger:
    def test_logger_info(self):
        logger = Logger()
        logger.info("hello")
        assert len(logger.messages) == 1
        assert logger.messages[0]["level"] == "INFO"

    def test_logger_error(self):
        logger = Logger()
        logger.error("fail")
        assert logger.messages[0]["level"] == "ERROR"

    def test_logger_verbose_flag_off(self):
        logger = Logger(verbose=False)
        logger.debug("hidden")
        assert len(logger.messages) == 0

    def test_logger_verbose_flag_on(self):
        logger = Logger(verbose=True)
        logger.debug("shown")
        assert len(logger.messages) == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_context.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 Context**

```python
# src/pipeforge/core/context.py
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


class InputStats(BaseModel):
    name: str
    rows_loaded: int
    elapsed_ms: float


class ProcessorStats(BaseModel):
    name: str
    tables_created: list[str]
    elapsed_ms: float


class OutputStats(BaseModel):
    rows_written: int
    file_path: str
    elapsed_ms: float


class ExecutionResult(BaseModel):
    inputs: dict[str, InputStats] = {}
    processors: list[ProcessorStats] = []
    output: OutputStats | None = None


@dataclass
class Logger:
    verbose: bool = False
    messages: list[dict[str, Any]] = field(default_factory=list)

    def info(self, msg: str) -> None:
        self.messages.append({"level": "INFO", "message": msg})

    def error(self, msg: str) -> None:
        self.messages.append({"level": "ERROR", "message": msg})

    def debug(self, msg: str) -> None:
        if self.verbose:
            self.messages.append({"level": "DEBUG", "message": msg})


@dataclass
class Context:
    db: "SQLiteManager"
    params: dict[str, str]
    yaml_dir: str
    scene_name: str
    output_path: str | None = None
    logger: Logger = field(default_factory=Logger)
    result: ExecutionResult = field(default_factory=ExecutionResult)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_context.py -v`
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_context.py src/pipeforge/core/context.py
git commit -m "feat: add Context, ExecutionResult, Stats, and Logger"
```

---

### Task 7: 配置加载器

**Files:**
- Create: `tests/test_config_loader.py`
- Create: `src/pipeforge/config/__init__.py`
- Create: `src/pipeforge/config/exceptions.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_config_loader.py
import tempfile
import os

import pytest

from pipeforge.config.models import SceneConfig
from pipeforge.config import load_yaml_config, ConfigError


class TestLoadYamlConfig:
    def test_load_valid_config(self):
        yaml_content = """
scene:
  name: 人员月报
  description: 测试
  version: "1.0"

inputs:
  - name: 人员明细
    plugin: excel
    table: person_detail
    param_key: person_file
    config:
      sheet: 人员列表

processors:
  - name: 数据合并
    plugin: sql
    output_tables:
      - report_data
    config:
      sql: CREATE TABLE report_data AS SELECT * FROM person_detail

output:
  plugin: excel
  config:
    template: templates/report.xlsx
    sheet: 报表
    source_table: report_data
    columns:
      - source: 姓名
        target: 姓名
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name

        try:
            config = load_yaml_config(path)
            assert isinstance(config, SceneConfig)
            assert config.scene.name == "人员月报"
        finally:
            os.unlink(path)

    def test_duplicate_table_names_detected(self):
        yaml_content = """
scene:
  name: test
  description: test
  version: "1.0"

inputs:
  - name: Input A
    plugin: excel
    table: same_table
    param_key: file_a
    config:
      sheet: Sheet1
  - name: Input B
    plugin: excel
    table: same_table
    param_key: file_b
    config:
      sheet: Sheet1

processors:
  - name: proc
    plugin: sql
    output_tables:
      - report
    config:
      sql: SELECT 1
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name

        try:
            with pytest.raises(ConfigError, match="same_table"):
                load_yaml_config(path)
        finally:
            os.unlink(path)

    def test_duplicate_param_key_detected(self):
        yaml_content = """
scene:
  name: test
  description: test
  version: "1.0"

inputs:
  - name: Input A
    plugin: excel
    table: table_a
    param_key: same_key
    config:
      sheet: Sheet1
  - name: Input B
    plugin: excel
    table: table_b
    param_key: same_key
    config:
      sheet: Sheet1

processors:
  - name: proc
    plugin: sql
    output_tables:
      - report
    config:
      sql: SELECT 1
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name

        try:
            with pytest.raises(ConfigError, match="same_key"):
                load_yaml_config(path)
        finally:
            os.unlink(path)

    def test_source_table_not_declared_in_output_tables(self):
        yaml_content = """
scene:
  name: test
  description: test
  version: "1.0"

inputs:
  - name: inp
    plugin: excel
    table: my_table
    param_key: file_key
    config:
      sheet: Sheet1

processors:
  - name: proc
    plugin: sql
    output_tables:
      - declared_table
    config:
      sql: SELECT 1

output:
  plugin: excel
  config:
    template: t.xlsx
    source_table: undeclared_table
    columns:
      - source: x
        target: y
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name

        try:
            with pytest.raises(ConfigError, match="undeclared_table"):
                load_yaml_config(path)
        finally:
            os.unlink(path)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_config_loader.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现配置加载器**

```python
# src/pipeforge/config/exceptions.py
class ConfigError(Exception):
    """配置加载或校验阶段的错误。"""
    pass
```

```python
# src/pipeforge/config/__init__.py
from pathlib import Path
from typing import Any

import yaml

from pipeforge.config.exceptions import ConfigError
from pipeforge.config.models import SceneConfig


def load_yaml_config(yaml_path: str) -> SceneConfig:
    """加载并校验 YAML 配置文件。"""
    path = Path(yaml_path)
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {yaml_path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ConfigError(f"Configuration file is empty: {yaml_path}")

    config = SceneConfig(**raw)

    _validate_table_names(config)
    _validate_param_keys(config)
    _validate_source_table(config)

    return config


def _validate_table_names(config: SceneConfig) -> None:
    """检测表名冲突：inputs[].table 互不相同，且不与 output_tables 冲突。"""
    seen = {}

    for inp in config.inputs:
        if inp.table in seen:
            raise ConfigError(
                f"Table name '{inp.table}' is used by both "
                f"inputs[name={seen[inp.table]}] and inputs[name={inp.name}]"
            )
        seen[inp.table] = inp.name

    for proc in config.processors:
        for ot in proc.output_tables:
            if ot in seen:
                raise ConfigError(
                    f"Output table '{ot}' conflicts with input table "
                    f"'{ot}' (inputs[name={seen[ot]}])"
                )
            seen[ot] = proc.name


def _validate_param_keys(config: SceneConfig) -> None:
    """检测 param_key 重复。"""
    seen = {}
    for inp in config.inputs:
        if inp.param_key in seen:
            raise ConfigError(
                f"param_key '{inp.param_key}' is used by both "
                f"inputs[name={seen[inp.param_key]}] and inputs[name={inp.name}]"
            )
        seen[inp.param_key] = inp.name


def _validate_source_table(config: SceneConfig) -> None:
    """检测 output.source_table 是否在某个 processor 的 output_tables 中声明。"""
    if config.output is None:
        return

    source_table = config.output.config.source_table
    declared = set()
    for proc in config.processors:
        declared.update(proc.output_tables)

    if source_table not in declared:
        raise ConfigError(
            f"Output source_table '{source_table}' is not declared in any "
            f"processor's output_tables. Declared tables: {sorted(declared)}"
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_config_loader.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_config_loader.py src/pipeforge/config/__init__.py src/pipeforge/config/exceptions.py
git commit -m "feat: add YAML config loader with table name conflict detection"
```

---

### Task 8: Pipeline 引擎

**Files:**
- Create: `tests/test_engine.py`
- Create: `src/pipeforge/core/engine.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_engine.py
import tempfile
import os

import pytest

from pipeforge.core.engine import PipelineEngine, RequiredParam


YAML_FIXTURE = """
scene:
  name: 测试场景
  description: 引擎单元测试
  version: "1.0"

inputs:
  - name: 输入A
    plugin: excel
    table: source_a
    param_key: file_a
    config:
      sheet: Sheet1

processors:
  - name: 处理A
    plugin: sql
    output_tables:
      - result_a
    config:
      sql: CREATE TABLE result_a AS SELECT 1 AS x

output:
  plugin: excel
  config:
    template: templates/report.xlsx
    sheet: 报表
    source_table: result_a
    columns:
      - source: x
        target: x
"""


@pytest.fixture
def yaml_path():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(YAML_FIXTURE)
        path = f.name
    yield path
    os.unlink(path)


class TestPipelineEngine:
    def test_load_config(self, yaml_path):
        engine = PipelineEngine(yaml_path)
        config = engine.config
        assert config.scene.name == "测试场景"

    def test_required_params(self, yaml_path):
        engine = PipelineEngine(yaml_path)
        params = engine.required_params()
        assert len(params) == 1
        assert params[0].key == "file_a"
        assert params[0].label == "输入A"

    def test_missing_params_raises(self, yaml_path):
        engine = PipelineEngine(yaml_path)
        with pytest.raises(ValueError, match="file_a"):
            engine.execute(params={})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_engine.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现引擎**

```python
# src/pipeforge/core/engine.py
from pathlib import Path

from pydantic import BaseModel

from pipeforge.config import load_yaml_config
from pipeforge.config.models import SceneConfig
from pipeforge.core.context import Context, InputStats, ProcessorStats, OutputStats
from pipeforge.core.registry import PluginRegistry
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.plugins.base import InputPlugin


class RequiredParam(BaseModel):
    key: str
    label: str
    description: str = ""


class PipelineEngine:
    """PipeForge 流水线引擎。"""

    def __init__(self, yaml_path: str):
        self._yaml_path = yaml_path
        self._yaml_dir = str(Path(yaml_path).parent.resolve())
        self.config: SceneConfig = load_yaml_config(yaml_path)

    def required_params(self) -> list[RequiredParam]:
        """返回流水线所需的运行时参数列表。"""
        return [
            RequiredParam(key=inp.param_key, label=inp.name)
            for inp in self.config.inputs
        ]

    def execute(self, params: dict[str, str], cleanup: bool = False) -> "ExecutionResult":
        """执行流水线。"""
        _validate_params(self.required_params(), params)

        db = SQLiteManager()
        context = Context(
            db=db,
            params=params,
            yaml_dir=self._yaml_dir,
            scene_name=self.config.scene.name,
        )

        try:
            for inp_spec in self.config.inputs:
                stats = self._execute_input(inp_spec, context)
                context.result.inputs[inp_spec.name] = stats

            for proc_spec in self.config.processors[:1]:
                stats = self._execute_processor(proc_spec, context)
                context.result.processors.append(stats)

            if self.config.output is not None:
                stats = self._execute_output(self.config.output, context)
                context.result.output = stats

        except Exception:
            context.logger.error(f"Temporary database preserved at: {db.path}")
            raise
        finally:
            if cleanup:
                db.close()
                db.remove()
            else:
                db.close()

        return context.result

    def _execute_input(self, inp_spec, context):
        import time
        start = time.time()
        plugin_cls = PluginRegistry.get(inp_spec.plugin, "input")
        plugin = plugin_cls()
        plugin.name = inp_spec.plugin
        plugin.label = inp_spec.name
        plugin.table_name = inp_spec.table
        config = inp_spec.config
        config.file = context.params[inp_spec.param_key]
        plugin.execute(context, config)
        elapsed = (time.time() - start) * 1000
        rows = context.db.query(f'SELECT COUNT(*) FROM "{inp_spec.table}"')
        return InputStats(
            name=inp_spec.name,
            rows_loaded=rows[0][0],
            elapsed_ms=round(elapsed, 2),
        )

    def _execute_processor(self, proc_spec, context):
        import time
        start = time.time()
        before_tables = set(context.db.list_tables())
        plugin_cls = PluginRegistry.get(proc_spec.plugin, "processor")
        plugin = plugin_cls()
        plugin.name = proc_spec.plugin
        plugin.label = proc_spec.name
        plugin.execute(context, proc_spec.config)
        elapsed = (time.time() - start) * 1000
        after_tables = set(context.db.list_tables())
        created = sorted(after_tables - before_tables)
        return ProcessorStats(
            name=proc_spec.name,
            tables_created=created,
            elapsed_ms=round(elapsed, 2),
        )

    def _execute_output(self, out_spec, context):
        import time
        start = time.time()
        plugin_cls = PluginRegistry.get(out_spec.plugin, "output")
        plugin = plugin_cls()
        plugin.name = out_spec.plugin
        plugin.execute(context, out_spec.config)
        elapsed = (time.time() - start) * 1000
        rows = context.db.query(f'SELECT COUNT(*) FROM "{out_spec.config.source_table}"')
        return OutputStats(
            rows_written=rows[0][0],
            file_path=context.output_path or "",
            elapsed_ms=round(elapsed, 2),
        )


def _validate_params(required: list[RequiredParam], provided: dict[str, str]) -> None:
    missing = [p.key for p in required if p.key not in provided]
    if missing:
        raise ValueError(
            f"Missing required parameters: {', '.join(missing)}. "
            f"Use --param key=value to provide them."
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_engine.py -v`
Expected: 3 tests PASS (load_config, required_params, missing_params_raises; execute will fail without plugins)

- [ ] **Step 5: Commit**

```bash
git add tests/test_engine.py src/pipeforge/core/engine.py
git commit -m "feat: add PipelineEngine with config loading and param injection"
```

---

### Task 9: Excel 输入插件

**Files:**
- Create: `tests/test_excel_input.py`
- Create: `src/pipeforge/plugins/input/__init__.py`
- Create: `src/pipeforge/plugins/input/excel.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_excel_input.py
import tempfile
import os

import pytest
from openpyxl import Workbook

from pipeforge.plugins.input.excel import ExcelInputPlugin, read_excel_rows
from pipeforge.plugins.input import ExcelInputPlugin as ImportedPlugin
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.core.context import Context
from pipeforge.config.models import ExcelInputConfig


@pytest.fixture
def sample_xlsx():
    """创建一个简单的测试 Excel 文件。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "人员列表"
    ws.append(["姓名", "部门", "年龄"])
    ws.append(["张三", "技术部", "30"])
    ws.append(["李四", "产品部", "28"])

    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    yield path
    os.unlink(path)


class TestReadExcelRows:
    def test_read_excel_rows(self, sample_xlsx):
        columns, rows = read_excel_rows(sample_xlsx, "人员列表")
        assert columns == ["姓名", "部门", "年龄"]
        data = list(rows)
        assert len(data) == 2
        assert data[0] == ("张三", "技术部", "30")
        assert data[1] == ("李四", "产品部", "28")

    def test_read_excel_rows_default_sheet(self, sample_xlsx):
        columns, rows = read_excel_rows(sample_xlsx, None)
        assert columns == ["姓名", "部门", "年龄"]

    def test_empty_file_raises(self):
        wb = Workbook()
        ws = wb.active
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        wb.save(path)

        try:
            with pytest.raises(ValueError, match="header"):
                read_excel_rows(path, "Sheet")
        finally:
            os.unlink(path)

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            read_excel_rows("/nonexistent/file.xlsx", "Sheet1")


class TestExcelInputPlugin:
    def test_config_model(self):
        assert ExcelInputPlugin.config_model() == ExcelInputConfig

    def test_execute_writes_to_db(self, sample_xlsx):
        db = SQLiteManager()
        context = Context(db=db, params={}, yaml_dir="/tmp", scene_name="test")
        config = ExcelInputConfig(file=sample_xlsx, sheet="人员列表")

        plugin = ExcelInputPlugin()
        plugin.name = "excel"
        plugin.label = "人员明细"
        plugin.table_name = "person_detail"
        plugin.execute(context, config)

        assert db.table_exists("person_detail")
        rows = db.query("SELECT * FROM person_detail")
        assert len(rows) == 2
        assert rows[0] == ("张三", "技术部", "30")

        db.close()
        db.remove()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_excel_input.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 Excel 输入插件**

```python
# src/pipeforge/plugins/input/__init__.py
from pipeforge.plugins.input.excel import ExcelInputPlugin

__all__ = ["ExcelInputPlugin"]
```

```python
# src/pipeforge/plugins/input/excel.py
from typing import Iterator

from openpyxl import load_workbook

from pipeforge.config.models import ExcelInputConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.base import InputPlugin


def read_excel_rows(file: str, sheet: str | None = None) -> tuple[list[str], Iterator[tuple]]:
    """读取 Excel 文件，返回 (columns, rows) 元组。"""
    wb = load_workbook(file, read_only=True, data_only=True)

    if sheet is None:
        ws = wb.active
    else:
        if sheet not in wb.sheetnames:
            wb.close()
            raise ValueError(f"Sheet '{sheet}' not found. Available: {wb.sheetnames}")
        ws = wb[sheet]

    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = next(rows_iter)
    except StopIteration:
        wb.close()
        raise ValueError("Excel file has no header row (first row is empty)")

    if header is None or all(h is None for h in header):
        wb.close()
        raise ValueError("Excel file has an empty header row")

    columns = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(header)]

    def row_generator():
        for row in rows_iter:
            if row is not None:
                yield row
        wb.close()

    return columns, row_generator()


@register_plugin("excel", "input")
class ExcelInputPlugin(InputPlugin):
    """从 Excel 文件读取数据并写入 SQLite。"""

    @classmethod
    def config_model(cls) -> type[ExcelInputConfig]:
        return ExcelInputConfig

    def execute(self, context, config: ExcelInputConfig) -> None:
        columns, rows = read_excel_rows(config.file, config.sheet)
        context.db.create_table(self.table_name, columns)
        with context.db.transaction():
            for row in rows:
                context.db.insert_row(self.table_name, row)
        context.logger.info(f"Input '{self.label}': loaded data into table '{self.table_name}'")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_excel_input.py -v`
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_excel_input.py src/pipeforge/plugins/input/__init__.py src/pipeforge/plugins/input/excel.py
git commit -m "feat: add Excel input plugin with read_excel_rows"
```

---

### Task 10: SQL 处理插件

**Files:**
- Create: `tests/test_sql_processor.py`
- Create: `src/pipeforge/plugins/processor/__init__.py`
- Create: `src/pipeforge/plugins/processor/sql.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_sql_processor.py
import sqlite3

import pytest

from pipeforge.plugins.processor.sql import SqlProcessorPlugin
from pipeforge.plugins.processor import SqlProcessorPlugin as ImportedPlugin
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.core.context import Context
from pipeforge.config.models import SqlProcessorConfig


class TestSqlProcessorPlugin:
    @pytest.fixture
    def setup_db(self):
        db = SQLiteManager()
        db.create_table("source_tbl", ["id", "name"])
        with db.transaction():
            db.insert_row("source_tbl", ("1", "Alice"))
            db.insert_row("source_tbl", ("2", "Bob"))
        context = Context(db=db, params={}, yaml_dir="/tmp", scene_name="test")
        yield db, context
        db.close()
        db.remove()

    def test_config_model(self):
        assert SqlProcessorPlugin.config_model() == SqlProcessorConfig

    def test_execute_creates_table(self, setup_db):
        db, context = setup_db
        config = SqlProcessorConfig(
            sql="CREATE TABLE report AS SELECT * FROM source_tbl WHERE id = '1'"
        )
        plugin = SqlProcessorPlugin()
        plugin.name = "sql"
        plugin.label = "过滤器"
        plugin.execute(context, config)

        assert db.table_exists("report")
        rows = db.query("SELECT * FROM report")
        assert len(rows) == 1
        assert rows[0] == ("1", "Alice")

    def test_invalid_sql_raises(self, setup_db):
        db, context = setup_db
        config = SqlProcessorConfig(sql="SELECT * FROM nonexistent_table")
        plugin = SqlProcessorPlugin()
        plugin.name = "sql"
        plugin.label = "bad_sql"

        with pytest.raises(sqlite3.OperationalError):
            plugin.execute(context, config)

    def test_multiple_statements(self, setup_db):
        db, context = setup_db
        config = SqlProcessorConfig(
            sql="""
            CREATE TABLE report_a AS SELECT * FROM source_tbl;
            CREATE TABLE report_b AS SELECT name FROM source_tbl;
            """
        )
        plugin = SqlProcessorPlugin()
        plugin.name = "sql"
        plugin.label = "多语句"
        plugin.execute(context, config)

        assert db.table_exists("report_a")
        assert db.table_exists("report_b")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_sql_processor.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 SQL 处理插件**

```python
# src/pipeforge/plugins/processor/__init__.py
from pipeforge.plugins.processor.sql import SqlProcessorPlugin

__all__ = ["SqlProcessorPlugin"]
```

```python
# src/pipeforge/plugins/processor/sql.py
from pipeforge.config.models import SqlProcessorConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.base import ProcessorPlugin


@register_plugin("sql", "processor")
class SqlProcessorPlugin(ProcessorPlugin):
    """在 SQLite 中执行 SQL 语句。"""

    @classmethod
    def config_model(cls) -> type[SqlProcessorConfig]:
        return SqlProcessorConfig

    def execute(self, context, config: SqlProcessorConfig) -> None:
        context.db.execute(config.sql)
        context.logger.info(f"Processor '{self.label}': SQL executed successfully")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_sql_processor.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_sql_processor.py src/pipeforge/plugins/processor/__init__.py src/pipeforge/plugins/processor/sql.py
git commit -m "feat: add SQL processor plugin"
```

---

### Task 11: Excel 输出插件

**Files:**
- Create: `tests/test_excel_output.py`
- Create: `src/pipeforge/plugins/output/__init__.py`
- Create: `src/pipeforge/plugins/output/excel.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_excel_output.py
import tempfile
import os
import copy

import pytest
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from pipeforge.plugins.output.excel import ExcelOutputPlugin, resolve_filename
from pipeforge.plugins.output import ExcelOutputPlugin as ImportedPlugin
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.core.context import Context
from pipeforge.config.models import ExcelOutputConfig, ColumnMapping


@pytest.fixture
def template_xlsx():
    """创建模板 Excel 文件，包含样式和列宽。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "报表"

    header_font = Font(name="微软雅黑", bold=True, size=12)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

    headers = ["姓名", "部门", "状态"]
    for i, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=i, value=h)
        cell.font = copy.copy(header_font)
        cell.fill = copy.copy(header_fill)

    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 20
    ws.freeze_panes = "A2"

    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    return path


@pytest.fixture
def setup_context_and_db(template_xlsx):
    db = SQLiteManager()
    db.create_table("report_data", ["name", "dept", "status"])
    with db.transaction():
        db.insert_row("report_data", ("张三", "技术部", "正常"))
        db.insert_row("report_data", ("李四", "产品部", "预警"))

    output_dir = tempfile.mkdtemp()
    context = Context(db=db, params={}, yaml_dir=os.path.dirname(template_xlsx), scene_name="人员月报")
    context.output_dir = output_dir
    yield db, context, template_xlsx, output_dir
    db.close()
    db.remove()
    for f in os.listdir(output_dir):
        os.unlink(os.path.join(output_dir, f))
    os.rmdir(output_dir)


class TestResolveFilename:
    def test_default_filename(self):
        result = resolve_filename(None, "人员月报")
        assert result.endswith(".xlsx")
        assert "人员月报" in result

    def test_scene_name_variable(self):
        result = resolve_filename("{{scene_name}}_report.xlsx", "人员月报")
        assert result == "人员月报_report.xlsx"

    def test_date_variable(self):
        result = resolve_filename("report_{{date:%Y}}.xlsx", "test")
        assert result.startswith("report_20")
        assert result.endswith(".xlsx")


class TestExcelOutputPlugin:
    def test_config_model(self):
        assert ExcelOutputPlugin.config_model() == ExcelOutputConfig

    def test_execute_writes_output(self, setup_context_and_db):
        db, context, template_xlsx, output_dir = setup_context_and_db
        config = ExcelOutputConfig(
            template=template_xlsx,
            sheet="报表",
            output_dir=output_dir,
            source_table="report_data",
            columns=[
                ColumnMapping(source="name", target="姓名"),
                ColumnMapping(source="dept", target="部门"),
                ColumnMapping(source="status", target="状态"),
            ],
        )

        plugin = ExcelOutputPlugin()
        plugin.name = "excel"
        plugin.execute(context, config)

        assert context.output_path is not None
        assert os.path.exists(context.output_path)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_excel_output.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 Excel 输出插件**

```python
# src/pipeforge/plugins/output/__init__.py
from pipeforge.plugins.output.excel import ExcelOutputPlugin

__all__ = ["ExcelOutputPlugin"]
```

```python
# src/pipeforge/plugins/output/excel.py
import copy
import os
from datetime import datetime
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell

from pipeforge.config.models import ExcelOutputConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.base import OutputPlugin


def resolve_filename(filename_template: str | None, scene_name: str) -> str:
    """解析文件名模板中的变量。"""
    if filename_template is None:
        filename_template = "{{scene_name}}_{{date:%Y%m%d}}.xlsx"

    now = datetime.now()
    result = filename_template
    result = result.replace("{{scene_name}}", scene_name)
    result = result.replace("{{timestamp}}", str(int(now.timestamp())))

    import re
    def replace_date(match):
        fmt = match.group(1)
        return now.strftime(fmt)

    result = re.sub(r"\{\{date:(.+?)\}\}", replace_date, result)
    return result


@register_plugin("excel", "output")
class ExcelOutputPlugin(OutputPlugin):
    """Excel 模板输出插件 — 三阶段写入保留样式、列宽和冻结窗格。"""

    @classmethod
    def config_model(cls) -> type[ExcelOutputConfig]:
        return ExcelOutputConfig

    def execute(self, context, config: ExcelOutputConfig) -> None:
        template_path = os.path.join(context.yaml_dir, config.template)
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found: {template_path}")

        filename = resolve_filename(config.filename, context.scene_name)
        output_dir = config.output_dir or "./output/"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        context.output_path = output_path

        rows = context.db.query(f'SELECT * FROM "{config.source_table}"')
        source_columns = [
            d[0] for d in context.db._conn.execute(
                f'PRAGMA table_info("{config.source_table}")'
            ).fetchall()
        ]

        source_to_idx = {col: i for i, col in enumerate(source_columns)}
        for cm in config.columns:
            if cm.source not in source_to_idx:
                raise ValueError(
                    f"Source column '{cm.source}' not found in table "
                    f"'{config.source_table}'. Available: {source_columns}"
                )

        header_styles, column_widths, freeze_panes = self._extract_template_attrs(
            template_path, config.sheet, config.columns
        )

        wb = Workbook(write_only=True)
        ws = wb.create_sheet(title=config.sheet)

        if freeze_panes:
            ws.freeze_panes = freeze_panes

        self._write_header(ws, config.columns, header_styles)

        for row in rows:
            data_row = [row[source_to_idx[cm.source]] for cm in config.columns]
            ws.append(data_row)

        wb.save(output_path)

        self._restore_column_widths(output_path, column_widths)

        context.logger.info(
            f"Output: wrote {len(rows)} rows to {output_path}"
        )

    def _extract_template_attrs(self, template_path, sheet_name, columns):
        wb = load_workbook(template_path)
        ws = wb[sheet_name] if sheet_name else wb.active

        first_row_cells = list(ws.iter_rows(min_row=1, max_row=1))
        template_headers = [c.value for c in first_row_cells[0]] if first_row_cells else []

        header_styles = {}
        for cell in first_row_cells[0]:
            if cell.value is not None:
                header_styles[str(cell.value)] = {
                    "font": copy.copy(cell.font),
                    "fill": copy.copy(cell.fill),
                    "border": copy.copy(cell.border),
                    "alignment": copy.copy(cell.alignment),
                    "number_format": cell.number_format,
                }

        column_widths = {}
        for col_letter, col_dim in ws.column_dimensions.items():
            if col_dim.width is not None:
                column_widths[col_letter] = col_dim.width

        for cm in columns:
            if cm.target not in header_styles:
                wb.close()
                raise ValueError(
                    f"Target column '{cm.target}' not found in template headers. "
                    f"Available: {template_headers}"
                )

        freeze_panes = ws.freeze_panes

        wb.close()
        return header_styles, column_widths, freeze_panes

    def _write_header(self, ws, columns, header_styles):
        header_row = []
        for cm in columns:
            cell = WriteOnlyCell(ws, value=cm.target)
            style = header_styles.get(cm.target)
            if style:
                cell.font = style["font"]
                cell.fill = style["fill"]
                cell.border = style["border"]
                cell.alignment = style["alignment"]
                cell.number_format = style["number_format"]
            header_row.append(cell)
        ws.append(header_row)

    def _restore_column_widths(self, output_path, column_widths):
        if not column_widths:
            return
        wb = load_workbook(output_path)
        ws = wb.active
        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width
        wb.save(output_path)
        wb.close()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_excel_output.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_excel_output.py src/pipeforge/plugins/output/__init__.py src/pipeforge/plugins/output/excel.py
git commit -m "feat: add Excel output plugin with three-phase write"
```

---

### Task 12: CLI 入口

**Files:**
- Create: `tests/test_cli.py`
- Create: `src/pipeforge/cli.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_cli.py
import tempfile
import os

import pytest
from click.testing import CliRunner

from pipeforge.cli import main


YAML_FIXTURE = """
scene:
  name: CLI测试
  description: test
  version: "1.0"

inputs:
  - name: 数据源
    plugin: excel
    table: source_tbl
    param_key: data_file
    config:
      sheet: Sheet1

processors:
  - name: 处理
    plugin: sql
    output_tables:
      - result
    config:
      sql: CREATE TABLE result AS SELECT 1 AS x

output:
  plugin: excel
  config:
    template: templates/report.xlsx
    sheet: 报表
    source_table: result
    columns:
      - source: x
        target: x
"""


class TestCLI:
    @pytest.fixture
    def yaml_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(YAML_FIXTURE)
            path = f.name
        yield path
        os.unlink(path)

    def test_run_missing_required_params_shows_error(self, yaml_config):
        runner = CliRunner()
        result = runner.invoke(main, ["run", yaml_config])
        assert result.exit_code != 0
        assert "data_file" in result.output or "Missing" in result.output

    def test_run_nonexistent_file(self):
        runner = CliRunner()
        result = runner.invoke(main, ["run", "/nonexistent/path.yaml"])
        assert result.exit_code != 0

    def test_version_command(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 CLI**

```python
# src/pipeforge/cli.py
import sys

import click

from pipeforge.core.engine import PipelineEngine


@click.group()
@click.version_option(version="0.1.0", prog_name="pipeforge")
def main():
    """PipeForge — CLI data pipeline framework."""
    pass


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option("--param", "-p", "params", multiple=True, help="Runtime parameter in key=value format")
@click.option("--cleanup", is_flag=True, help="Remove temporary database after execution")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def run(config_path, params, cleanup, verbose):
    """Execute a pipeline from a YAML configuration file."""
    try:
        engine = PipelineEngine(config_path)
    except Exception as e:
        click.echo(f"Config error: {e}", err=True)
        sys.exit(1)

    required = engine.required_params()
    provided = {}
    for p in params:
        if "=" in p:
            key, value = p.split("=", 1)
            provided[key.strip()] = value.strip()

    missing = [r for r in required if r.key not in provided]
    if missing:
        click.echo(f"Pipeline: {engine.config.scene.name}")
        click.echo(f"Description: {engine.config.scene.description or 'N/A'}")
        click.echo()
        for r in missing:
            click.echo(f"  [{r.label}]")
            value = click.prompt(f"  Enter file path for '{r.label}'", type=str)
            provided[r.key] = value

    if verbose:
        click.echo(f"Executing pipeline: {engine.config.scene.name}")

    try:
        result = engine.execute(params=provided, cleanup=cleanup)
        _print_result(result)
    except Exception as e:
        click.echo(f"Pipeline error: {e}", err=True)
        sys.exit(1)


def _print_result(result):
    click.echo()
    click.echo("=== Pipeline Complete ===")
    for name, stats in result.inputs.items():
        click.echo(f"  Input [{name}]: {stats.rows_loaded} rows ({stats.elapsed_ms}ms)")
    for stats in result.processors:
        created = ", ".join(stats.tables_created) if stats.tables_created else "none"
        click.echo(f"  Processor [{stats.name}]: created tables: {created} ({stats.elapsed_ms}ms)")
    if result.output:
        click.echo(f"  Output: {result.output.rows_written} rows → {result.output.file_path} ({result.output.elapsed_ms}ms)")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_cli.py -v`
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_cli.py src/pipeforge/cli.py
git commit -m "feat: add CLI entry point with interactive param collection"
```

---

### Task 13: 集成测试 + 边界场景

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_integration.py`

- [ ] **Step 1: 创建共享 fixtures**

```python
# tests/conftest.py
import tempfile
import os
import copy

import pytest
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


@pytest.fixture
def sample_xlsx():
    """创建包含人员明细的测试 Excel。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "人员列表"
    ws.append(["工号", "姓名", "部门", "岗位"])
    ws.append(["001", "张三", "技术部", "工程师"])
    ws.append(["002", "李四", "产品部", "产品经理"])
    ws.append(["003", "王五", "技术部", "高级工程师"])

    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    yield path
    os.unlink(path)


@pytest.fixture
def sample_xlsx_attendance():
    """创建包含考勤数据的测试 Excel。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "考勤统计"
    ws.append(["工号", "出勤天数", "迟到次数"])
    ws.append(["001", "22", "1"])
    ws.append(["002", "20", "4"])
    ws.append(["003", "21", "0"])

    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    yield path
    os.unlink(path)


@pytest.fixture
def template_xlsx():
    """创建带样式的 Excel 模板。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "报表"

    header_font = Font(name="微软雅黑", bold=True, size=12)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

    headers = ["姓名", "所属部门", "岗位", "出勤天数", "迟到次数", "状态"]
    for i, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=i, value=h)
        cell.font = copy.copy(header_font)
        cell.fill = copy.copy(header_fill)

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 15
    ws.freeze_panes = "A2"

    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    yield path
    os.unlink(path)
```

- [ ] **Step 2: 写集成测试**

```python
# tests/test_integration.py
import tempfile
import os

import pytest

from pipeforge.config import load_yaml_config
from pipeforge.core.engine import PipelineEngine


def _write_yaml(content, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class TestSingleInputPipeline:
    """单输入 → SQL处理 → 输出的完整流程。"""
    def test_end_to_end(self, sample_xlsx, template_xlsx):
        output_dir = tempfile.mkdtemp()
        yaml_content = f"""
scene:
  name: 单输入测试
  description: test
  version: "1.0"

inputs:
  - name: 人员
    plugin: excel
    table: person
    param_key: person_file
    config:
      sheet: 人员列表

processors:
  - name: 统计
    plugin: sql
    output_tables:
      - report
    config:
      sql: |
        CREATE TABLE report AS
        SELECT 姓名, 部门, 岗位 FROM person WHERE 部门 = '技术部'

output:
  plugin: excel
  config:
    template: {template_xlsx}
    sheet: 报表
    output_dir: {output_dir}
    source_table: report
    columns:
      - source: 姓名
        target: 姓名
      - source: 部门
        target: 所属部门
      - source: 岗位
        target: 岗位
"""
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        _write_yaml(yaml_content, yaml_path)

        try:
            engine = PipelineEngine(yaml_path)
            result = engine.execute(params={"person_file": sample_xlsx})

            assert "人员" in result.inputs
            assert result.inputs["人员"].rows_loaded == 3
            assert len(result.processors) == 1
            assert result.processors[0].tables_created == ["report"]
            assert result.output is not None
            assert result.output.rows_written == 2  # 技术部有 2 人
            assert os.path.exists(result.output.file_path)
        finally:
            os.unlink(yaml_path)
            for f in os.listdir(output_dir):
                os.unlink(os.path.join(output_dir, f))
            os.rmdir(output_dir)


class TestMultiInputPipeline:
    """多输入 JOIN 场景。"""
    def test_join_pipeline(self, sample_xlsx, sample_xlsx_attendance, template_xlsx):
        output_dir = tempfile.mkdtemp()
        yaml_content = f"""
scene:
  name: 多输入JOIN
  description: test
  version: "1.0"

inputs:
  - name: 人员
    plugin: excel
    table: person
    param_key: person_file
    config:
      sheet: 人员列表
  - name: 考勤
    plugin: excel
    table: attendance
    param_key: attendance_file
    config:
      sheet: 考勤统计

processors:
  - name: 合并统计
    plugin: sql
    output_tables:
      - report
    config:
      sql: |
        CREATE TABLE report AS
        SELECT
          p.姓名,
          p.部门,
          p.岗位,
          a.出勤天数,
          a.迟到次数,
          CASE WHEN CAST(a.迟到次数 AS INTEGER) > 3 THEN '预警' ELSE '正常' END AS 状态
        FROM person p
        LEFT JOIN attendance a ON p.工号 = a.工号

output:
  plugin: excel
  config:
    template: {template_xlsx}
    sheet: 报表
    output_dir: {output_dir}
    source_table: report
    columns:
      - source: 姓名
        target: 姓名
      - source: 部门
        target: 所属部门
      - source: 岗位
        target: 岗位
      - source: 出勤天数
        target: 出勤天数
      - source: 迟到次数
        target: 迟到次数
      - source: 状态
        target: 状态
"""
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        _write_yaml(yaml_content, yaml_path)

        try:
            engine = PipelineEngine(yaml_path)
            result = engine.execute(params={
                "person_file": sample_xlsx,
                "attendance_file": sample_xlsx_attendance,
            })

            assert result.inputs["人员"].rows_loaded == 3
            assert result.inputs["考勤"].rows_loaded == 3
            assert result.output is not None
            assert result.output.rows_written == 3
        finally:
            os.unlink(yaml_path)
            for f in os.listdir(output_dir):
                os.unlink(os.path.join(output_dir, f))
            os.rmdir(output_dir)


class TestEmptyResultsPipeline:
    """空查询结果输出仅含表头的文件。"""
    def test_empty_output(self, sample_xlsx, template_xlsx):
        output_dir = tempfile.mkdtemp()
        yaml_content = f"""
scene:
  name: 空结果测试
  description: test
  version: "1.0"

inputs:
  - name: 人员
    plugin: excel
    table: person
    param_key: person_file
    config:
      sheet: 人员列表

processors:
  - name: 过滤为空
    plugin: sql
    output_tables:
      - report
    config:
      sql: CREATE TABLE report AS SELECT 姓名, 部门, 岗位 FROM person WHERE 部门 = '不存在部门'

output:
  plugin: excel
  config:
    template: {template_xlsx}
    sheet: 报表
    output_dir: {output_dir}
    source_table: report
    columns:
      - source: 姓名
        target: 姓名
      - source: 部门
        target: 所属部门
      - source: 岗位
        target: 岗位
"""
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        _write_yaml(yaml_content, yaml_path)

        try:
            engine = PipelineEngine(yaml_path)
            result = engine.execute(params={"person_file": sample_xlsx})

            assert result.output is not None
            assert result.output.rows_written == 0
            assert os.path.exists(result.output.file_path)
        finally:
            os.unlink(yaml_path)
            for f in os.listdir(output_dir):
                os.unlink(os.path.join(output_dir, f))
            os.rmdir(output_dir)


class TestNoInputPipeline:
    """空 inputs — processor 直接用 SQL 创建表。"""
    def test_no_inputs(self, template_xlsx):
        output_dir = tempfile.mkdtemp()
        yaml_content = f"""
scene:
  name: 无输入测试
  description: test
  version: "1.0"

processors:
  - name: 直接生成
    plugin: sql
    output_tables:
      - report
    config:
      sql: |
        CREATE TABLE report (姓名, 部门, 岗位);
        INSERT INTO report VALUES ('系统生成', 'IT', '自动');

output:
  plugin: excel
  config:
    template: {template_xlsx}
    sheet: 报表
    output_dir: {output_dir}
    source_table: report
    columns:
      - source: 姓名
        target: 姓名
      - source: 部门
        target: 所属部门
      - source: 岗位
        target: 岗位
"""
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        _write_yaml(yaml_content, yaml_path)

        try:
            engine = PipelineEngine(yaml_path)
            assert len(engine.required_params()) == 0
            result = engine.execute(params={})

            assert result.processors[0].tables_created == ["report"]
            assert result.output is not None
            assert result.output.rows_written == 1
        finally:
            os.unlink(yaml_path)
            for f in os.listdir(output_dir):
                os.unlink(os.path.join(output_dir, f))
            os.rmdir(output_dir)
```

- [ ] **Step 3: 运行所有测试**

Run: `pytest tests/ -v`
Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/test_integration.py
git commit -m "test: add integration tests for single input, multi-input JOIN, empty results, no inputs"
```

---

## 自检清单

1. **Spec 覆盖:** 每个需求都对应一个 Task — Input (Task 9), Processor (Task 10), Output (Task 11), 配置 (Task 4+7), CLI (Task 12), 错误处理 (各 Task 测试中覆盖), 边界场景 (Task 13)
2. **占位符检查:** 无 "TOD" / "TBD" / "implement later" — 所有步骤含完整代码
3. **类型一致性:** `Context` 属性 (Task 6) 与引擎使用 (Task 8) 一致; `config.file` 注入 (Task 8) 与 `ExcelInputConfig.file` 字段 (Task 4) 一致; 插件属性注入 (Task 8) 与基类设计 (Task 2) 一致

---

**Plan complete. Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, two-stage review between tasks
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
