from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SceneMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    version: str = "1.0"


class ExcelInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["excel"] = "excel"
    file: str | None = None
    sheet: str = "Sheet1"


class CsvInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["csv"] = "csv"
    file: str | None = None
    delimiter: str = ","
    encoding: str = "utf-8"
    has_header: bool = True


class DbInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["database"] = "database"
    connection_string: str
    db_type: str = ""
    tables: list[str] = []
    sql: str = ""

    @model_validator(mode="after")
    def validate_tables_sql_mutual_exclusion(self):
        has_tables = len(self.tables) > 0
        has_sql = bool(self.sql.strip())
        if has_tables and has_sql:
            raise ValueError("tables 和 sql 互斥，只能二选一")
        if not has_tables and not has_sql:
            raise ValueError("tables 和 sql 必须提供一个")
        return self


class JsonInputConfig(BaseModel):
    """限制③C：JSON 输入源配置（reader 适配器支持执行）。"""
    model_config = ConfigDict(extra="forbid")

    type: Literal["json"] = "json"
    file: str | None = None
    flatten_separator: str = "."


class XmlInputConfig(BaseModel):
    """限制③C：XML 输入源配置（reader 适配器支持执行）。"""
    model_config = ConfigDict(extra="forbid")

    type: Literal["xml"] = "xml"
    file: str | None = None
    row_element: str = ""


class ParquetInputConfig(BaseModel):
    """限制③C：Parquet 输入源配置（reader 适配器支持执行）。"""
    model_config = ConfigDict(extra="forbid")

    type: Literal["parquet"] = "parquet"
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


class SqlProcessorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["sql"] = "sql"
    sql: str

    @field_validator("sql")
    @classmethod
    def sql_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("sql must not be empty")
        return v


class PythonProcessorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["python"] = "python"
    script: str

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

    type: Literal["excel"] = "excel"
    template: str
    sheet: str = "Sheet1"
    output_dir: str = "./output/"
    source_table: str
    filename: str | None = None
    columns: list[ColumnMapping]

    @field_validator("columns")
    @classmethod
    def columns_not_empty(cls, v: list[ColumnMapping]) -> list[ColumnMapping]:
        return v  # Allow empty — pipeline auto-infers columns from input


class CsvOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["csv"] = "csv"
    source_table: str
    output_dir: str = "./output/"
    filename: str | None = None
    delimiter: str = ","
    encoding: str = "utf-8"
    columns: list[ColumnMapping]

    @field_validator("columns")
    @classmethod
    def columns_not_empty(cls, v: list[ColumnMapping]) -> list[ColumnMapping]:
        return v  # Allow empty — pipeline auto-infers columns from input


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
    connection_string: str = ""


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
