from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    """Database input configuration — connection_string is resolved by API layer before engine receives it."""
    model_config = ConfigDict(extra="forbid")
    type: Literal["database"] = "database"
    db_type: str                       # "sqlite" | "mysql" | "postgresql"
    connection_string: str             # SQLAlchemy connection string, resolved from connectionId by API
    tables: list[str] = []             # max 1 element; multi-table uses separate InputSources or SQL JOIN
    sql: str = ""                      # custom SQL query (mutually exclusive with tables)


class InputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    plugin: str
    table: str
    param_key: str
    config: Annotated[ExcelInputConfig | CsvInputConfig | DbInputConfig, Field(discriminator="type")]


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


class ProcessorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    plugin: str
    output_tables: list[str] = []
    config: Annotated[SqlProcessorConfig, Field(discriminator="type")]


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
        if len(v) == 0:
            raise ValueError(
                "columns must not be empty — at least one column mapping is required"
            )
        return v


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
        if len(v) == 0:
            raise ValueError(
                "columns must not be empty — at least one column mapping is required"
            )
        return v


class OutputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin: str
    config: Annotated[ExcelOutputConfig | CsvOutputConfig, Field(discriminator="type")]


class SceneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene: SceneMeta
    inputs: list[InputSpec] = []
    processors: list[ProcessorSpec] = []
    output: OutputSpec | None = None
