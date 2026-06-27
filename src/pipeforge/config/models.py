from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pipeforge.config.models_loose import (
    LooseColumnMapping,
    LooseCsvInputConfig,
    LooseCsvOutputConfig,
    LooseDatabaseOutputConfig,
    LooseDbInputConfig,
    LooseExcelInputConfig,
    LooseExcelOutputConfig,
    LooseJsonInputConfig,
    LooseParquetInputConfig,
    LoosePythonProcessorConfig,
    LooseSqlProcessorConfig,
    LooseXmlInputConfig,
)


class SceneMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    version: str = "1.0"


class ExcelInputConfig(LooseExcelInputConfig):
    """限制②C：继承 loose 基类，添加 pipeforge 执行态的 file 字段。"""
    file: str | None = None


class CsvInputConfig(LooseCsvInputConfig):
    """限制②C：继承 loose 基类，添加 pipeforge 执行态的 file 字段。"""
    file: str | None = None


class DbInputConfig(LooseDbInputConfig):
    """限制②C：继承 loose 基类，connection_string 改为必填，添加 file 字段。"""
    file: str | None = None
    connection_string: str  # 必填（覆盖 loose 默认 ""）

    @model_validator(mode="after")
    def validate_tables_sql_mutual_exclusion(self):
        has_tables = len(self.tables) > 0
        has_sql = bool(self.sql.strip())
        if has_tables and has_sql:
            raise ValueError("tables 和 sql 互斥，只能二选一")
        if not has_tables and not has_sql:
            raise ValueError("tables 和 sql 必须提供一个")
        return self


class JsonInputConfig(LooseJsonInputConfig):
    """限制③C：JSON 输入源配置（reader 适配器支持执行）。限制②C：继承 loose。"""
    file: str | None = None


class XmlInputConfig(LooseXmlInputConfig):
    """限制③C：XML 输入源配置（reader 适配器支持执行）。限制②C：继承 loose。"""
    file: str | None = None


class ParquetInputConfig(LooseParquetInputConfig):
    """限制③C：Parquet 输入源配置（reader 适配器支持执行）。限制②C：继承 loose。"""
    file: str | None = None


class InputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    plugin: str
    table: str
    param_key: str
    config: Annotated[
        ExcelInputConfig | CsvInputConfig | DbInputConfig | JsonInputConfig | XmlInputConfig | ParquetInputConfig,
        Field(discriminator="type"),
    ]

    @field_validator("param_key")
    @classmethod
    def param_key_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("param_key must not be empty")
        return v


class SqlProcessorConfig(LooseSqlProcessorConfig):
    """限制②C：继承 loose 基类，sql 改为必填。"""
    # 必填（覆盖 loose 默认 ""）；json_schema_extra 需重新声明（Finding 2: 不合并继承）
    sql: str = Field(json_schema_extra={"x-ui-widget": "code-editor"})

    @field_validator("sql")
    @classmethod
    def sql_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("sql must not be empty")
        return v


class PythonProcessorConfig(LoosePythonProcessorConfig):
    """限制②C：继承 loose 基类，script 改为必填。"""
    # 必填（覆盖 loose 默认 ""）；json_schema_extra 需重新声明（Finding 2: 不合并继承）
    script: str = Field(json_schema_extra={"x-ui-widget": "code-editor"})

    @field_validator("script")
    @classmethod
    def script_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("script must not be empty")
        return v


class ProcessorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    plugin: str
    input_tables: list[str] = []
    output_tables: list[str] = []
    config: Annotated[SqlProcessorConfig | PythonProcessorConfig, Field(discriminator="type")]
    checkpoints: list[CheckRule] = []


class ColumnMapping(LooseColumnMapping):
    """限制②C：继承 loose 基类，source/target 改为必填。"""
    source: str  # 必填（覆盖 loose 默认 ""）
    target: str  # 必填（覆盖 loose 默认 ""）

    @field_validator("source")
    @classmethod
    def source_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source column name must not be empty")
        return v


class ExcelOutputConfig(LooseExcelOutputConfig):
    """限制②C：继承 loose 基类，template/source_table/columns 改为必填。

    注意（spike Finding 2）：source_table 在 loose 父类带 alias="sourceTable"，
    覆盖为必填时必须重新声明 alias，否则继承链丢失 alias。
    """
    template: str  # 必填（覆盖 loose 默认 ""）
    source_table: str = Field(alias="sourceTable")  # 必填 + 重新声明 alias
    columns: list[ColumnMapping]  # 必填（覆盖 loose 默认 []），使用 strict 子类型

    @field_validator("columns")
    @classmethod
    def columns_not_empty(cls, v: list[ColumnMapping]) -> list[ColumnMapping]:
        return v  # Allow empty — pipeline auto-infers columns from input


class CsvOutputConfig(LooseCsvOutputConfig):
    """限制②C：继承 loose 基类，source_table/columns 改为必填。

    注意（spike Finding 2）：source_table 在 loose 父类带 alias="sourceTable"，
    覆盖为必填时必须重新声明 alias，否则继承链丢失 alias。
    """
    source_table: str = Field(alias="sourceTable")  # 必填 + 重新声明 alias
    columns: list[ColumnMapping]  # 必填（覆盖 loose 默认 []），使用 strict 子类型

    @field_validator("columns")
    @classmethod
    def columns_not_empty(cls, v: list[ColumnMapping]) -> list[ColumnMapping]:
        return v  # Allow empty — pipeline auto-infers columns from input


class DatabaseOutputConfig(LooseDatabaseOutputConfig):
    """限制②C：继承 loose 基类。所有字段在 loose 已有默认，无需覆盖字段。"""
    columns: list[ColumnMapping] = Field(default=[])  # 使用 strict 子类型保留 validator


OutputConfig = Annotated[
    ExcelOutputConfig | CsvOutputConfig | DatabaseOutputConfig,
    Field(discriminator="type")
]


class OutputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin: Literal["excel", "csv", "database"] = "excel"
    config: OutputConfig


class SceneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene: SceneMeta
    inputs: list[InputSpec] = []
    processors: list[ProcessorSpec] = []
    output: OutputSpec | None = None


# 数据检查点（v0.2：支持 6 种规则）


class RowCountRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["row_count"] = "row_count"
    table: str = ""
    min: int = 0
    max: int | None = None
    on_failure: Literal["block", "warn"] = "block"


class NullRateRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["null_rate"] = "null_rate"
    table: str = ""
    column: str = ""
    max_null_rate: float = Field(default=0.05, ge=0, le=1)
    on_failure: Literal["block", "warn"] = "block"


class UniquenessRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["uniqueness"] = "uniqueness"
    table: str = ""
    column: str = ""
    on_failure: Literal["block", "warn"] = "block"


class ValueRangeRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["value_range"] = "value_range"
    table: str = ""
    column: str = ""
    min_value: float | None = None
    max_value: float | None = None
    on_failure: Literal["block", "warn"] = "block"


class CustomSqlRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["custom_sql"] = "custom_sql"
    sql: str = ""
    result_column: str = "result"
    comparison: Literal["<", "<=", "==", "!=", ">", ">="] = "<="
    expected_value: float | None = None
    on_failure: Literal["block", "warn"] = "block"


class EnumCheckRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["enum_check"] = "enum_check"
    table: str = ""
    column: str = ""
    allowed_values: list[str] = Field(default=[])
    on_failure: Literal["block", "warn"] = "block"


CheckRule = Annotated[
    RowCountRule | NullRateRule | UniquenessRule | ValueRangeRule | CustomSqlRule | EnumCheckRule,
    Field(discriminator="type")
]


class CheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    passed: bool
    message: str
    on_failure: Literal["block", "warn"]
    checked_at: str
