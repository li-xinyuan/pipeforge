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
            raise ValueError(
                "columns must not be empty — at least one column mapping is required"
            )
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
