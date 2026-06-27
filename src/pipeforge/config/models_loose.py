"""Loose 基础配置模型（限制②C — 单一数据源）。

全字段可空 + camelCase alias + populate_by_name=True。
configforge 和 pipeforge strict 模型共同继承此类，消除字段定义重复。

设计要点（spike 验证通过的 3 个 findings）：
- Finding 1: ValidationError 用 alias 名 — 前端友好，CLI/日志需注意
- Finding 2: json_schema_extra 不合并继承 — 只定义在 loose 父类（Day 11-12 添加 UI hint 时）
- Finding 3: schema required/properties 用 alias 键 — 前端消费无需转换

注意：`file` 字段不放 loose（它是 pipeforge 运行时注入，非配置定义）。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LooseColumnMapping(BaseModel):
    """列映射 loose 基类。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    source: str = ""
    target: str = ""


# === Input configs ===

class LooseExcelInputConfig(BaseModel):
    """Excel 输入 loose 基类。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["excel"] = "excel"
    sheet: str = Field(
        default="Sheet1",
        json_schema_extra={"x-ui-widget": "sheet-selector"},
    )


class LooseCsvInputConfig(BaseModel):
    """CSV 输入 loose 基类。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["csv"] = "csv"
    delimiter: str = ","
    encoding: str = Field(
        default="utf-8",
        json_schema_extra={"x-ui-options-from": "encodings"},
    )
    has_header: bool = Field(default=True, alias="hasHeader")


class LooseDbInputConfig(BaseModel):
    """Database 输入 loose 基类。configforge 侧继承并添加 connection_id/query_type。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["database"] = "database"
    connection_string: str = ""
    db_type: str = ""
    tables: list[str] = []
    sql: str = ""


class LooseJsonInputConfig(BaseModel):
    """JSON 输入 loose 基类。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["json"] = "json"
    flatten_separator: str = "."


class LooseXmlInputConfig(BaseModel):
    """XML 输入 loose 基类。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["xml"] = "xml"
    row_element: str = ""


class LooseParquetInputConfig(BaseModel):
    """Parquet 输入 loose 基类。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["parquet"] = "parquet"


# === Processor configs ===

class LooseSqlProcessorConfig(BaseModel):
    """SQL 处理器 loose 基类。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["sql"] = "sql"
    sql: str = ""


class LoosePythonProcessorConfig(BaseModel):
    """Python 处理器 loose 基类。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["python"] = "python"
    script: str = ""


# === Output configs ===

class LooseExcelOutputConfig(BaseModel):
    """Excel 输出 loose 基类。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["excel"] = "excel"
    template: str = ""
    sheet: str = Field(
        default="Sheet1",
        json_schema_extra={"x-ui-widget": "sheet-selector"},
    )
    output_dir: str = Field(default="./output/", alias="outputDir")
    source_table: str = Field(default="", alias="sourceTable")
    filename: str | None = Field(
        default=None,
        json_schema_extra={"x-ui-widget": "filename-template"},
    )
    columns: list[LooseColumnMapping] = []


class LooseCsvOutputConfig(BaseModel):
    """CSV 输出 loose 基类。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["csv"] = "csv"
    source_table: str = Field(default="", alias="sourceTable")
    output_dir: str = Field(default="./output/", alias="outputDir")
    filename: str | None = Field(
        default=None,
        json_schema_extra={"x-ui-widget": "filename-template"},
    )
    delimiter: str = ","
    encoding: str = Field(
        default="utf-8",
        json_schema_extra={"x-ui-options-from": "encodings"},
    )
    columns: list[LooseColumnMapping] = []


class LooseDatabaseOutputConfig(BaseModel):
    """Database 输出 loose 基类。spike 验证目标。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["database"] = "database"
    connection_id: str = Field(
        default="",
        alias="connectionId",
        json_schema_extra={"x-ui-widget": "connection-selector"},
    )
    target_table: str = Field(default="", alias="targetTable")
    write_mode: Literal["replace", "append", "upsert"] = Field(
        default="replace",
        alias="writeMode",
        json_schema_extra={
            "x-ui-enum-labels": {
                "replace": "替换（覆盖）",
                "append": "追加",
                "upsert": "更新（upsert）",
            },
        },
    )
    source_table: str = Field(default="", alias="sourceTable")
    columns: list[LooseColumnMapping] = []
    create_table_if_not_exists: bool = Field(default=True, alias="createTableIfNotExists")
    primary_key_columns: list[str] = Field(
        default=[],
        alias="primaryKeyColumns",
        json_schema_extra={
            "x-ui-widget": "multi-select",
            "x-ui-visible-when": "writeMode == 'upsert'",
            "x-ui-options-from": "output-columns",
        },
    )
    batch_size: int = Field(default=1000, ge=1, le=100000)
    connection_string: str = ""
