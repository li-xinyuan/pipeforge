from pydantic import BaseModel, Field
from typing import Optional, Literal, Annotated


class SceneInfo(BaseModel):
    name: str
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


class InputSource(BaseModel):
    name: str
    plugin: Literal["excel", "csv"] = "excel"
    table: str
    param_key: str
    file_id: str
    config: Annotated[ExcelInputConfig | CsvInputConfig, Field(discriminator="type")] = Field(
        default_factory=ExcelInputConfig
    )


class ProcessorConfig(BaseModel):
    plugin: Literal["sql"] = "sql"
    sql: str
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


class ErrorResponse(BaseModel):
    error: str
    code: str
    recoverable: bool = True
