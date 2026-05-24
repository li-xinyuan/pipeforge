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


class InputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    plugin: str
    table: str
    param_key: str
    config: Annotated[ExcelInputConfig | CsvInputConfig | DbInputConfig, Field(discriminator="type")]

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
