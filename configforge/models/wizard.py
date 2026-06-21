from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeforge.config.models import CheckRule


class SceneInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    version: str = "1.0"
    tags: list[str] = []


class ExcelInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["excel"] = "excel"
    sheet: str = "Sheet1"


class CsvInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["csv"] = "csv"
    delimiter: str = ","
    encoding: str = "utf-8"
    has_header: bool = Field(default=True, alias="hasHeader")


class DatabaseInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["database"] = "database"
    connection_id: str = Field(default="", alias="connectionId")
    connection_string: str = ""   # API layer fills this after resolving connectionId
    db_type: str = ""             # API layer fills this
    query_type: Literal["table", "sql"] = Field(default="table", alias="queryType")
    tables: list[str] = []        # max 1 element
    sql: str = ""


class JsonInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["json"] = "json"
    flatten_separator: str = "."


class XmlInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["xml"] = "xml"
    row_element: str = ""


class ParquetInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["parquet"] = "parquet"


class ApiInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["api"] = "api"
    url: str = ""
    method: Literal["GET", "POST"] = "GET"
    headers: dict[str, str] = {}
    params: dict[str, str] = {}
    body: dict | None = None
    data_path: str = ""
    pagination: Literal["none", "offset", "cursor"] = "none"
    page_size: int = 100
    max_pages: int = 10


class InputSource(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str = ""
    plugin: Literal["excel", "csv", "database", "json", "xml", "parquet", "api"] = "excel"
    table: str = ""
    param_key: str = Field(default="", alias="paramKey")
    file_id: str = Field(default="", alias="fileId")
    config: Annotated[
        ExcelInputConfig | CsvInputConfig | DatabaseInputConfig | JsonInputConfig | XmlInputConfig | ParquetInputConfig | ApiInputConfig,
        Field(discriminator="type"),
    ] = Field(default_factory=ExcelInputConfig)


class ProcessorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str = ""
    plugin: Literal["sql", "python"] = "sql"
    sql: str = Field(default="", alias="sql")
    script: str = Field(default="", alias="script")
    input_tables: list[str] = Field(default=[], alias="inputTables")
    output_tables: list[str] = Field(default=[], alias="outputTables")
    checkpoints: list[CheckRule] = Field(default=[])

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
    model_config = ConfigDict(extra="forbid")

    source: str
    target: str


class ExcelOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["excel"] = "excel"
    template: str = ""
    sheet: str = "Sheet1"
    output_dir: str = Field(default="./output/", alias="outputDir")
    source_table: str = Field(default="", alias="sourceTable")
    filename: str
    columns: list[ColumnMappingItem] = []


class CsvOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["csv"] = "csv"
    source_table: str = Field(default="", alias="sourceTable")
    output_dir: str = Field(default="./output/", alias="outputDir")
    filename: str
    delimiter: str = ","
    encoding: str = "utf-8"
    columns: list[ColumnMappingItem] = []


class DatabaseOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["database"] = "database"
    connection_id: str = Field(default="", alias="connectionId")
    target_table: str = Field(default="", alias="targetTable")
    write_mode: Literal["replace", "append", "upsert"] = Field(default="replace", alias="writeMode")
    source_table: str = Field(default="", alias="sourceTable")
    columns: list[ColumnMappingItem] = Field(default=[])
    create_table_if_not_exists: bool = Field(default=True, alias="createTableIfNotExists")
    primary_key_columns: list[str] = Field(default=[], alias="primaryKeyColumns")
    batch_size: int = Field(default=1000, ge=1, le=100000)
    connection_string: str = ""


class OutputTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin: Literal["excel", "csv", "database"] = "excel"
    config: Annotated[ExcelOutputConfig | CsvOutputConfig | DatabaseOutputConfig, Field(discriminator="type")]


class WizardState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_step: int = 1
    scene: SceneInfo = Field(default_factory=lambda: SceneInfo(name="Untitled Scene"))
    inputs: list[InputSource] = []
    processors: list[ProcessorConfig] = []
    output: OutputTarget | None = None
    uploaded_files: dict[str, dict] = {}


class SceneInitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_ids: list[str]


class SceneInitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene: SceneInfo


class InputInferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: str
    type: str = "excel"  # "excel" or "csv"


class ApiInferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = ""
    method: Literal["GET", "POST"] = "GET"
    headers: dict[str, str] = {}
    params: dict[str, str] = {}
    body: dict | None = None
    data_path: str = ""
    pagination: Literal["none", "offset", "cursor"] = "none"
    page_size: int = 100
    max_pages: int = 10


class ColumnInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    sample_values: list[str] = []


class InputInferResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: list[ColumnInfo]
    suggested_table: str
    suggested_param_key: str


class OutputInferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inputs: list[InputSource]


class OutputInferResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggested_columns: list[ColumnMappingItem]


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: WizardState


class GenerateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    yaml: str
    template: bytes | None = None


class ColumnPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: list[str]
    rows: list[list[str]]


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: str
    sheet: str | None = None
    max_rows: int | None = None


class FileUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: str
    original_name: str


class SqlExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sql: str
    table_mapping: dict[str, str]  # table_name -> file_id


class SqlExecuteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: list[str]
    rows: list[list[str]]
    total_source_rows: int = 0
    sample_rows_loaded: int = 0
    is_sampled: bool = True


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: str
    code: str
    recoverable: bool = True


# === Config persistence models ===

class ConfigInputMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    param_key: str
    plugin: str  # "excel" | "csv"


class ConfigMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    scene_name: str
    description: str = ""
    input_count: int
    output_type: str = ""
    version: str = "1.0"
    updated_at: str
    current_version: int = 1
    created_at: str = ""
    inputs: list[ConfigInputMeta] = []
    tags: list[str] = []
    input_types: list[str] = []


class SaveConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: WizardState
    config_id: str | None = None


class SaveConfigResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str


class ExecuteConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: dict[str, str]  # param_key -> file_id


class ConfigVersionMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    scene_version: str = "1.0"
    change_summary: str = ""
    created_at: str = ""
    input_count: int = 0
    processor_count: int = 0
    output_type: str = ""


class ExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = ""  # 8-char hex
    config_id: str = ""
    config_version: int | None = None
    scene_name: str = ""
    status: Literal["success", "failed"] = "success"
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    inputs_summary: list[dict] = []
    processors_summary: list[dict] = []
    output_type: str = ""
    checks_summary: list[dict] = []
    error_message: str | None = None
    output_file_name: str | None = None
    diagnosis: dict | None = None
