from pydantic import BaseModel, Field
from typing import Optional, Literal, Annotated


class SceneInfo(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    version: str = "1.0"


class ExcelInputConfig(BaseModel):
    type: Literal["excel"] = "excel"
    sheet: str = "Sheet1"


class CsvInputConfig(BaseModel):
    type: Literal["csv"] = "csv"
    delimiter: str = ","
    encoding: str = "utf-8"
    has_header: bool = True


class DatabaseInputConfig(BaseModel):
    type: Literal["database"] = "database"
    connection_id: str = ""
    connection_string: str = ""   # API layer fills this after resolving connectionId
    db_type: str = ""             # API layer fills this
    query_type: Literal["table", "sql"] = "table"
    tables: list[str] = []        # max 1 element
    sql: str = ""


class InputSource(BaseModel):
    name: str
    plugin: Literal["excel", "csv", "database"] = "excel"
    table: str
    param_key: str
    file_id: str
    config: Annotated[ExcelInputConfig | CsvInputConfig | DatabaseInputConfig, Field(discriminator="type")] = Field(
        default_factory=ExcelInputConfig
    )


class ProcessorConfig(BaseModel):
    name: str = ""
    plugin: Literal["sql"] = "sql"
    sql: str
    input_tables: list[str] = []
    output_tables: list[str] = []


class ColumnMappingItem(BaseModel):
    source: str
    target: str


class ExcelOutputConfig(BaseModel):
    type: Literal["excel"] = "excel"
    template: str = ""
    sheet: str = "Sheet1"
    output_dir: str = "./output/"
    source_table: str
    filename: str
    columns: list[ColumnMappingItem] = []


class CsvOutputConfig(BaseModel):
    type: Literal["csv"] = "csv"
    source_table: str
    output_dir: str = "./output/"
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
