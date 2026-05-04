# PipeForge 详细设计文档

> 基于: DESIGN_v6.md (高阶设计 v0.6 终版)  
> 文档版本: v0.1  
> 日期: 2026-05-03  
> 状态: 详细设计阶段  
> 粒度: 模块级伪代码

---

## 前言：与高阶设计的关系

本文档是 DESIGN_v6.md 的详细设计补充。阅读本文档前需先理解高阶设计中的：

- 三段式流水线架构（§3.1）
- 四种设计模式（§3.2）
- 插件接口与参数注入机制（§3.3）
- 配置结构与字段定义（§4）
- 技术选型理由（§6）

本文档聚焦于每个模块的**完整接口、算法伪代码、数据结构和错误处理流程**，可直接作为编码依据。

### 高阶设计勘误

以下问题在编写详细设计过程中发现，对应修正将体现在本文档的各模块设计中：

| # | 问题 | HLD 位置 | 修正 |
|---|------|---------|------|
| 1 | `column_dimensions` 在 openpyxl `write_only` 模式下不支持，HLD 声称可恢复 | §4.5、§6.1 | 改为**三阶段写入**：write_only 写数据后，用普通模式重新打开设置列宽 |
| 2 | `extra="ignore"` 静默丢弃拼写错误 | §4.7 | 保持 `extra="ignore"`，但加载后对未知字段输出 warning 日志 |
| 3 | openpyxl 样式对象不可直接赋值给 WriteOnlyCell，需 `copy.copy()` | §6.1 步骤 5 | 明确要求对 font/fill/border/alignment 使用 `copy()` |
| 4 | `freeze_panes` 必须在 `append()` 之前设置 | §6.1 步骤 7 | 调整步骤顺序，冻结窗格在写入数据前设置 |
| 5 | 模板路径解析规则未定义 | §4.2 | 明确：相对于 YAML 配置文件所在目录解析 |
| 6 | 文件名中场景名可能包含非法字符 | §4.3 | 自动替换非法字符 `/\:*?"<>|` 为 `_` |

### 详细设计中的关键决策

| # | 决策 | 理由 |
|---|------|------|
| D1 | 模板路径相对于 YAML 配置文件目录 | 配置可移植（整个目录打包即可复用） |
| D2 | 插件通过 `__init__.py` 显式 import | MVP 简单可预测，避免 importlib 黑魔法 |
| D3 | 文件名非法字符自动替换为 `_` | 安全且用户无需关心细节 |
| D4 | Plugin.name 不在基类声明，由引擎注入 | 避免 Python 类变量/实例变量混淆（详见 §3.1） |
| D5 | SQLite 临时库在引擎 `execute()` 开始时创建 | 确保所有阶段都能写入，避免懒加载复杂性 |
| D6 | 配置加载时额外字段输出 warning（非 error） | 兼顾向前兼容性和可发现性 |

---

## 1. 模块详细设计：CLI 层

### 1.1 职责

CLI 层负责所有终端 I/O，引擎不接触 `input()` / `print()`。

### 1.2 入口函数

```
# src/pipeforge/cli.py

import click
from pipeforge.core.engine import PipelineEngine

@click.group()
def main():
    """PipeForge - 数据流水线框架"""
    pass

@main.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option("--param", "-p", multiple=True, help="运行时参数，格式: key=value")
@click.option("--cleanup", is_flag=True, help="执行成功后清理临时文件")
@click.option("--verbose", "-v", is_flag=True, help="显示详细日志")
def run(config_path: str, param: tuple[str, ...], cleanup: bool, verbose: bool):
    """
    执行流水线配置。

    示例:
      pipeforge run pipelines/report.yaml
      pipeforge run pipelines/report.yaml -p person_file=data/人员.xlsx
      pipeforge run pipelines/report.yaml -p person_file=data/人员.xlsx -p attendance_file=data/考勤.xlsx
    """
```

### 1.3 run 命令流程

```
run(config_path, param, cleanup, verbose):
    # 步骤 1: 解析 --param 参数
    parsed_params = {}
    for p in param:
        if "=" not in p:
            click.echo(f"错误: --param 格式应为 key=value，收到: {p}", err=True)
            raise SystemExit(1)
        key, _, value = p.partition("=")
        parsed_params[key] = value

    # 步骤 2: 初始化引擎
    engine = PipelineEngine(config_path=config_path)

    # 步骤 3: 加载配置（可能失败 → 结构化错误输出）
    try:
        engine.load_config()
    except ConfigError as e:
        _print_config_error(e)
        raise SystemExit(1)

    # 步骤 4: 收集运行时参数
    required = engine.required_params()
    for rp in required:
        if rp.key not in parsed_params:
            # 交互式引导输入
            prompt = f"{rp.label}"
            if rp.description:
                prompt += f" ({rp.description})"
            value = click.prompt(prompt)
            parsed_params[rp.key] = value

    # 步骤 5: 执行流水线
    try:
        result = engine.execute(params=parsed_params, cleanup=cleanup)
    except PipelineError as e:
        _print_pipeline_error(e)
        raise SystemExit(1)

    # 步骤 6: 输出结果摘要
    _print_result(result, verbose)
```

### 1.4 输出格式化

```
_print_config_error(e: ConfigError):
    """结构化输出配置错误"""
    click.echo(click.style("配置错误", fg="red", bold=True))
    click.echo(f"  文件: {e.config_path}")
    for err in e.errors:  # errors 是列表，可能有多个
        click.echo(f"  - [{err.field}] {err.message}")

_print_pipeline_error(e: PipelineError):
    """结构化输出运行时错误"""
    click.echo(click.style(f"{e.stage}阶段错误", fg="red", bold=True))
    click.echo(f"  类型: {e.error_type}")
    click.echo(f"  详情: {e.message}")
    if e.db_path:
        click.echo(f"  临时数据库已保留: {e.db_path}")
    if e.hint:
        click.echo(f"  提示: {e.hint}")

_print_result(result: ExecutionResult, verbose: bool):
    """输出执行结果摘要"""
    click.echo(click.style("\n执行完成", fg="green", bold=True))

    if verbose:
        for name, stats in result.inputs.items():
            click.echo(f"  输入 [{name}]: {stats.rows_loaded} 行, {stats.elapsed_ms}ms")

        for ps in result.processors:
            click.echo(f"  处理 [{ps.name}]: 创建表 {ps.tables_created}, {ps.elapsed_ms}ms")

        if result.output:
            click.echo(f"  输出: {result.output.rows_written} 行 → {result.output.file_path}, {result.output.elapsed_ms}ms")
    else:
        total_rows = sum(s.rows_loaded for s in result.inputs.values())
        click.echo(f"  输入: {len(result.inputs)} 个来源, 共 {total_rows} 行")
        if result.output:
            click.echo(f"  输出: {result.output.file_path}")

    if result.warnings:
        click.echo(click.style("\n警告:", fg="yellow"))
        for w in result.warnings:
            click.echo(f"  - {w}")
```

### 1.5 异常类型

```
class PipeForgeError(Exception):
    """所有 PipeForge 错误的基类"""
    pass

class ConfigError(PipeForgeError):
    config_path: str
    errors: list[ConfigErrorItem]  # ConfigErrorItem 见 §2.7

class PipelineError(PipeForgeError):
    stage: str          # "配置" | "输入" | "处理" | "输出"
    error_type: str     # 如 "FileNotFoundError"
    message: str
    db_path: str | None = None
    hint: str | None = None
```

---

## 2. 模块详细设计：配置系统

### 2.1 模块结构

```
src/pipeforge/config/
├── __init__.py    # 导出 SceneConfig, load_yaml_config
├── models.py      # 所有 Pydantic 模型
└── loader.py      # YAML 加载 + 校验编排
```

### 2.2 Pydantic 配置模型完整定义

```
# src/pipeforge/config/models.py

from pydantic import BaseModel, Field, model_validator
from typing import Literal

# ============================================================
# Scene 元信息
# ============================================================

class SceneMeta(BaseModel):
    name: str                                    # 场景名称
    description: str = ""                        # 场景描述
    version: str = "1.0"                         # 配置版本

    model_config = ConfigDict(extra="ignore")    # 向前兼容

# ============================================================
# Input 配置
# ============================================================

class ExcelInputConfig(BaseModel):
    """excel 输入插件的 config: 块"""
    sheet: str = "Sheet1"                        # 工作表名
    file: str | None = None                      # 文件路径（由参数注入，YAML 中不出现）

    model_config = ConfigDict(extra="ignore")

class InputSpec(BaseModel):
    """单个 input 的完整配置"""
    name: str                                    # 人类可读名称
    plugin: Literal["excel"]                     # 插件名（MVP 仅 excel）
    table: str                                   # 目标 SQLite 表名
    param_key: str                               # 运行时参数名
    config: ExcelInputConfig                     # 插件专属配置

    model_config = ConfigDict(extra="ignore")

# ============================================================
# Processor 配置
# ============================================================

class SqlProcessorConfig(BaseModel):
    """sql 处理插件的 config: 块"""
    sql: str                                     # SQL 语句

    model_config = ConfigDict(extra="ignore")

class ProcessorSpec(BaseModel):
    """单个 processor 的完整配置"""
    name: str                                    # 人类可读名称
    plugin: Literal["sql"]                       # 插件名（MVP 仅 sql）
    output_tables: list[str] = []                # 声明该处理器创建的表名
    config: SqlProcessorConfig                   # 插件专属配置

    model_config = ConfigDict(extra="ignore")

# ============================================================
# Output 配置
# ============================================================

class ColumnMapping(BaseModel):
    """单列映射"""
    source: str                                  # SQL 结果列名
    target: str                                  # 模板列头名

class ExcelOutputConfig(BaseModel):
    """excel 输出插件的 config: 块"""
    template: str                                # 模板文件路径（相对于 YAML 文件目录）
    sheet: str = "Sheet1"                        # 目标 Sheet 名
    output_dir: str = "./output/"                # 输出目录（相对于 CWD）
    source_table: str                            # 数据源表名
    filename: str | None = None                  # 输出文件名模板
    columns: list[ColumnMapping]                 # 列映射列表

    model_config = ConfigDict(extra="ignore")

class OutputSpec(BaseModel):
    """output 的完整配置"""
    plugin: Literal["excel"]                     # 插件名（MVP 仅 excel）
    config: ExcelOutputConfig                    # 插件专属配置

    model_config = ConfigDict(extra="ignore")

# ============================================================
# Pipeline 顶层配置
# ============================================================

class SceneConfig(BaseModel):
    """完整的管道配置"""
    scene: SceneMeta
    inputs: list[InputSpec] = []
    processors: list[ProcessorSpec] = []         # MVP 只执行第一个
    output: OutputSpec | None = None

    model_config = ConfigDict(extra="ignore")
```

### 2.3 YAML 加载流程

```
# src/pipeforge/config/loader.py

def load_yaml_config(yaml_path: str) -> tuple[SceneConfig, list[str]]:
    """
    加载 YAML 配置，返回 (配置模型, 未知字段警告列表)。

    步骤:
    1. 读取 YAML 文件
    2. PyYAML safe_load 解析
    3. 检测 YAML 中的未知顶层字段
    4. SceneConfig.model_validate() 校验
    5. 检测每个 spec 中的未知字段
    6. 执行业务校验（表名冲突检测等）
    """

    # 步骤 1-2: 读取 + 解析
    with open(yaml_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ConfigError(config_path=yaml_path, errors=[
            ConfigErrorItem(field="(root)", message="YAML 文件为空")
        ])

    # 步骤 3: 检测未知顶层字段
    known_top_fields = {"scene", "inputs", "processors", "output"}
    warnings = _collect_unknown_fields(raw, known_top_fields, path="")

    # 步骤 4: Pydantic 校验
    try:
        config = SceneConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(config_path=yaml_path, errors=_convert_errors(e))

    # 步骤 5: 检测子节点未知字段
    warnings += _detect_unknown_in_specs(raw)
    # ...

    return config, warnings
```

### 2.4 未知字段检测算法

```
# 常数：所有已知字段
KNOWN_TOP_FIELDS = {"scene", "inputs", "processors", "output"}
KNOWN_INPUT_FIELDS = {"name", "plugin", "table", "param_key", "config"}
KNOWN_PROCESSOR_FIELDS = {"name", "plugin", "output_tables", "config"}
KNOWN_OUTPUT_FIELDS = {"plugin", "config"}

def _collect_unknown_fields(raw: dict, known: set[str], path: str) -> list[str]:
    """递归收集未知字段，生成 warning 消息"""
    warnings = []
    for key in raw:
        if key not in known:
            warnings.append(f"未知字段 '{path}.{key}'，已忽略")
    return warnings

def _detect_unknown_in_specs(raw: dict) -> list[str]:
    """检测 inputs/processors/output 中的未知字段"""
    warnings = []

    for i, inp in enumerate(raw.get("inputs", [])):
        warnings += _collect_unknown_fields(inp, KNOWN_INPUT_FIELDS, f"inputs[{i}]")
        if "config" in inp and isinstance(inp["config"], dict):
            # ExcelInputConfig 已知字段
            warnings += _collect_unknown_fields(inp["config"], {"sheet"}, f"inputs[{i}].config")

    for i, proc in enumerate(raw.get("processors", [])):
        warnings += _collect_unknown_fields(proc, KNOWN_PROCESSOR_FIELDS, f"processors[{i}]")
        if "config" in proc and isinstance(proc["config"], dict):
            warnings += _collect_unknown_fields(proc["config"], {"sql"}, f"processors[{i}].config")

    if "output" in raw and raw["output"] is not None:
        out = raw["output"]
        warnings += _collect_unknown_fields(out, KNOWN_OUTPUT_FIELDS, "output")
        if "config" in out and isinstance(out["config"], dict):
            known_out_config = {"template", "sheet", "output_dir", "source_table", "filename", "columns"}
            warnings += _collect_unknown_fields(out["config"], known_out_config, "output.config")
            # 递归检查 columns 子项
            for j, col in enumerate(out["config"].get("columns", [])):
                warnings += _collect_unknown_fields(col, {"source", "target"}, f"output.config.columns[{j}]")

    return warnings
```

### 2.5 表名冲突检测算法

```
def validate_table_names(config: SceneConfig, yaml_dir: str) -> None:
    """
    配置加载阶段执行，失败抛 ConfigError。
    检测三条规则（对应 HLD §4.6）:

    1. inputs[].table 互不相同
    2. inputs[].table 不与任何 processor 的 output_tables 冲突
    3. output.config.source_table 存在于某个 processor 的 output_tables 中
    """
    errors = []

    # 规则 1: inputs 表名互斥
    seen_input_tables = {}
    for inp in config.inputs:
        if inp.table in seen_input_tables:
            errors.append(ConfigErrorItem(
                field=f"inputs[name={inp.name}].table",
                message=f"表名 '{inp.table}' 与 inputs[name={seen_input_tables[inp.table]}].table 冲突"
            ))
        seen_input_tables[inp.table] = inp.name

    # 收集所有 processor 声明的 output_tables
    all_output_tables = {}
    for proc in config.processors:
        for tbl in proc.output_tables:
            all_output_tables[tbl] = proc.name

    # 规则 2: input table 不与 output_tables 冲突
    for inp in config.inputs:
        if inp.table in all_output_tables:
            errors.append(ConfigErrorItem(
                field=f"inputs[name={inp.name}].table",
                message=f"表名 '{inp.table}' 与 processors[name={all_output_tables[inp.table]}].output_tables 冲突"
            ))

    # 规则 3: source_table 必须在 output_tables 中声明
    if config.output is not None:
        st = config.output.config.source_table
        if st not in all_output_tables:
            errors.append(ConfigErrorItem(
                field="output.config.source_table",
                message=f"表 '{st}' 未在任何 processor 的 output_tables 中声明"
            ))

    if errors:
        raise ConfigError(config_path=None, errors=errors)
```

### 2.6 模板列校验算法

```
def validate_template_columns(config: SceneConfig, yaml_dir: str) -> None:
    """
    配置加载阶段执行。

    校验 output.config.columns[].target 是否与模板目标 Sheet 首行匹配。
    模板文件此时必须存在且可读。
    """
    if config.output is None:
        return

    out_cfg = config.output.config

    # 解析模板路径（相对于 YAML 文件目录）
    template_path = _resolve_path(out_cfg.template, yaml_dir)

    # 读取模板目标 Sheet 首行表头
    try:
        wb = load_workbook(template_path, read_only=False)
    except FileNotFoundError:
        raise ConfigError(config_path=template_path, errors=[
            ConfigErrorItem(field="output.config.template", message=f"模板文件不存在: {template_path}")
        ])

    if out_cfg.sheet not in wb.sheetnames:
        raise ConfigError(config_path=template_path, errors=[
            ConfigErrorItem(field="output.config.sheet", message=f"Sheet '{out_cfg.sheet}' 不存在于模板中")
        ])

    ws = wb[out_cfg.sheet]
    header_row = [cell.value for cell in ws[1]]  # 第 1 行所有单元格

    # 首行不能为空
    if all(v is None for v in header_row):
        raise ConfigError(config_path=template_path, errors=[
            ConfigErrorItem(field="output.config.sheet", message=f"模板 Sheet '{out_cfg.sheet}' 首行为空")
        ])

    # 检查 target 列是否都在表头中
    errors = []
    for i, cm in enumerate(out_cfg.columns):
        if cm.target not in header_row:
            errors.append(ConfigErrorItem(
                field=f"output.config.columns[{i}].target",
                message=f"列 '{cm.target}' 不在模板首行中，可用列: {header_row}"
            ))

    wb.close()

    if errors:
        raise ConfigError(config_path=template_path, errors=errors)
```

### 2.7 配置错误模型

```
class ConfigErrorItem(BaseModel):
    """单个配置错误项"""
    field: str       # 出错的字段路径，如 "inputs[0].table"
    message: str     # 人类可读的错误描述
```

---

## 3. 模块详细设计：插件基类与注册中心

### 3.1 Plugin 基类设计

> **设计说明**: HLD 中 Plugin 基类声明了 `name: str`，但在 Python 中这会产生歧义——如果 `name` 没有默认值，`plugin = plugin_cls()` 会在 `__init__` 时报错。详细设计中不在基类体声明 `name`，改为由引擎实例化后通过属性注入设置，接口文档明确列出注入属性。

```
# src/pipeforge/plugins/base.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from pipeforge.core.context import Context

C = TypeVar("C", bound=BaseModel)


class Plugin(ABC, Generic[C]):
    """
    所有插件的抽象基类。

    由引擎注入的属性（不在 __init__ 中设置）:
      - name: str        插件标识名（来自 config.plugin）
      - label: str       人类可读名称（来自 config.name，Output 插件为 ""）

    子类特有用注入属性:
      - InputPlugin.table_name: str  数据写入的目标表名
    """

    # --- 子类必须实现的抽象方法 ---

    @classmethod
    @abstractmethod
    def config_model(cls) -> type[C]:
        """返回该插件的配置 Pydantic 模型"""
        ...

    @abstractmethod
    def execute(self, context: Context, config: C) -> None:
        """
        执行插件逻辑。

        参数:
          context: 执行上下文（提供 db、logger）
          config:  已校验且已注入运行时参数的配置模型实例
        """
        ...


class InputPlugin(Plugin[C], ABC):
    """输入插件基类"""

    # 引擎注入
    table_name: str


class ProcessorPlugin(Plugin[C], ABC):
    """处理插件基类 — MVP 与 Plugin 相同，预留扩展"""
    pass


class OutputPlugin(Plugin[C], ABC):
    """输出插件基类"""
    pass
```

### 3.2 注册中心

```
# src/pipeforge/core/registry.py

from typing import Type

from pipeforge.plugins.base import Plugin

# 合法插件类型
PLUGIN_TYPE_INPUT = "input"
PLUGIN_TYPE_PROCESSOR = "processor"
PLUGIN_TYPE_OUTPUT = "output"


class PluginNotFoundError(Exception):
    """插件未找到"""
    def __init__(self, name: str, plugin_type: str):
        self.name = name
        self.plugin_type = plugin_type
        super().__init__(f"插件未找到: type={plugin_type}, name={name}")


class PluginRegistry:
    """全局插件注册中心"""

    _plugins: dict[tuple[str, str], type[Plugin]] = {}

    @classmethod
    def register(cls, name: str, plugin_type: str, plugin_cls: type[Plugin]) -> None:
        """
        注册插件。

        参数:
          name: 插件标识名（如 "excel", "sql"）
          plugin_type: 插件类型（"input" | "processor" | "output"）
          plugin_cls: 插件类（必须是 Plugin 的子类）
        """
        key = (name, plugin_type)
        if key in cls._plugins:
            # 重复注册 → 报错，防止静默覆盖
            existing = cls._plugins[key].__name__
            raise ValueError(
                f"插件注册冲突: type={plugin_type}, name={name} "
                f"已被 {existing} 注册，尝试再次注册 {plugin_cls.__name__}"
            )
        cls._plugins[key] = plugin_cls

    @classmethod
    def get(cls, name: str, plugin_type: str) -> type[Plugin]:
        """
        获取插件类。

        参数:
          name: 插件标识名
          plugin_type: 插件类型

        返回:
          插件类（Plugin 的子类）

        抛出:
          PluginNotFoundError: 未找到对应插件
        """
        key = (name, plugin_type)
        if key not in cls._plugins:
            raise PluginNotFoundError(name, plugin_type)
        return cls._plugins[key]

    @classmethod
    def list(cls, plugin_type: str | None = None) -> list[str]:
        """列出已注册的插件名。可按类型过滤。"""
        result = []
        for (name, ptype) in cls._plugins:
            if plugin_type is None or ptype == plugin_type:
                result.append(name)
        return result

    @classmethod
    def clear(cls) -> None:
        """清空注册中心（仅测试使用）"""
        cls._plugins.clear()


def register_plugin(name: str, plugin_type: str):
    """
    插件注册装饰器。

    用法:
      @register_plugin("excel", "input")
      class ExcelInputPlugin(InputPlugin[ExcelInputConfig]):
          ...
    """
    def decorator(cls: type[Plugin]) -> type[Plugin]:
        PluginRegistry.register(name, plugin_type, cls)
        return cls
    return decorator
```

### 3.3 插件导入策略

```
# src/pipeforge/plugins/input/__init__.py
from pipeforge.plugins.input.excel import ExcelInputPlugin  # noqa: F401

# src/pipeforge/plugins/processor/__init__.py
from pipeforge.plugins.processor.sql import SqlProcessorPlugin  # noqa: F401

# src/pipeforge/plugins/output/__init__.py
from pipeforge.plugins.output.excel import ExcelOutputPlugin  # noqa: F401

# src/pipeforge/plugins/__init__.py
from pipeforge.plugins.input import *    # noqa: F401, F403
from pipeforge.plugins.processor import *  # noqa: F401, F403
from pipeforge.plugins.output import *   # noqa: F401, F403
```

插件模块在 import 时通过 `@register_plugin` 装饰器自动注册到 PluginRegistry。引擎只需 `import pipeforge.plugins` 即可确保所有内置插件已注册。添加新插件时，只需在对应 `__init__.py` 中添加一行 import。

---

## 4. 模块详细设计：SQLite 管理器

### 4.1 接口定义

```
# src/pipeforge/core/sqlite.py

import sqlite3
import tempfile
from pathlib import Path
from contextlib import contextmanager
from typing import Iterator


class SQLiteManager:
    """
    SQLite 临时数据库管理器。

    每个 Pipeline 执行创建一个新的临时 .db 文件。
    """

    db_path: str       # 临时文件路径
    _conn: sqlite3.Connection

    def __init__(self):
        """创建临时数据库文件"""
        # tempfile.NamedTemporaryFile 保证文件名唯一
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False, prefix="pipeforge_")
        self.db_path = tmp.name
        tmp.close()  # 关闭文件句柄，sqlite3 会自己打开

        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row  # 查询结果可通过列名访问

    # --- 表操作 ---

    def create_table(self, table_name: str, columns: list[str]) -> None:
        """
        用动态列名创建表。

        参数:
          table_name: 表名
          columns: 列名列表，所有列类型均为 TEXT

        实现:
          CREATE TABLE IF NOT EXISTS {table_name} (
              "{col[0]}" TEXT,
              "{col[1]}" TEXT,
              ...
          )
        """
        cols_def = ", ".join(f'"{c}" TEXT' for c in columns)
        sql = f'CREATE TABLE "{table_name}" ({cols_def})'
        self._conn.execute(sql)
        self._conn.commit()

    # --- 数据写入 ---

    def insert_row(self, table_name: str, row: tuple) -> None:
        """
        插入单行数据。

        参数:
          table_name: 目标表名
          row: 数据元组，长度必须与表的列数一致
        """
        placeholders = ", ".join("?" for _ in row)
        sql = f'INSERT INTO "{table_name}" VALUES ({placeholders})'
        self._conn.execute(sql, row)

    # --- 查询 ---

    def execute(self, sql: str) -> sqlite3.Cursor:
        """
        执行任意 SQL 语句（用于 processor 和 output）。

        返回:
          sqlite3.Cursor（可用于迭代结果）
        """
        return self._conn.execute(sql)

    def query(self, sql: str) -> list[sqlite3.Row]:
        """
        执行 SELECT 查询，返回全部结果。

        返回:
          list[sqlite3.Row]（每行可通过列名访问）
        """
        cursor = self._conn.execute(sql)
        return cursor.fetchall()

    def get_columns(self, table_name: str) -> list[str]:
        """
        获取表的所有列名。

        通过 PRAGMA table_info 查询。
        """
        rows = self._conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        return [row["name"] for row in rows]

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        row = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()
        return row is not None

    def get_user_tables(self) -> list[str]:
        """
        获取所有用户创建的表名（排除 sqlite_ 内部表）。

        用于 ProcessorStats.tables_created 的计算——
        比较 SQL 执行前后的 sqlite_master 差异。详见 §6.3。
        """
        rows = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return [r["name"] for r in rows]

    # --- 事务 ---

    @contextmanager
    def transaction(self):
        """
        事务上下文管理器。

        用法:
          with db.transaction():
              for row in rows:
                  db.insert_row(table, row)
          # 退出时自动 commit，异常时自动 rollback
        """
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    # --- 生命周期 ---

    def close(self) -> None:
        """关闭数据库连接"""
        self._conn.close()

    def cleanup_file(self) -> None:
        """删除临时数据库文件"""
        Path(self.db_path).unlink(missing_ok=True)
```

### 4.2 临时文件生命周期

```
创建时机: 引擎 execute() 方法中创建 SQLiteManager 实例
保留时机: 任何阶段失败（默认）或成功执行（用户决定）
清理时机: 用户指定 --cleanup 且执行成功，或用户手动删除

详细流程见 §6.1。
```

---

## 5. 模块详细设计：执行上下文

### 5.1 完整模型定义

```
# src/pipeforge/core/context.py

from pydantic import BaseModel
from pipeforge.core.sqlite import SQLiteManager

# ============================================================
# 统计模型
# ============================================================

class InputStats(BaseModel):
    name: str            # 输入名称（来自 inputs[].name）
    rows_loaded: int     # 载入行数
    elapsed_ms: float    # 耗时（毫秒）


class ProcessorStats(BaseModel):
    name: str                   # 处理器名称（来自 processors[].name）
    tables_created: list[str]   # 实际创建的表名（从 sqlite_master 查询）
    elapsed_ms: float           # 耗时（毫秒）


class OutputStats(BaseModel):
    rows_written: int    # 写入行数
    file_path: str       # 输出文件完整路径
    elapsed_ms: float    # 耗时（毫秒）


class ExecutionResult(BaseModel):
    inputs: dict[str, InputStats]            # key = inputs[].name
    processors: list[ProcessorStats]
    output: OutputStats | None = None
    warnings: list[str] = []                 # 执行过程中的警告

    # 调试信息
    db_path: str = ""                        # 临时数据库文件路径

# ============================================================
# 执行上下文
# ============================================================

class Context:
    """
    执行上下文 — 在引擎 execute() 中创建，贯穿整个 Pipeline 生命周期。

    属性:
      db: SQLiteManager        临时数据库管理器
      params: dict             运行时参数字典（key = param_key, value = 文件路径等）
      yaml_dir: str            YAML 配置文件所在目录（用于解析模板路径等）
      scene_name: str          场景名称（用于文件名模板变量替换）
      logger: Logger           日志记录器
      result: ExecutionResult  执行结果（引擎在各阶段填充）
      output_path: str         输出文件完整路径（由 output 插件设置，引擎用于统计）
    """

    def __init__(self, db: SQLiteManager, params: dict[str, str], yaml_dir: str, scene_name: str):
        self.db = db
        self.params = params
        self.yaml_dir = yaml_dir
        self.scene_name = scene_name
        self.logger = Logger()
        self.result = ExecutionResult()
        self.output_path = ""

# ============================================================
# Logger
# ============================================================

class Logger:
    """
    简单日志记录器 — 引擎内部使用，不直接接触终端 I/O。

    记录结构化日志条目，CLI 层可通过 result.warnings / verbose 标志获取。
    """
    _logs: list[dict]

    def __init__(self):
        self._logs = []

    def info(self, message: str) -> None:
        self._logs.append({"level": "INFO", "message": message})

    def warning(self, message: str) -> None:
        self._logs.append({"level": "WARNING", "message": message})

    def error(self, message: str) -> None:
        self._logs.append({"level": "ERROR", "message": message})

    def get_warnings(self) -> list[str]:
        return [log["message"] for log in self._logs if log["level"] == "WARNING"]

    def get_logs(self, level: str | None = None) -> list[dict]:
        if level:
            return [log for log in self._logs if log["level"] == level]
        return list(self._logs)
```

---

## 6. 模块详细设计：Pipeline 引擎

### 6.1 引擎完整接口

```
# src/pipeforge/core/engine.py

import time
from pathlib import Path
from typing import Type

from pipeforge.config.loader import load_yaml_config, validate_table_names, validate_template_columns
from pipeforge.config.models import SceneConfig
from pipeforge.core.registry import PluginRegistry, PluginNotFoundError, PLUGIN_TYPE_INPUT, PLUGIN_TYPE_PROCESSOR, PLUGIN_TYPE_OUTPUT
from pipeforge.core.context import Context, InputStats, ProcessorStats, OutputStats
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.plugins.base import Plugin, InputPlugin, ProcessorPlugin, OutputPlugin

# 确保所有插件已注册
import pipeforge.plugins  # noqa: F401


class RequiredParam(BaseModel):
    """引擎与 CLI 之间的参数契约"""
    key: str             # param_key
    label: str           # 人类可读名称
    description: str = ""


class PipelineEngine:
    config_path: str                  # YAML 文件路径
    _config: SceneConfig | None       # 解析后的配置
    _yaml_dir: str                    # YAML 文件所在目录
    _warnings: list[str]              # 配置加载期警告

    def __init__(self, config_path: str):
        self.config_path = config_path
        self._config = None
        self._yaml_dir = str(Path(config_path).resolve().parent)
        self._warnings = []
```

### 6.2 load_config()

```
    def load_config(self) -> None:
        """
        加载并校验配置。

        步骤:
        1. load_yaml_config() — YAML 解析 + Pydantic 校验 + 未知字段检测
        2. validate_table_names() — 表名冲突检测
        3. validate_template_columns() — 模板列校验
        """
        self._config, self._warnings = load_yaml_config(self.config_path)
        validate_table_names(self._config, self._yaml_dir)
        validate_template_columns(self._config, self._yaml_dir)
```

### 6.3 required_params()

```
    def required_params(self) -> list[RequiredParam]:
        """
        声明该配置需要的运行时参数。

        遍历所有 inputs，收集 param_key，生成 RequiredParam 列表。
        CLI 据此收集用户输入。
        """
        if self._config is None:
            raise RuntimeError("请先调用 load_config()")

        result = []
        for inp in self._config.inputs:
            description = ""
            if inp.plugin == "excel":
                description = f"请提供 {inp.config.sheet} 的数据文件"
            result.append(RequiredParam(
                key=inp.param_key,
                label=inp.name,
                description=description,
            ))
        return result
```

### 6.4 execute() 主流程伪代码

```
    def execute(self, params: dict[str, str], cleanup: bool = False) -> ExecutionResult:
        """
        执行流水线。

        参数:
          params: 运行时参数字典（key = param_key, value = 文件路径等）
          cleanup: 执行成功后是否清理临时 .db

        返回:
          ExecutionResult（含各阶段统计和警告）
        """
        if self._config is None:
            raise RuntimeError("请先调用 load_config()")

        config = self._config

        # ------- 阶段 0: 初始化 -------
        db = SQLiteManager()                              # 创建临时数据库
        context = Context(
            db=db,
            params=params,
            yaml_dir=self._yaml_dir,
            scene_name=config.scene.name,
        )

        # 注入配置加载期的警告
        context.result.warnings = list(self._warnings)

        context.logger.info(f"临时数据库: {db.db_path}")
        context.logger.info(f"场景: {config.scene.name}")

        try:
            # ------- 阶段 1: Input -------
            for inp_spec in config.inputs:
                stats = self._execute_input(inp_spec, context)
                context.result.inputs[inp_spec.name] = stats

            # ------- 阶段 2: Process -------
            # MVP: 只执行第一个 processor（v0.2 遍历全部）
            for proc_spec in config.processors[:1]:
                stats = self._execute_processor(proc_spec, context)
                context.result.processors.append(stats)

            # ------- 阶段 3: Output -------
            if config.output is not None:
                stats = self._execute_output(config.output, context)
                context.result.output = stats

        except PipelineError:
            # 运行时错误，保留 .db
            context.result.db_path = db.db_path
            raise
        except Exception as e:
            # 未预期异常，包装为 PipelineError
            context.result.db_path = db.db_path
            raise PipelineError(
                stage="未知",
                error_type=type(e).__name__,
                message=str(e),
                db_path=db.db_path,
            )

        # ------- 成功 -------
        context.result.db_path = db.db_path

        if cleanup:
            db.cleanup_file()

        db.close()
        return context.result
```

### 6.5 插件实例化流程详细伪代码

```
    def _instantiate_plugin(
        self,
        spec: InputSpec | ProcessorSpec | OutputSpec,
        plugin_type: str,
        resolved_config: BaseModel,
    ) -> Plugin:
        """
        插件实例化 + 属性注入。

        步骤:
        1. 从注册中心获取插件类
        2. 实例化（无参构造）
        3. 注入 name / label
        4. 注入类型特有属性
        """
        # 步骤 1: 获取插件类
        try:
            plugin_cls = PluginRegistry.get(spec.plugin, plugin_type)
        except PluginNotFoundError as e:
            raise ConfigError(config_path=self.config_path, errors=[
                ConfigErrorItem(
                    field=f"{plugin_type}.plugin",
                    message=f"插件 '{spec.plugin}' (type={plugin_type}) 未注册。"
                           f"已注册的 {plugin_type} 插件: {PluginRegistry.list(plugin_type)}"
                )
            ])

        # 步骤 2: 实例化
        plugin = plugin_cls()

        # 步骤 3: 注入 name 和 label
        plugin.name = spec.plugin

        # 区分三种类型注入 label:
        # - InputSpec 和 ProcessorSpec 有 name 字段
        # - OutputSpec 没有 name 字段 → label 保持默认 ""
        if hasattr(spec, "name"):
            plugin.label = spec.name

        # 步骤 4: InputPlugin 特有注入
        if isinstance(plugin, InputPlugin):
            plugin.table_name = spec.table  # type: ignore[attr-defined]

        return plugin
```

### 6.6 参数注入详细伪代码

```
    def _resolve_input_config(
        self,
        spec: InputSpec,
        context: Context,
    ) -> ExcelInputConfig:
        """
        解析 Input 配置 + 注入运行时参数。

        步骤:
        1. 获取配置模型（此时 file 字段为 None）
        2. 从 context.params 中根据 param_key 获取文件路径
        3. 校验文件路径不为空
        4. 将文件路径赋值给 config.file
        """
        config = spec.config  # ExcelInputConfig, file 为 None

        # 从 params 获取文件路径
        file_path = context.params.get(spec.param_key)
        if not file_path:
            raise PipelineError(
                stage="输入",
                error_type="MissingParameter",
                message=f"缺少运行时参数 '{spec.param_key}'（{spec.name}）",
                db_path=context.db.db_path,
                hint=f"请通过 --param {spec.param_key}=<文件路径> 或交互式提示提供",
            )

        # 注入
        config.file = file_path
        return config
```

### 6.7 _execute_input 详细伪代码

```
    def _execute_input(self, spec: InputSpec, context: Context) -> InputStats:
        """
        执行单个输入插件。

        步骤:
        1. 解析配置 + 注入运行时参数
        2. 实例化插件
        3. 调用 plugin.execute(context, resolved_config)
        4. 捕获异常，包装为 PipelineError
        """
        start = time.perf_counter()

        try:
            resolved_config = self._resolve_input_config(spec, context)
            plugin = self._instantiate_plugin(
                spec, PLUGIN_TYPE_INPUT, resolved_config
            )
            plugin.execute(context, resolved_config)

        except PipelineError:
            raise  # 直接上抛
        except FileNotFoundError as e:
            raise PipelineError(
                stage="输入",
                error_type="FileNotFoundError",
                message=str(e),
                db_path=context.db.db_path,
                hint="请检查文件路径是否正确",
            )
        except PermissionError as e:
            raise PipelineError(
                stage="输入",
                error_type="PermissionError",
                message=str(e),
                db_path=context.db.db_path,
                hint="文件可能被其他程序占用，请关闭后重试",
            )
        except Exception as e:
            raise PipelineError(
                stage="输入",
                error_type=type(e).__name__,
                message=str(e),
                db_path=context.db.db_path,
            )

        elapsed_ms = (time.perf_counter() - start) * 1000

        row_count = context.db._conn.execute(
            f'SELECT COUNT(*) FROM "{spec.table}"'
        ).fetchone()[0]

        return InputStats(
            name=spec.name,
            rows_loaded=row_count,
            elapsed_ms=round(elapsed_ms, 2),
        )
```

### 6.8 _execute_processor 详细伪代码

```
    def _execute_processor(self, spec: ProcessorSpec, context: Context) -> ProcessorStats:
        """
        执行 SQL 处理器。

        步骤:
        1. 记录 SQL 执行前的表列表
        2. 实例化插件 + 调用 execute()
        3. 记录 SQL 执行后的表列表
        4. 对比得到新创建的表名

        关键: ProcessorStats.tables_created 从 sqlite_master 查询得到，
              保证反映实际执行结果，而非依赖配置声明。
        """
        start = time.perf_counter()

        tables_before = set(context.db.get_user_tables())

        resolved_config = spec.config  # SqlProcessorConfig
        plugin = self._instantiate_plugin(spec, PLUGIN_TYPE_PROCESSOR, resolved_config)

        try:
            plugin.execute(context, resolved_config)
        except sqlite3.OperationalError as e:
            raise PipelineError(
                stage="处理",
                error_type="SQLError",
                message=str(e),
                db_path=context.db.db_path,
                hint="请检查 SQL 语法和引用的表名是否正确",
            )

        tables_after = set(context.db.get_user_tables())
        tables_created = list(tables_after - tables_before)

        elapsed_ms = (time.perf_counter() - start) * 1000

        return ProcessorStats(
            name=spec.name,
            tables_created=tables_created,
            elapsed_ms=round(elapsed_ms, 2),
        )
```

### 6.9 _execute_output 详细伪代码

```
    def _execute_output(self, spec: OutputSpec, context: Context) -> OutputStats:
        """
        执行输出插件。

        步骤:
        1. 校验 source_table 在数据库中确实存在
        2. 校验 source 列在查询结果中存在
        3. 实例化插件 + 调用 execute()
        """
        start = time.perf_counter()

        # 校验 source_table 存在（防御性检查，配置阶段已保证 output_tables 声明）
        if not context.db.table_exists(spec.config.source_table):
            raise PipelineError(
                stage="输出",
                error_type="TableNotFound",
                message=f"表 '{spec.config.source_table}' 在数据库中不存在",
                db_path=context.db.db_path,
                hint="可能原因: processor SQL 实际创建的表名与 output_tables 声明不一致",
            )

        # 校验 source 列存在
        db_columns = context.db.get_columns(spec.config.source_table)
        missing_sources = []
        for cm in spec.config.columns:
            if cm.source not in db_columns:
                missing_sources.append(cm.source)

        if missing_sources:
            raise PipelineError(
                stage="输出",
                error_type="ColumnNotFound",
                message=f"列 {missing_sources} 在表 '{spec.config.source_table}' 中不存在。可用列: {db_columns}",
                db_path=context.db.db_path,
                hint="请检查 columns[].source 是否与 SQL 查询结果的列名一致",
            )

        resolved_config = spec.config
        plugin = self._instantiate_plugin(spec, PLUGIN_TYPE_OUTPUT, resolved_config)

        try:
            plugin.execute(context, resolved_config)
        except Exception as e:
            if isinstance(e, PipelineError):
                raise
            raise PipelineError(
                stage="输出",
                error_type=type(e).__name__,
                message=str(e),
                db_path=context.db.db_path,
            )

        elapsed_ms = (time.perf_counter() - start) * 1000

        # 输出文件路径由插件计算并存入 context.output_path

        row_count = context.db._conn.execute(
            f'SELECT COUNT(*) FROM "{spec.config.source_table}"'
        ).fetchone()[0]

        return OutputStats(
            rows_written=row_count,
            file_path=context.output_path,
            elapsed_ms=round(elapsed_ms, 2),
        )
```

---

## 7. 模块详细设计：Excel 输入插件

### 7.1 配置模型

```
# ExcelInputConfig 已在 §2.2 定义
# 关键字段:
#   sheet: str = "Sheet1"    工作表名
#   file: str | None = None  文件路径（引擎在 execute 前注入）
```

### 7.2 插件实现

```
# src/pipeforge/plugins/input/excel.py

from openpyxl import load_workbook

from pipeforge.core.registry import register_plugin, PLUGIN_TYPE_INPUT
from pipeforge.plugins.base import InputPlugin
from pipeforge.config.models import ExcelInputConfig


@register_plugin("excel", PLUGIN_TYPE_INPUT)
class ExcelInputPlugin(InputPlugin[ExcelInputConfig]):

    @classmethod
    def config_model(cls) -> type[ExcelInputConfig]:
        return ExcelInputConfig

    def execute(self, context: Context, config: ExcelInputConfig) -> None:
        # 步骤 1: 校验文件
        if not config.file.endswith(".xlsx"):
            raise PipelineError(
                stage="输入",
                error_type="UnsupportedFormat",
                message=f"不支持的文件格式: {config.file}，仅支持 .xlsx",
            )

        # 步骤 2: 读取 Excel
        columns, rows = read_excel_rows(config.file, config.sheet)

        # 步骤 3: 建表
        context.db.create_table(self.table_name, columns)

        # 步骤 4: 事务写入
        with context.db.transaction():
            for row in rows:
                context.db.insert_row(self.table_name, row)
```

### 7.3 read_excel_rows 算法

```
def read_excel_rows(file_path: str, sheet: str) -> tuple[list[str], Iterator[tuple]]:
    """
    读取 Excel 数据，返回 (列名列表, 数据行迭代器)。

    步骤:
    1. 普通模式打开工作簿
    2. 定位目标 Sheet（如果不存在则报错）
    3. 读取首行作为列名 → 校验非空
    4. 构造数据行迭代器（第 2 行起）
    """

    # 步骤 1-2
    try:
        wb = load_workbook(file_path, read_only=True)  # 输入用 read_only 减少内存
    except FileNotFoundError:
        raise  # 引擎层捕获
    except Exception as e:
        # 密码保护文件等
        raise PipelineError(
            stage="输入",
            error_type=type(e).__name__,
            message=f"无法打开文件: {e}",
        )

    if sheet not in wb.sheetnames:
        raise PipelineError(
            stage="输入",
            error_type="SheetNotFound",
            message=f"Sheet '{sheet}' 不存在。可用 Sheet: {wb.sheetnames}",
        )

    ws = wb[sheet]

    # 步骤 3: 读首行作为列名
    # 使用 iter_rows 获取第一行
    first_row_cells = list(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    if not first_row_cells or not first_row_cells[0]:
        raise PipelineError(
            stage="输入",
            error_type="EmptyHeader",
            message=f"Sheet '{sheet}' 首行为空，无法获取列名",
        )

    columns = [str(cell) if cell is not None else f"column_{i}" for i, cell in enumerate(first_row_cells[0])]

    # 步骤 4: 数据行迭代器
    def row_generator():
        for row in ws.iter_rows(min_row=2, values_only=True):
            # 跳过全空行
            if all(cell is None for cell in row):
                continue
            yield tuple(cell if cell is not None else "" for cell in row)

    return columns, row_generator()
```

### 7.4 边界情况处理

| 情况 | 处理 |
|------|------|
| 文件不存在 | 引擎层捕获 FileNotFoundError → PipelineError |
| 密码保护 | openpyxl 抛出异常 → 引擎层包装 |
| Sheet 不存在 | 插件检测 → PipelineError(stage="输入") |
| 首行为空 | 插件检测 → PipelineError(stage="输入") |
| 首行有 None 单元格 | 自动填充为 `column_N` |
| 数据行有 None 单元格 | 转换为空字符串 `""` |
| 空行（全 None） | 跳过，不写入数据库 |
| .xls 格式 | `read_only` 模式不支持旧格式，openpyxl 抛出异常 |

---

## 8. 模块详细设计：SQL 处理器插件

### 8.1 配置模型

```
# SqlProcessorConfig 已在 §2.2 定义
# 关键字段:
#   sql: str    SQL 语句
```

### 8.2 插件实现

```
# src/pipeforge/plugins/processor/sql.py

import sqlite3

from pipeforge.core.registry import register_plugin, PLUGIN_TYPE_PROCESSOR
from pipeforge.plugins.base import ProcessorPlugin
from pipeforge.config.models import SqlProcessorConfig


@register_plugin("sql", PLUGIN_TYPE_PROCESSOR)
class SqlProcessorPlugin(ProcessorPlugin[SqlProcessorConfig]):

    @classmethod
    def config_model(cls) -> type[SqlProcessorConfig]:
        return SqlProcessorConfig

    def execute(self, context: Context, config: SqlProcessorConfig) -> None:
        """
        执行 SQL。

        步骤:
        1. 执行 SQL 语句
        2. SQLite 错误由引擎层捕获包装
        """
        try:
            # executescript 支持多语句（如 CREATE TABLE + INSERT）
            context.db._conn.executescript(config.sql)
        except sqlite3.Error as e:
            # 上抛给引擎层包装为 PipelineError
            raise
```

### 8.3 设计说明

- 使用 `executescript()` 而非 `execute()`，因为配置中的 SQL 可能包含多条语句
- 错误信息中会包含 SQLite 返回的完整错误消息（含行号等），足够用户排查
- `tables_created` 的收集在引擎层完成（§6.8），通过比较 sqlite_master 快照
- 不解析 SQL 内容，不验证语义——一切依赖配置创建者负责

---

## 9. 模块详细设计：Excel 输出插件

### 9.1 配置模型

```
# ExcelOutputConfig 已在 §2.2 定义
# 关键字段:
#   template: str                             模板文件路径（相对 YAML 目录）
#   sheet: str = "Sheet1"                     目标 Sheet 名
#   output_dir: str = "./output/"             输出目录（相对 CWD）
#   source_table: str                         数据源表名
#   filename: str | None = None               文件名模板
#   columns: list[ColumnMapping]              列映射
```

### 9.2 文件名模板解析

```
import re
from datetime import datetime

# 合法变量（scene_name 由 resolve_filename 调用者传入，不在此处理）

# 文件名非法字符
_FILENAME_ILLEGAL_CHARS = re.compile(r'[\/\\\:\*\?\"\<\>\|]')


def resolve_filename(template: str | None, scene_name: str) -> str:
    """
    解析文件名模板。

    步骤:
    1. 如果没有 template，使用默认模板: "{{scene_name}}_{{date:%Y%m%d}}.xlsx"
    2. 解析所有 {{var}} 和 {{var:arg}} 占位符
    3. 替换非法文件名字符为 _

    支持的变量:
      - {{date:FORMAT}}       当前日期（Python strftime 格式）
      - {{scene_name}}        场景名称
      - {{timestamp}}         Unix 时间戳
    """
    if template is None:
        template = "{{scene_name}}_{{date:%Y%m%d}}.xlsx"

    def replace_var(match):
        expr = match.group(1)
        if ":" in expr:
            var, arg = expr.split(":", 1)
        else:
            var, arg = expr, ""

        if var == "date":
            result = datetime.now().strftime(arg)
        elif var == "scene_name":
            result = scene_name
        elif var == "timestamp":
            result = str(int(datetime.now().timestamp()))
        else:
            raise PipelineError(
                stage="输出",
                error_type="UnknownVariable",
                message=f"文件名模板中未知变量: {{{{ {var} }}}}",
                hint="可用变量: date, scene_name, timestamp",
            )

        # 替换非法文件名字符为 _
        result = _FILENAME_ILLEGAL_CHARS.sub("_", str(result))
        return result

    # 匹配 {{var}} 和 {{var:arg}}
    filename = re.sub(r'\{\{([^}]+)\}\}', replace_var, template)

    # 确保以 .xlsx 结尾
    if not filename.endswith(".xlsx"):
        filename += ".xlsx"

    return filename
```

### 9.3 插件实现主流程

```
# src/pipeforge/plugins/output/excel.py

from copy import copy
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.workbook import Workbook
from openpyxl.cell.write_only import WriteOnlyCell

from pipeforge.core.registry import register_plugin, PLUGIN_TYPE_OUTPUT
from pipeforge.plugins.base import OutputPlugin
from pipeforge.config.models import ExcelOutputConfig


@register_plugin("excel", PLUGIN_TYPE_OUTPUT)
class ExcelOutputPlugin(OutputPlugin[ExcelOutputConfig]):

    @classmethod
    def config_model(cls) -> type[ExcelOutputConfig]:
        return ExcelOutputConfig

    def execute(self, context: Context, config: ExcelOutputConfig) -> None:
        # 步骤 1: 确定路径
        template_path = _resolve_template_path(config, context.yaml_dir)
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 步骤 2: 阶段 1 — 读模板提取样式
        header_styles, column_widths, freeze_panes = _extract_template_properties(
            template_path, config.sheet
        )

        # 步骤 3: 从数据库查询数据
        source_cols = [cm.source for cm in config.columns]
        rows = context.db.query(
            f'SELECT "{'" , "'.join(source_cols)}" FROM "{config.source_table}"'
        )

        # 步骤 4: 阶段 2 — write_only 写入数据
        output_path = output_dir / resolve_filename(config.filename, context.scene_name)
        _write_output_with_styles(
            output_path, config.sheet, config.columns,
            header_styles, freeze_panes, rows
        )

        # 步骤 5: 阶段 3 — 恢复列宽
        _restore_column_widths(output_path, config.sheet, column_widths)
```

### 9.4 阶段 1: 提取模板属性

```
def _extract_template_properties(
    template_path: str, sheet_name: str
) -> tuple[list[dict], dict[str, float], str]:
    """
    阶段 1: 普通模式加载模板，提取样式和属性。

    返回:
      header_styles:  list[dict]  每个表头单元格的样式属性（font/fill/border/alignment/number_format）
      column_widths:  dict[str, float]  列宽映射（列字母 → 宽度）
      freeze_panes:   str         冻结窗格设置（如 "A2"）
    """

    wb = load_workbook(template_path)  # 普通模式
    ws = wb[sheet_name]

    # --- 提取表头行样式 ---
    header_styles = []
    for cell in ws[1]:  # 第一行所有单元格
        if cell.value is not None:
            style = {
                "font": copy(cell.font),
                "fill": copy(cell.fill),
                "border": copy(cell.border),
                "alignment": copy(cell.alignment),
                "number_format": cell.number_format,  # 字符串，无需 copy
            }
        else:
            style = {}  # 空单元格无样式
        header_styles.append(style)

    # --- 提取列宽 ---
    column_widths = {}
    for col_letter, col_dim in ws.column_dimensions.items():
        if col_dim.width is not None:
            column_widths[col_letter] = col_dim.width

    # --- 提取冻结窗格 ---
    freeze_panes = ws.freeze_panes or ""

    wb.close()
    return header_styles, column_widths, freeze_panes
```

### 9.5 阶段 2: write_only 写入数据

```
def _write_output_with_styles(
    output_path: str,
    sheet_name: str,
    columns: list[ColumnMapping],
    header_styles: list[dict],
    freeze_panes: str,
    rows: Iterator[sqlite3.Row],
) -> None:
    """
    阶段 2: write_only 模式创建新文件，写入表头和数据。

    openpyxl 关键约束:
    - freeze_panes 必须在 append() 之前设置
    - WriteOnlyCell 样式属性需 copy() 复制
    - column_dimensions 在 write_only 模式下不可用（在阶段 3 处理）
    """

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(title=sheet_name)

    # 设置冻结窗格（必须在 append 前）
    if freeze_panes:
        ws.freeze_panes = freeze_panes

    # --- 写入表头行 ---
    header_row = []
    for i, cm in enumerate(columns):
        cell = WriteOnlyCell(ws, value=cm.target)

        if i < len(header_styles) and header_styles[i]:
            style = header_styles[i]
            if "font" in style:
                cell.font = style["font"]       # 已 copy
            if "fill" in style:
                cell.fill = style["fill"]       # 已 copy
            if "border" in style:
                cell.border = style["border"]   # 已 copy
            if "alignment" in style:
                cell.alignment = style["alignment"]  # 已 copy
            if "number_format" in style:
                cell.number_format = style["number_format"]

        header_row.append(cell)

    ws.append(header_row)

    # --- 写入数据行 ---
    col_keys = [cm.source for cm in columns]
    for row in rows:
        data_row = [row[key] for key in col_keys]
        ws.append(data_row)

    wb.save(output_path)
    wb.close()
```

### 9.6 阶段 3: 恢复列宽

```
def _restore_column_widths(
    output_path: str,
    sheet_name: str,
    column_widths: dict[str, float],
) -> None:
    """
    阶段 3: 普通模式重新打开文件，设置列宽，保存。

    只在有列宽信息时执行。这个操作只修改工作表元数据，
    不遍历数据行，所以即使有 10 万行数据，性能影响也可以忽略。
    """
    if not column_widths:
        return

    wb = load_workbook(output_path)  # 普通模式
    ws = wb[sheet_name]

    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width

    wb.save(output_path)
    wb.close()
```

### 9.7 模板路径解析

```
def _resolve_template_path(config: ExcelOutputConfig, yaml_dir: str) -> str:
    """
    解析模板文件路径。

    规则: 相对于 YAML 配置文件所在目录。如果已经是绝对路径则直接使用。
    """
    template = config.template
    if Path(template).is_absolute():
        return template
    return str(Path(yaml_dir) / template)
```

### 9.8 列映射说明

```
列映射从数据库到模板的流程:

  DB 查询结果 (source) ──→ 模板列头 (target)

  columns:
    - source: 姓名    target: 姓名          # 同名映射
    - source: 部门    target: 所属部门        # 重命名映射
    - source: 出勤天数 target: 本月出勤天数    # 重命名映射

  SQL 查询:
    SELECT "姓名", "部门", "岗位", "出勤天数", "迟到次数", "考勤状态"
    FROM report_data

  target 列校验:
    - 配置加载阶段：校验 target 与模板首行匹配（§2.6）
    - 执行阶段（§6.9）：校验 source 在数据库查询结果中存在
```

---

## 10. 测试策略

### 10.1 测试架构

```
tests/
├── conftest.py              # 共享 fixtures（模板文件、示例 Excel、配置 YAML）
├── test_config_models.py    # Pydantic 模型单元测试
├── test_config_loader.py    # YAML 加载 + 校验测试
├── test_registry.py         # 注册中心单元测试
├── test_sqlite.py           # SQLiteManager 单元测试
├── test_engine.py           # 引擎集成测试
├── test_excel_input.py      # Excel 输入插件测试
├── test_sql_processor.py    # SQL 处理插件测试
├── test_excel_output.py     # Excel 输出插件测试
└── test_cli.py              # CLI 端到端测试
```

### 10.2 单元测试覆盖矩阵

| 模块 | 测试类 | 测试重点 |
|------|--------|---------|
| **config/models.py** | `TestSceneConfig` | 合法配置通过、缺必填字段报错、extra=ignore 行为 |
| | `TestExcelInputConfig` | sheet 默认值、file 可选 |
| | `TestSqlProcessorConfig` | sql 必填 |
| | `TestExcelOutputConfig` | columns 为空列表报错、filename 可选 |
| **config/loader.py** | `TestLoadYAML` | 空文件、格式错误、合法配置 |
| | `TestTableConflictDetection` | 三条规则的正常和错误路径 |
| | `TestTemplateColumnValidation` | target 匹配、不匹配、模板不存在 |
| | `TestUnknownFieldWarnings` | 顶层未知字段、子节点未知字段 |
| **core/registry.py** | `TestPluginRegistry` | 注册、获取、重复注册报错、未注册报错 |
| | `TestRegisterDecorator` | 装饰器正确设置 name 和 plugin_type |
| **core/sqlite.py** | `TestSQLiteManager` | 建表、插入、查询、事务回滚、get_user_tables |
| **core/engine.py** | `TestEngineLoadConfig` | 正常加载、配置错误 |
| | `TestEngineRequiredParams` | 从 inputs 正确提取 param_key |
| | `TestEngineParamInjection` | 参数注入到 config.file |
| | `TestEnginePluginInstantiation` | 三种类型差异、label 注入 |
| **plugins/input/excel.py** | `TestReadExcelRows` | 正常读取、首行为空、Sheet 不存在 |
| | `TestExcelInputExecute` | 表创建、数据写入、事务 |
| **plugins/processor/sql.py** | `TestSqlExecute` | 正常执行、语法错误、表不存在 |
| **plugins/output/excel.py** | `TestFilenameResolution` | date/scene_name/timestamp、默认文件名 |
| | `TestExtractTemplateProperties` | 样式提取、列宽、冻结窗格 |
| | `TestThreePhaseWrite` | 列映射、样式保留、列宽恢复 |

### 10.3 关键测试场景

#### 配置错误路径

| 场景 | 预期 |
|------|------|
| YAML 语法错误 | ConfigError，提示具体行号 |
| 缺少必填字段（如 scene.name） | ConfigError，列出缺失字段 |
| inputs[].table 重复 | ConfigError，表名冲突 |
| inputs[].table 与 output_tables 冲突 | ConfigError |
| source_table 未在 output_tables 声明 | ConfigError |
| template target 列不匹配 | ConfigError，列出模板可用列 |
| 未知字段 | Warning 日志 |
| 插件不存在 | ConfigError，列出可用插件 |

#### 运行时错误路径

| 场景 | 预期 |
|------|------|
| 输入文件不存在 | PipelineError(stage="输入")，保留 .db |
| 输入文件为 .xls 格式 | PipelineError(stage="输入") |
| 输入 Sheet 不存在 | PipelineError(stage="输入") |
| 输入首行为空 | PipelineError(stage="输入") |
| 输入文件被占用 | PipelineError(stage="输入") |
| SQL 语法错误 | PipelineError(stage="处理")，保留 .db |
| SQL 引用不存在的表 | PipelineError(stage="处理")，保留 .db |
| source 列在结果中不存在 | PipelineError(stage="输出")，保留 .db |
| 模板文件不存在 | PipelineError(stage="输出") / ConfigError |
| 输出目录无写权限 | PipelineError(stage="输出") |

#### 正常路径（集成测试）

| 场景 | 验证点 |
|------|--------|
| 单输入 + SQL + 单输出 | 完整流程通过，结果文件列映射正确 |
| 多输入 JOIN | 两个 Excel → SQL LEFT JOIN → 输出 |
| --cleanup | 执行成功后 .db 被删除 |
| --param 传参 | 跳过交互式提示 |
| 交互式提示 | 缺少 param 时正确提示 |
| 非法文件名字符替换 | scene_name 含 `/`，输出文件名已替换 |

### 10.4 测试 Fixtures

```python
# conftest.py 核心 fixtures

@pytest.fixture
def sample_xlsx(tmp_path):
    """创建示例输入 Excel（含表头 + 3 行数据）"""
    path = tmp_path / "sample.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["姓名", "部门", "工号"])
    ws.append(["张三", "技术部", "001"])
    ws.append(["李四", "市场部", "002"])
    ws.append(["王五", "技术部", "003"])
    wb.save(path)
    return str(path)

@pytest.fixture
def template_xlsx(tmp_path):
    """创建模板 Excel（含表头样式 + 列宽 + 冻结窗格）"""
    path = tmp_path / "template.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "报表"

    # 设置表头样式
    from openpyxl.styles import Font, PatternFill
    header_font = Font(bold=True, size=14)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

    for col_idx, val in enumerate(["姓名", "所属部门", "岗位", "本月出勤天数", "迟到次数", "状态"], 1):
        cell = ws.cell(row=1, column=col_idx, value=val)
        cell.font = header_font
        cell.fill = header_fill

    # 设置列宽
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 15

    # 设置冻结窗格
    ws.freeze_panes = "A2"

    wb.save(path)
    return str(path)

@pytest.fixture
def valid_yaml_config(tmp_path, sample_xlsx, template_xlsx):
    """创建合法的 YAML 配置文件"""
    # 返回 YAML 内容字符串和文件路径
    ...
```

---

## 附录 A：与高阶设计的差异汇总

| HLD 位置 | HLD 原文 | 详细设计修正 |
|----------|---------|-------------|
| §4.5 | 会保留列宽（column_dimensions） | 三阶段写入实现（write_only 不支持直接设置） |
| §4.7 | extra="ignore" 忽略未知字段 | 保留该策略，增加 warning 日志 |
| §6.1 | 两阶段写入 | 改为三阶段写入 |
| §6.1 步骤 5 | 使用 WriteOnlyCell + 样式对象 | 明确要求 `copy.copy()` 每个样式属性 |
| §6.1 步骤 7 | 恢复 column_dimensions 和 freeze_panes | freeze_panes 在 write_only 阶段设置（append 前）；column_dimensions 在阶段 3 设置 |
| §3.3 插件基类 | `name: str` 在类体中声明 | 不在基类体声明，改为由引擎属性注入（避免 Python 类变量/实例变量混淆） |
| §4.3 文件名 | 未定义场景名特殊字符处理 | 自动替换 `/\:*?"<>|` 为 `_` |
| §4.2 模板路径 | 未定义路径解析规则 | 相对于 YAML 配置文件所在目录 |
| §8 | 插件自动发现（importlib） | MVP 用显式 import |

## 附录 B：待 v0.2 细化的设计点

以下设计点在高阶设计中已有方向，但详细实现留待 v0.2：

1. **多处理器链式执行**：`processors` 列表遍历，处理器的 `output_tables` 作为下游处理器的隐式输入
2. **CSV 输入/输出**：openpyxl 的 CSV 替代方案
3. **Jinja2 模板变量**：SQL 中的变量替换，安全变量 vs 用户输入变量
4. **数据校验**：与 Pydantic schema 或 Great Expectations 集成
5. **配置迁移工具**：根据 `scene.version` 自动迁移配置结构
6. **执行日志持久化**：日志写入文件而非仅内存
7. **插件 entry_points 集成**：第三方包自动发现
8. **openpyxl 合并单元格/数据验证写入区域**的高级处理
