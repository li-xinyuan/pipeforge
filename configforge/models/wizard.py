from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional, Literal, Annotated


class SceneInfo(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    version: str = "1.0"


class ExcelInputConfig(BaseModel):
    type: Literal["excel"] = "excel"
    sheet: str = "Sheet1"


class CsvInputConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Literal["csv"] = "csv"
    delimiter: str = ","
    encoding: str = "utf-8"
    has_header: bool = Field(default=True, alias="hasHeader")


class DatabaseInputConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Literal["database"] = "database"
    connection_id: str = Field(default="", alias="connectionId")
    connection_string: str = ""   # API layer fills this after resolving connectionId
    db_type: str = ""             # API layer fills this
    query_type: Literal["table", "sql"] = Field(default="table", alias="queryType")
    tables: list[str] = []        # max 1 element
    sql: str = ""


class InputSource(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = ""
    plugin: Literal["excel", "csv", "database"] = "excel"
    table: str = ""
    param_key: str = Field(default="", alias="paramKey")
    file_id: str = Field(default="", alias="fileId")
    config: Annotated[ExcelInputConfig | CsvInputConfig | DatabaseInputConfig, Field(discriminator="type")] = Field(
        default_factory=ExcelInputConfig
    )


class ProcessorConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = ""
    plugin: Literal["sql", "python"] = "sql"
    sql: str = Field(default="", alias="sql")
    script: str = Field(default="", alias="script")
    input_tables: list[str] = Field(default=[], alias="inputTables")
    output_tables: list[str] = Field(default=[], alias="outputTables")

    @model_validator(mode="after")
    def validate_plugin_fields(self):
        # Only validate when the processor has meaningful configuration
        # (has output_tables or non-empty sql/script).
        # Empty ProcessorConfig (default/placeholder) is always valid.
        has_config = bool(self.output_tables) or bool(self.sql.strip()) or bool(self.script.strip())
        if not has_config:
            return self

        if self.plugin == "sql" and not self.sql.strip():
            raise ValueError("SQL 步骤的 sql 字段不能为空")
        if self.plugin == "python" and not self.script.strip():
            raise ValueError("Python 步骤的 script 字段不能为空")
        return self


class ColumnMappingItem(BaseModel):
    source: str
    target: str


class ExcelOutputConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Literal["excel"] = "excel"
    template: str = ""
    sheet: str = "Sheet1"
    output_dir: str = Field(default="./output/", alias="outputDir")
    source_table: str = Field(default="", alias="sourceTable")
    filename: str
    columns: list[ColumnMappingItem] = []


class CsvOutputConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Literal["csv"] = "csv"
    source_table: str = Field(default="", alias="sourceTable")
    output_dir: str = Field(default="./output/", alias="outputDir")
    filename: str
    delimiter: str = ","
    encoding: str = "utf-8"
    columns: list[ColumnMappingItem] = []


class OutputTarget(BaseModel):
    plugin: Literal["excel", "csv"] = "excel"
    config: Annotated[ExcelOutputConfig | CsvOutputConfig, Field(discriminator="type")]


class WizardState(BaseModel):
    current_step: int = 1
    scene: SceneInfo = Field(default_factory=lambda: SceneInfo(name="Untitled Scene"))
    inputs: list[InputSource] = []
    processor: ProcessorConfig = Field(
        default_factory=lambda: ProcessorConfig(sql="", output_tables=[])
    )
    processors: list[ProcessorConfig] = []
    output: Optional[OutputTarget] = None
    uploaded_files: dict[str, dict] = {}


class SceneInitRequest(BaseModel):
    file_ids: list[str]


class SceneInitResponse(BaseModel):
    scene: SceneInfo


class InputInferRequest(BaseModel):
    file_id: str
    type: str = "excel"  # "excel" or "csv"


class ColumnInfo(BaseModel):
    name: str
    sample_values: list[str] = []


class InputInferResponse(BaseModel):
    columns: list[ColumnInfo]
    suggested_table: str
    suggested_param_key: str


class OutputInferRequest(BaseModel):
    inputs: list[InputSource]


class OutputInferResponse(BaseModel):
    suggested_columns: list[ColumnMappingItem]


class GenerateRequest(BaseModel):
    state: WizardState


class GenerateResponse(BaseModel):
    yaml: str
    template: Optional[bytes] = None


class ColumnPreview(BaseModel):
    columns: list[str]
    rows: list[list[str]]


class PreviewRequest(BaseModel):
    file_id: str
    sheet: Optional[str] = None


class FileUploadResponse(BaseModel):
    file_id: str
    original_name: str


class SqlExecuteRequest(BaseModel):
    sql: str
    table_mapping: dict[str, str]  # table_name -> file_id


class SqlExecuteResponse(BaseModel):
    columns: list[str]
    rows: list[list[str]]


class ErrorResponse(BaseModel):
    error: str
    code: str
    recoverable: bool = True


# === Config persistence models ===

class ConfigInputMeta(BaseModel):
    name: str
    param_key: str
    plugin: str  # "excel" | "csv"


class ConfigMeta(BaseModel):
    id: str
    scene_name: str
    description: str = ""
    input_count: int
    output_type: str = ""
    version: str = "1.0"
    updated_at: str
    inputs: list[ConfigInputMeta] = []


class SaveConfigRequest(BaseModel):
    state: WizardState
    config_id: str | None = None


class SaveConfigResponse(BaseModel):
    id: str


class ExecuteConfigRequest(BaseModel):
    files: dict[str, str]  # param_key -> file_id
