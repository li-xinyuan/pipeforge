# ConfigForge v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build ConfigForge — an independent Web application for guided, visual, AI-assisted creation of PipeForge pipeline configurations (Excel→SQL→Excel).

**Architecture:** Python FastAPI backend with strategy-pattern ConfigGenerators + GeneratorRegistry, serving a Vue 3 SPA frontend with 4-step wizard and Pinia state management. Backend and frontend share `pipeforge.config.models` as the interface contract. Deployed as single FastAPI process serving built static files.

**Tech Stack:** Python FastAPI + Pydantic + openpyxl | Vue 3 + Vite + TypeScript + Pinia + Vue Router + Tailwind CSS + CodeMirror

---

## File Map

```
configforge/                          # Backend
├── server.py                         # FastAPI entry, static mount
├── requirements.txt
├── core/
│   ├── registry.py                   # GeneratorRegistry
│   └── pipeline.py                   # Config generation orchestrator
├── generators/
│   ├── base.py                       # ConfigGenerator[C] base
│   ├── input/excel_input.py
│   ├── processor/sql_processor.py
│   └── output/excel_output.py
├── api/
│   ├── files.py                      # POST /api/files/upload
│   ├── preview.py                    # POST /api/preview/file
│   ├── wizard.py                     # POST /api/wizard/*
│   └── ai.py                         # POST /api/ai/suggest
├── services/
│   ├── excel_reader.py               # Read Excel: sheets, columns, sample rows
│   ├── sql_generator.py              # Template + AI SQL generation
│   ├── yaml_builder.py               # WizardState → YAML (snake_case)
│   ├── template_builder.py           # Generate .xlsx template
│   └── ai/base.py                    # LlmBackend abstract base
├── models/
│   ├── wizard.py                     # Request/response Pydantic models
│   └── ai.py                         # AI request/response models
└── tests/

configforge-web/                      # Frontend
├── package.json, vite.config.ts, tsconfig.json
├── index.html
├── src/
│   ├── main.ts, App.vue
│   ├── router/index.ts
│   ├── stores/wizard.ts              # Pinia store (single source of truth)
│   ├── composables/
│   │   ├── useWizardApi.ts           # /api/wizard/* calls
│   │   ├── useAiSuggest.ts          # /api/ai/* calls
│   │   ├── useFileUpload.ts         # Upload + preview
│   │   └── useErrorHandler.ts       # Error dispatch
│   ├── types/wizard.ts              # TypeScript interfaces
│   ├── components/
│   │   ├── common/ (StepIndicator, AiSuggestPanel, ErrorBanner, LoadingSpinner, FatalError)
│   │   ├── step1/SceneInfoForm.vue
│   │   ├── step2/ (InputSourceList, InputSourceCard, ColumnPreview)
│   │   ├── step3/ (SqlEditorTab, OutputConfigTab, ColumnMapping)
│   │   └── step4/ (YamlPreview, ExportActions)
│   └── views/ (HomeView, Step1-4 Views)
└── tests/
```

---

### Task 1: Backend project scaffold + Pydantic models

**Files:**
- Create: `configforge/requirements.txt`
- Create: `configforge/server.py`
- Create: `configforge/models/__init__.py`
- Create: `configforge/models/wizard.py`
- Create: `configforge/models/ai.py`
- Create: `configforge/core/__init__.py`

- [ ] **Step 1: Write requirements.txt**

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
python-multipart>=0.0.12
openpyxl>=3.1.0
pyyaml>=6.0
pydantic>=2.0
pipeforge @ git+https://github.com/lixinyuan/pipeforge.git
```

- [ ] **Step 2: Write Pydantic models**

`models/wizard.py`:
```python
from pydantic import BaseModel, Field
from typing import Optional, Literal

class SceneInfo(BaseModel):
    name: str
    description: str = ""
    version: str = "1.0"

class ExcelInputConfig(BaseModel):
    type: Literal["excel"] = "excel"
    sheet: str = "Sheet1"

class InputSource(BaseModel):
    name: str
    plugin: Literal["excel"] = "excel"
    table: str
    param_key: str
    file_id: str
    config: ExcelInputConfig = Field(default_factory=ExcelInputConfig)

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

class OutputTarget(BaseModel):
    plugin: Literal["excel"] = "excel"
    config: ExcelOutputConfig

class WizardState(BaseModel):
    current_step: int = 1
    scene: SceneInfo = Field(default_factory=SceneInfo)
    inputs: list[InputSource] = []
    processor: ProcessorConfig = Field(default_factory=lambda: ProcessorConfig(sql="", output_tables=[]))
    output: Optional[OutputTarget] = None
    uploaded_files: dict[str, dict] = {}

class SceneInitRequest(BaseModel):
    file_ids: list[str]

class SceneInitResponse(BaseModel):
    scene: SceneInfo

class InputInferRequest(BaseModel):
    file_id: str
    type: str = "excel"

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

class FileUploadResponse(BaseModel):
    file_id: str
    original_name: str

class ErrorResponse(BaseModel):
    error: str
    code: str
    recoverable: bool = True
```

`models/ai.py`:
```python
from pydantic import BaseModel
from typing import Literal, Optional

class AiSuggestionRequest(BaseModel):
    category: Literal["scene", "columns", "sql", "mapping"]
    context: dict  # context details vary by category

class AiSuggestionResponse(BaseModel):
    content: str
    category: str
```

- [ ] **Step 3: Write server.py skeleton**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ConfigForge", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Verify server starts**

Run: `cd configforge && python -c "from server import app; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add configforge/
git commit -m "feat: configforge backend scaffold with pydantic models"
```


### Task 2: ConfigGenerator base + GeneratorRegistry

**Files:**
- Create: `configforge/generators/__init__.py`
- Create: `configforge/generators/base.py`
- Create: `configforge/core/registry.py`
- Create: `configforge/core/__init__.py`

- [ ] **Step 1: Write the failing test**

`tests/test_registry.py`:
```python
import pytest
from generators.base import ConfigGenerator
from core.registry import GeneratorRegistry

class FakeConfig(BaseModel):
    type: str = "fake"
    name: str = ""

@GeneratorRegistry.register("fake", "input")
class FakeGenerator(ConfigGenerator[FakeConfig]):
    @classmethod
    def config_model(cls): return FakeConfig
    def infer_config(self, source: dict) -> FakeConfig:
        return FakeConfig(name=source.get("name", ""))
    def build_config(self, state: dict) -> FakeConfig:
        return FakeConfig(name=state.get("name", ""))
    def validate_config(self, config: FakeConfig) -> list[str]:
        return [] if config.name else ["name is required"]

def test_register_and_retrieve():
    cls = GeneratorRegistry.get("fake", "input")
    assert cls == FakeGenerator

def test_unregistered_raises():
    with pytest.raises(KeyError):
        GeneratorRegistry.get("nonexistent", "input")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd configforge && python -m pytest tests/test_registry.py -v`
Expected: FAIL — `ImportError: cannot import 'ConfigGenerator'`

- [ ] **Step 3: Write ConfigGenerator base**

`generators/base.py`:
```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel

C = TypeVar("C", bound=BaseModel)

class ConfigGenerator(ABC, Generic[C]):
    @classmethod
    @abstractmethod
    def config_model(cls) -> type[C]: ...

    @abstractmethod
    def infer_config(self, source: dict) -> C: ...

    @abstractmethod
    def build_config(self, wizard_state: dict) -> C: ...

    @abstractmethod
    def validate_config(self, config: C) -> list[str]: ...
```

`generators/__init__.py`:
```python
from generators.base import ConfigGenerator
```

- [ ] **Step 4: Write GeneratorRegistry**

`core/registry.py`:
```python
from typing import TypeVar
from generators.base import ConfigGenerator

T = TypeVar("T", bound=ConfigGenerator)

class GeneratorRegistry:
    _generators: dict[tuple[str, str], type[ConfigGenerator]] = {}

    @classmethod
    def register(cls, name: str, category: str):
        def decorator(generator_cls):
            cls._generators[(name, category)] = generator_cls
            return generator_cls
        return decorator

    @classmethod
    def get(cls, name: str, category: str) -> type[ConfigGenerator]:
        key = (name, category)
        if key not in cls._generators:
            raise KeyError(f"Generator '{name}' (category: {category}) not registered")
        return cls._generators[key]

    @classmethod
    def list_all(cls) -> list[tuple[str, str]]:
        return list(cls._generators.keys())

    @classmethod
    def clear(cls):
        cls._generators.clear()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd configforge && python -m pytest tests/test_registry.py -v`
Expected: PASS (2/2)

- [ ] **Step 6: Commit**

```bash
git add configforge/generators/ configforge/core/ configforge/tests/
git commit -m "feat: ConfigGenerator base class + GeneratorRegistry"
```


### Task 3: Excel reader service

**Files:**
- Create: `configforge/services/__init__.py`
- Create: `configforge/services/excel_reader.py`
- Test: `configforge/tests/test_excel_reader.py`

- [ ] **Step 1: Write the failing test**

`tests/test_excel_reader.py`:
```python
import io
import openpyxl
from services.excel_reader import read_excel_info

def make_xlsx(headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

def test_read_columns_and_sample():
    buf = make_xlsx(["姓名", "部门", "工号"], [["张三", "研发", "001"], ["李四", "产品", "002"]])
    info = read_excel_info(buf)
    assert info["columns"] == ["姓名", "部门", "工号"]
    assert len(info["sample_rows"]) == 2
    assert info["sample_rows"][0] == ["张三", "研发", "001"]

def test_read_sheet_names():
    buf = make_xlsx(["A"], [["x"]])
    info = read_excel_info(buf)
    assert "Sheet" in info["sheets"][0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd configforge && python -m pytest tests/test_excel_reader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.excel_reader'`

- [ ] **Step 3: Write implementation**

`services/excel_reader.py`:
```python
import io
import openpyxl

def read_excel_info(file_like, sheet_name=None, max_sample_rows=10):
    wb = openpyxl.load_workbook(file_like, read_only=True)
    sheets = wb.sheetnames
    ws_name = sheet_name or sheets[0]
    ws = wb[ws_name]
    rows_iter = ws.iter_rows(values_only=True)
    try:
        headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(next(rows_iter))]
    except StopIteration:
        wb.close()
        return {"sheets": sheets, "columns": [], "sample_rows": []}
    sample_rows = []
    for i, row in enumerate(rows_iter):
        if i >= max_sample_rows:
            break
        sample_rows.append([str(v) if v is not None else "" for v in row])
    wb.close()
    return {"sheets": sheets, "columns": headers, "sample_rows": sample_rows}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd configforge && python -m pytest tests/test_excel_reader.py -v`
Expected: PASS (2/2)

- [ ] **Step 5: Commit**

```bash
git add configforge/services/ configforge/tests/
git commit -m "feat: excel_reader service - read columns, sheets, sample rows"
```


### Task 4: ExcelInputGenerator

**Files:**
- Create: `configforge/generators/input/__init__.py`
- Create: `configforge/generators/input/excel_input.py`
- Test: `configforge/tests/test_input_generator.py`

- [ ] **Step 1: Write the failing test**

`tests/test_input_generator.py`:
```python
import io, pytest
from generators.input.excel_input import ExcelInputGenerator

def test_infer_config_from_excel_info():
    gen = ExcelInputGenerator()
    config = gen.infer_config({"file_id": "f1", "type": "excel", "columns": ["姓名", "部门"], "original_name": "person.xlsx"})
    assert config.type == "excel"
    assert config.sheet == "Sheet1"

def test_build_config_from_wizard_state():
    gen = ExcelInputGenerator()
    state = {"name": "人员明细", "table": "person", "param_key": "person_file", "file_id": "f1", "sheet": "人员列表"}
    config = gen.build_config(state)
    assert config.sheet == "人员列表"

def test_validate_empty_sheet_rejected():
    gen = ExcelInputGenerator()
    from models.wizard import ExcelInputConfig
    errors = gen.validate_config(ExcelInputConfig(sheet=""))
    assert any("Sheet" in str(e) for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd configforge && python -m pytest tests/test_input_generator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`generators/input/excel_input.py`:
```python
from typing import Literal
from generators.base import ConfigGenerator
from models.wizard import ExcelInputConfig
from core.registry import GeneratorRegistry

@GeneratorRegistry.register("excel", "input")
class ExcelInputGenerator(ConfigGenerator[ExcelInputConfig]):
    @classmethod
    def config_model(cls):
        return ExcelInputConfig

    def infer_config(self, source: dict) -> ExcelInputConfig:
        return ExcelInputConfig(sheet="Sheet1")

    def build_config(self, wizard_state: dict) -> ExcelInputConfig:
        return ExcelInputConfig(
            sheet=wizard_state.get("sheet", "Sheet1"),
        )

    def validate_config(self, config: ExcelInputConfig) -> list[str]:
        errors = []
        if not config.sheet or not config.sheet.strip():
            errors.append("Sheet name is required")
        return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd configforge && python -m pytest tests/test_input_generator.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Commit**

```bash
git add configforge/generators/input/ configforge/tests/
git commit -m "feat: ExcelInputGenerator - infer, build, validate"
```


### Task 5: SqlProcessorGenerator

**Files:**
- Create: `configforge/generators/processor/__init__.py`
- Create: `configforge/generators/processor/sql_processor.py`
- Test: `configforge/tests/test_processor_generator.py`

- [ ] **Step 1: Write the failing test**

`tests/test_processor_generator.py`:
```python
import pytest
from generators.processor.sql_processor import SqlProcessorGenerator
from models.wizard import ProcessorConfig

def test_build_config():
    gen = SqlProcessorGenerator()
    state = {"sql": "SELECT * FROM person", "output_tables": ["monthly_report"]}
    config = gen.build_config(state)
    assert config.sql == "SELECT * FROM person"
    assert config.output_tables == ["monthly_report"]

def test_validate_sql_syntax_error():
    gen = SqlProcessorGenerator()
    errors = gen.validate_config(ProcessorConfig(sql="SELEC * FROM", output_tables=[]))
    assert len(errors) > 0

def test_validate_passing():
    gen = SqlProcessorGenerator()
    errors = gen.validate_config(ProcessorConfig(sql="SELECT 1", output_tables=["t1"]))
    assert len(errors) == 0

def test_validate_empty_sql():
    gen = SqlProcessorGenerator()
    errors = gen.validate_config(ProcessorConfig(sql="", output_tables=[]))
    assert len(errors) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd configforge && python -m pytest tests/test_processor_generator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`generators/processor/sql_processor.py`:
```python
import sqlite3
from generators.base import ConfigGenerator
from models.wizard import ProcessorConfig
from core.registry import GeneratorRegistry

@GeneratorRegistry.register("sql", "processor")
class SqlProcessorGenerator(ConfigGenerator[ProcessorConfig]):
    @classmethod
    def config_model(cls):
        return ProcessorConfig

    def infer_config(self, source: dict) -> ProcessorConfig:
        return ProcessorConfig(sql="", output_tables=[])

    def build_config(self, wizard_state: dict) -> ProcessorConfig:
        return ProcessorConfig(
            sql=wizard_state.get("sql", ""),
            output_tables=wizard_state.get("output_tables", []),
        )

    def validate_config(self, config: ProcessorConfig) -> list[str]:
        errors = []
        if not config.sql or not config.sql.strip():
            errors.append("SQL must not be empty")
            return errors
        try:
            conn = sqlite3.connect(":memory:")
            conn.executescript(config.sql)
            conn.close()
        except sqlite3.Error as e:
            errors.append(f"SQL syntax error: {e}")
        return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd configforge && python -m pytest tests/test_processor_generator.py -v`
Expected: PASS (4/4)

- [ ] **Step 5: Commit**

```bash
git add configforge/generators/processor/ configforge/tests/
git commit -m "feat: SqlProcessorGenerator with SQLite syntax validation"
```


### Task 6: ExcelOutputGenerator

**Files:**
- Create: `configforge/generators/output/__init__.py`
- Create: `configforge/generators/output/excel_output.py`
- Test: `configforge/tests/test_output_generator.py`

- [ ] **Step 1: Write the failing test**

`tests/test_output_generator.py`:
```python
import pytest
from generators.output.excel_output import ExcelOutputGenerator
from models.wizard import ExcelOutputConfig, ColumnMappingItem

def test_build_config():
    gen = ExcelOutputGenerator()
    state = {
        "template": "templates/report.xlsx",
        "sheet": "报表",
        "output_dir": "./output/",
        "source_table": "monthly_report",
        "filename": "report_{{date:%Y%m%d}}.xlsx",
        "columns": [{"source": "姓名", "target": "姓名"}],
    }
    config = gen.build_config(state)
    assert config.template == "templates/report.xlsx"
    assert config.source_table == "monthly_report"
    assert len(config.columns) == 1

def test_validate_empty_columns():
    gen = ExcelOutputGenerator()
    errors = gen.validate_config(ExcelOutputConfig(
        template="t.xlsx", source_table="t1", filename="f.xlsx", columns=[],
    ))
    assert any("columns" in e.lower() for e in errors)

def test_validate_missing_template():
    gen = ExcelOutputGenerator()
    errors = gen.validate_config(ExcelOutputConfig(
        template="", source_table="t1", filename="f.xlsx",
        columns=[ColumnMappingItem(source="a", target="a")],
    ))
    assert any("template" in e.lower() for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd configforge && python -m pytest tests/test_output_generator.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

`generators/output/excel_output.py`:
```python
from generators.base import ConfigGenerator
from models.wizard import ExcelOutputConfig, ColumnMappingItem
from core.registry import GeneratorRegistry

@GeneratorRegistry.register("excel", "output")
class ExcelOutputGenerator(ConfigGenerator[ExcelOutputConfig]):
    @classmethod
    def config_model(cls):
        return ExcelOutputConfig

    def infer_config(self, source: dict) -> ExcelOutputConfig:
        input_columns = source.get("input_columns", [])
        return ExcelOutputConfig(
            template="",
            sheet="Sheet1",
            output_dir="./output/",
            source_table="",
            filename="output.xlsx",
            columns=[ColumnMappingItem(source=c, target=c) for c in input_columns],
        )

    def build_config(self, wizard_state: dict) -> ExcelOutputConfig:
        cols = wizard_state.get("columns", [])
        return ExcelOutputConfig(
            template=wizard_state.get("template", ""),
            sheet=wizard_state.get("sheet", "Sheet1"),
            output_dir=wizard_state.get("output_dir", "./output/"),
            source_table=wizard_state.get("source_table", ""),
            filename=wizard_state.get("filename", "output.xlsx"),
            columns=[ColumnMappingItem(**c) if isinstance(c, dict) else c for c in cols],
        )

    def validate_config(self, config: ExcelOutputConfig) -> list[str]:
        errors = []
        if not config.template:
            errors.append("template is required")
        if not config.source_table:
            errors.append("source_table is required")
        if not config.filename:
            errors.append("filename is required")
        if len(config.columns) == 0:
            errors.append("at least one column mapping is required")
        return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd configforge && python -m pytest tests/test_output_generator.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Commit**

```bash
git add configforge/generators/output/ configforge/tests/
git commit -m "feat: ExcelOutputGenerator with column mapping validation"
```


### Task 7: YAML builder + Template builder services

**Files:**
- Create: `configforge/services/yaml_builder.py`
- Create: `configforge/services/template_builder.py`
- Test: `configforge/tests/test_services.py`

- [ ] **Step 1: Write the failing test**

`tests/test_services.py`:
```python
import io
from models.wizard import WizardState, SceneInfo, InputSource, ProcessorConfig, OutputTarget, ExcelOutputConfig, ExcelInputConfig, ColumnMappingItem
from services.yaml_builder import build_yaml
from services.template_builder import build_template

def test_build_yaml_has_all_sections():
    state = WizardState(
        scene=SceneInfo(name="测试", description="测试描述", version="1.0"),
        inputs=[InputSource(name="in1", plugin="excel", table="t1", param_key="f1", file_id="x1",
                             config=ExcelInputConfig(sheet="Sheet1"))],
        processor=ProcessorConfig(sql="SELECT 1", output_tables=["t1"]),
        output=OutputTarget(plugin="excel", config=ExcelOutputConfig(
            template="t.xlsx", source_table="t1", filename="out.xlsx",
            columns=[ColumnMappingItem(source="a", target="a")],
        )),
    )
    y = build_yaml(state)
    assert "scene:" in y
    assert "inputs:" in y
    assert "processors:" in y
    assert "output:" in y
    assert "snake_case" not in y
    assert "source_table" in y

def test_build_template_returns_bytes():
    buf = build_template(["姓名", "部门"])
    assert isinstance(buf, io.BytesIO)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd configforge && python -m pytest tests/test_services.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write yaml_builder.py**

`services/yaml_builder.py`:
```python
import yaml
from models.wizard import WizardState

def build_yaml(state: WizardState) -> str:
    d = {"scene": {"name": state.scene.name, "description": state.scene.description, "version": state.scene.version}}
    d["inputs"] = []
    for inp in state.inputs:
        d["inputs"].append({
            "name": inp.name, "plugin": inp.plugin, "table": inp.table,
            "param_key": inp.param_key, "config": {"sheet": inp.config.sheet},
        })
    d["processors"] = [{
        "name": state.scene.name + "处理",
        "plugin": state.processor.plugin,
        "output_tables": state.processor.output_tables,
        "config": {"sql": state.processor.sql},
    }]
    if state.output:
        out_cfg = state.output.config
        d["output"] = {
            "plugin": state.output.plugin,
            "config": {
                "template": out_cfg.template,
                "source_table": out_cfg.source_table,
                "sheet": out_cfg.sheet,
                "output_dir": out_cfg.output_dir,
                "filename": out_cfg.filename,
                "columns": [{"source": c.source, "target": c.target} for c in out_cfg.columns],
            },
        }
    return yaml.dump(d, allow_unicode=True, default_flow_style=False, sort_keys=False)
```

- [ ] **Step 4: Write template_builder.py**

`services/template_builder.py`:
```python
import io
import openpyxl

def build_template(headers: list[str]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd configforge && python -m pytest tests/test_services.py -v`
Expected: PASS (2/2)

- [ ] **Step 6: Commit**

```bash
git add configforge/services/ configforge/tests/
git commit -m "feat: yaml_builder + template_builder services"
```


### Task 8: API — files.py (upload endpoint)

**Files:**
- Create: `configforge/api/__init__.py`
- Create: `configforge/api/files.py`
- Test: `configforge/tests/test_api_files.py`

- [ ] **Step 1: Write the failing test**

`tests/test_api_files.py`:
```python
import io
import pytest
from httpx import AsyncClient, ASGITransport
from server import app
from models.wizard import FileUploadResponse

async def make_xlsx_content():
    import openpyxl; wb = openpyxl.Workbook(); ws = wb.active; ws.append(["A"]); b = io.BytesIO(); wb.save(b); b.seek(0); return b.read()

@pytest.mark.asyncio
async def test_upload_valid_xlsx_returns_file_id():
    content = await make_xlsx_content()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/files/upload", files={"file": ("test.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert resp.status_code == 200
    data = resp.json()
    assert "file_id" in data
    assert data["original_name"] == "test.xlsx"

@pytest.mark.asyncio
async def test_upload_unsupported_format():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/files/upload", files={"file": ("test.pdf", b"test", "application/pdf")})
    assert resp.status_code == 422
    assert resp.json()["code"] == "FILE_FORMAT_UNSUPPORTED"

@pytest.mark.asyncio
async def test_upload_no_file():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/files/upload")
    assert resp.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd configforge && pip install httpx && python -m pytest tests/test_api_files.py -v`
Expected: FAIL — `AssertionError: 404 != 200` (route not found)

- [ ] **Step 3: Write files.py**

`api/files.py`:
```python
import os, uuid, shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from models.wizard import FileUploadResponse, ErrorResponse

router = APIRouter()
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
MAX_FILE_SIZE = 50 * 1024 * 1024
UPLOAD_DIR = "tmp/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=422, detail=ErrorResponse(error="No file provided", code="VALIDATION_ERROR", recoverable=True).model_dump())
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=ErrorResponse(error=f"Unsupported format '{ext}'", code="FILE_FORMAT_UNSUPPORTED", recoverable=True).model_dump())
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=ErrorResponse(error="File exceeds 50MB limit", code="FILE_TOO_LARGE", recoverable=True).model_dump())
    file_id = uuid.uuid4().hex
    path = os.path.join(UPLOAD_DIR, file_id)
    with open(path, "wb") as f:
        f.write(content)
    return {"file_id": file_id, "original_name": file.filename}
```

- [ ] **Step 4: Register route in server.py, add exception handler**

In `server.py`, after the middleware setup, add:
```python
from api.files import router as files_router
from fastapi.responses import JSONResponse
from models.wizard import ErrorResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content=ErrorResponse(error=str(detail), code="VALIDATION_ERROR", recoverable=True).model_dump())

app.include_router(files_router, prefix="/api/files")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd configforge && python -m pytest tests/test_api_files.py -v`
Expected: PASS (3/3)

- [ ] **Step 6: Commit**

```bash
git add configforge/api/ configforge/server.py configforge/tests/
git commit -m "feat: POST /api/files/upload with format validation"
```


### Task 9: API — preview.py

**Files:**
- Create: `configforge/api/preview.py`
- Test: `configforge/tests/test_api_preview.py`

- [ ] **Step 1: Write the failing test**

`tests/test_api_preview.py`:
```python
import io, os, pytest, uuid
from httpx import AsyncClient, ASGITransport
from server import app

async def upload_test_xlsx():
    import openpyxl; wb = openpyxl.Workbook(); ws = wb.active; ws.append(["姓名", "部门"]); ws.append(["张三","研发"]); b = io.BytesIO(); wb.save(b); b.seek(0)
    fid = uuid.uuid4().hex
    os.makedirs("tmp/uploads", exist_ok=True)
    with open(f"tmp/uploads/{fid}", "wb") as f: f.write(b.read())
    return fid

@pytest.mark.asyncio
async def test_preview_file_returns_columns():
    fid = await upload_test_xlsx()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/preview/file", json={"file_id": fid})
    assert resp.status_code == 200
    data = resp.json()
    assert "姓名" in data["columns"]

@pytest.mark.asyncio
async def test_preview_nonexistent_file():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/preview/file", json={"file_id": "nonexistent"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd configforge && python -m pytest tests/test_api_preview.py -v`
Expected: FAIL — 404 (route not found)

- [ ] **Step 3: Write preview.py**

`api/preview.py`:
```python
import os
from fastapi import APIRouter, HTTPException
from models.wizard import ErrorResponse
from services.excel_reader import read_excel_info

router = APIRouter()
UPLOAD_DIR = "tmp/uploads"

@router.post("/file")
async def preview_file(req: dict):
    file_id = req.get("file_id", "")
    path = os.path.join(UPLOAD_DIR, file_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=ErrorResponse(error="File not found", code="FILE_NOT_FOUND", recoverable=True).model_dump())
    info = read_excel_info(path, sheet_name=req.get("sheet"))
    return {"columns": info["columns"], "rows": [[str(v) if v else "" for v in row] for row in info["sample_rows"]]}
```

- [ ] **Step 4: Register route in server.py**

```python
from api.preview import router as preview_router
app.include_router(preview_router, prefix="/api/preview")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd configforge && python -m pytest tests/test_api_preview.py -v`
Expected: PASS (2/2)

- [ ] **Step 6: Commit**

```bash
git add configforge/api/preview.py configforge/server.py configforge/tests/
git commit -m "feat: POST /api/preview/file endpoint"
```


### Task 10: API — wizard.py (complete wizard endpoints)

**Files:**
- Create: `configforge/api/wizard.py`
- Create: `configforge/core/pipeline.py`
- Test: `configforge/tests/test_api_wizard.py`

- [ ] **Step 1: Write the failing test**

`tests/test_api_wizard.py`:
```python
import io, os, pytest, uuid
from httpx import AsyncClient, ASGITransport
from server import app

async def upload_test_xlsx():
    import openpyxl; wb = openpyxl.Workbook(); ws = wb.active; ws.append(["姓名","部门"]); ws.append(["张三","研发"]); b = io.BytesIO(); wb.save(b); b.seek(0)
    fid = uuid.uuid4().hex
    os.makedirs("tmp/uploads", exist_ok=True)
    with open(f"tmp/uploads/{fid}", "wb") as f: f.write(b.read())
    return fid

@pytest.mark.asyncio
async def test_init_scene():
    fid = await upload_test_xlsx()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/wizard/init-scene", json={"file_ids": [fid]})
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_infer_input():
    fid = await upload_test_xlsx()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/wizard/infer-input/test_input", json={"file_id": fid, "type": "excel"})
    assert resp.status_code == 200
    assert "columns" in resp.json()

@pytest.mark.asyncio
async def test_infer_output():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/wizard/infer-output", json={"inputs": []})
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_generate():
    state = {"scene": {"name":"测试","description":"","version":"1.0"}, "inputs":[], "processor":{"plugin":"sql","sql":"SELECT 1","output_tables":["t1"]}, "output":None, "current_step":4, "uploaded_files":{}}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/wizard/generate", json={"state": state})
    assert resp.status_code == 200
    assert "yaml" in resp.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd configforge && python -m pytest tests/test_api_wizard.py -v`
Expected: FAIL — 404

- [ ] **Step 3: Write core/pipeline.py**

`core/pipeline.py`:
```python
from models.wizard import WizardState, SceneInitRequest, SceneInitResponse, InputInferRequest, InputInferResponse, OutputInferRequest, OutputInferResponse, ColumnMappingItem
from core.registry import GeneratorRegistry
from services.excel_reader import read_excel_info
from services.yaml_builder import build_yaml
from services.template_builder import build_template
import os

UPLOAD_DIR = "tmp/uploads"

def init_scene(req: SceneInitRequest) -> SceneInitResponse:
    return SceneInitResponse(scene={"name": "新场景", "description": "", "version": "1.0"})

def infer_input(input_name: str, req: InputInferRequest) -> InputInferResponse:
    path = os.path.join(UPLOAD_DIR, req.file_id)
    info = read_excel_info(path)
    return InputInferResponse(
        columns=[{"name": c, "sample_values": info["sample_rows"][0] if info["sample_rows"] else []} for c in info["columns"]],
        suggested_table=input_name,
        suggested_param_key=f"{input_name}_file",
    )

def infer_output(req: OutputInferRequest) -> OutputInferResponse:
    cols = []
    if req.inputs:
        pass
    return OutputInferResponse(suggested_columns=cols)

def generate(state: WizardState) -> dict:
    yaml = build_yaml(state)
    return {"yaml": yaml}
```

- [ ] **Step 4: Write wizard.py**

`api/wizard.py`:
```python
from fastapi import APIRouter
from models.wizard import WizardState, SceneInitRequest, InputInferRequest, OutputInferRequest, GenerateRequest
from core.pipeline import init_scene, infer_input, infer_output, generate

router = APIRouter()

@router.post("/init-scene")
async def api_init_scene(req: SceneInitRequest):
    return init_scene(req)

@router.post("/infer-input/{input_name}")
async def api_infer_input(input_name: str, req: InputInferRequest):
    return infer_input(input_name, req)

@router.post("/infer-output")
async def api_infer_output(req: OutputInferRequest):
    return infer_output(req)

@router.post("/generate")
async def api_generate(req: GenerateRequest):
    return generate(req.state)
```

- [ ] **Step 5: Register route in server.py**

```python
from api.wizard import router as wizard_router
app.include_router(wizard_router, prefix="/api/wizard")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd configforge && python -m pytest tests/test_api_wizard.py -v`
Expected: PASS (4/4)

- [ ] **Step 7: Commit**

```bash
git add configforge/api/wizard.py configforge/core/pipeline.py configforge/server.py configforge/tests/
git commit -m "feat: /api/wizard/* endpoints - init-scene, infer-input, infer-output, generate"
```


### Task 11: API — ai.py (AI suggest endpoint)

**Files:**
- Create: `configforge/api/ai.py`
- Create: `configforge/services/ai/__init__.py`
- Create: `configforge/services/ai/base.py`
- Test: `configforge/tests/test_api_ai.py`

- [ ] **Step 1: Write the failing test**

`tests/test_api_ai.py`:
```python
import pytest
from httpx import AsyncClient, ASGITransport
from server import app

@pytest.mark.asyncio
async def test_ai_suggest_returns_noop():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/ai/suggest", json={"category": "sql", "context": {"inputs": []}})
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd configforge && python -m pytest tests/test_api_ai.py -v`
Expected: FAIL — 404

- [ ] **Step 3: Write AI base service**

`services/ai/base.py`:
```python
from abc import ABC, abstractmethod

class LlmBackend(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str: ...
```

`services/ai/__init__.py`:
```python
from services.ai.base import LlmBackend
```

- [ ] **Step 4: Write ai.py**

`api/ai.py`:
```python
from fastapi import APIRouter
from models.ai import AiSuggestionRequest, AiSuggestionResponse

router = APIRouter()

@router.post("/suggest", response_model=AiSuggestionResponse)
async def suggest(req: AiSuggestionRequest):
    # v0.1: AI backend is optional; return no-op response if not configured
    return AiSuggestionResponse(content="AI 未配置，请手动填写", category=req.category)
```

- [ ] **Step 5: Register route in server.py**

```python
from api.ai import router as ai_router
app.include_router(ai_router, prefix="/api/ai")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd configforge && python -m pytest tests/test_api_ai.py -v`
Expected: PASS (1/1)

- [ ] **Step 7: Commit**

```bash
git add configforge/api/ai.py configforge/services/ai/ configforge/server.py configforge/tests/
git commit -m "feat: /api/ai/suggest endpoint with no-op backend"
```


### Task 12: Frontend project scaffold

**Files:**
- Create: `configforge-web/package.json`
- Create: `configforge-web/vite.config.ts`
- Create: `configforge-web/tsconfig.json`
- Create: `configforge-web/index.html`
- Create: `configforge-web/src/main.ts`
- Create: `configforge-web/src/App.vue`

- [ ] **Step 1: Scaffold with Vite**

Run: `cd configforge-web && npm create vite@latest . -- --template vue-ts 2>/dev/null || true`

- [ ] **Step 2: Write package.json dependencies**

Ensure these are in package.json:
```json
{
  "dependencies": {
    "vue": "^3.5.0",
    "vue-router": "^4.4.0",
    "pinia": "^2.2.0",
    "pinia-plugin-persistedstate": "^3.2.0",
    "@codemirror/lang-sql": "^6.0.0",
    "@codemirror/view": "^6.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.5.0",
    "vite": "^6.0.0",
    "vitest": "^2.0.0",
    "@vue/test-utils": "^2.4.0",
    "happy-dom": "^14.0.0"
  }
}
```

Run: `cd configforge-web && npm install`

- [ ] **Step 3: Write vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: { '/api': 'http://localhost:8000' }
  }
})
```

- [ ] **Step 4: Write index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ConfigForge</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

- [ ] **Step 5: Write main.ts + App.vue**

`src/main.ts`:
```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import App from './App.vue'
import router from './router'

const app = createApp(App)
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
app.use(pinia)
app.use(router)
app.mount('#app')
```

`src/App.vue`:
```vue
<template>
  <div class="min-h-screen bg-slate-50 font-sans text-slate-900 antialiased">
    <router-view />
  </div>
</template>
```

- [ ] **Step 6: Verify dev server starts**

Run: `cd configforge-web && npx vite --host 2>&1 | head -10`
Expected: `VITE v6.x.x  ready in ...`

- [ ] **Step 7: Commit**

```bash
git add configforge-web/
git commit -m "feat: configforge-web scaffold with Vue 3 + Vite + Pinia + Router"
```


### Task 13: TypeScript types + Pinia WizardStore

**Files:**
- Create: `configforge-web/src/types/wizard.ts`
- Create: `configforge-web/src/stores/wizard.ts`
- Test: `configforge-web/tests/stores/wizard.test.ts`

- [ ] **Step 1: Write types/wizard.ts**

```typescript
export interface UploadedFileMeta {
  fileId: string
  originalName: string
}

export interface AiSuggestion {
  content: string
  category: 'scene' | 'columns' | 'sql' | 'mapping'
  status: 'pending' | 'accepted' | 'rejected'
  timestamp: number
}

export interface SceneInfo {
  name: string
  description: string
  version: string
}

export interface ExcelInputConfig {
  type: 'excel'
  sheet: string
}

export interface InputSource {
  name: string
  plugin: 'excel'
  table: string
  paramKey: string
  fileId: string
  config: ExcelInputConfig
}

export interface ProcessorConfig {
  plugin: 'sql'
  sql: string
  outputTables: string[]
}

export interface ColumnMappingItem {
  source: string
  target: string
}

export interface ExcelOutputConfig {
  type: 'excel'
  template: string
  sheet: string
  outputDir: string
  sourceTable: string
  filename: string
  columns: ColumnMappingItem[]
}

export interface OutputTarget {
  plugin: 'excel'
  config: ExcelOutputConfig
}

export interface WizardState {
  currentStep: number
  scene: SceneInfo
  inputs: InputSource[]
  processor: ProcessorConfig
  output: OutputTarget | null
  uploadedFiles: Record<string, UploadedFileMeta>
  aiSuggestions: Record<string, AiSuggestion>
}
```

- [ ] **Step 2: Write the failing test for the store**

`tests/stores/wizard.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWizardStore } from '../../src/stores/wizard'

describe('useWizardStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts at step 1', () => {
    const store = useWizardStore()
    expect(store.currentStep).toBe(1)
  })

  it('canProceed is false when scene name is empty', () => {
    const store = useWizardStore()
    store.scene.name = ''
    expect(store.canProceed).toBe(false)
  })

  it('canProceed is true when scene name is set', () => {
    const store = useWizardStore()
    store.scene.name = '测试场景'
    expect(store.canProceed).toBe(true)
  })

  it('nextStep advances step', () => {
    const store = useWizardStore()
    store.scene.name = '测试'
    store.nextStep()
    expect(store.currentStep).toBe(2)
  })

  it('goToStep navigates to completed step', () => {
    const store = useWizardStore()
    store.scene.name = '测试'
    store.nextStep() // 1->2
    store.nextStep() // 2->3
    store.goToStep(1)
    expect(store.currentStep).toBe(1)
  })

  it('addInput adds to inputs array', () => {
    const store = useWizardStore()
    store.addInput({ name: 'in1', plugin: 'excel', table: 't1', paramKey: 'f1', fileId: 'x1', config: { type: 'excel', sheet: 'Sheet1' } })
    expect(store.inputs).toHaveLength(1)
  })

  it('removeInput removes by index', () => {
    const store = useWizardStore()
    store.addInput({ name: 'in1', plugin: 'excel', table: 't1', paramKey: 'f1', fileId: 'x1', config: { type: 'excel', sheet: 'Sheet1' } })
    store.removeInput(0)
    expect(store.inputs).toHaveLength(0)
  })
})
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd configforge-web && npx vitest run tests/stores/wizard.test.ts`
Expected: FAIL — store not defined

- [ ] **Step 4: Write Pinia store**

`src/stores/wizard.ts`:
```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { WizardState, SceneInfo, InputSource, ProcessorConfig, OutputTarget, UploadedFileMeta, AiSuggestion } from '../types/wizard'

export const useWizardStore = defineStore('wizard', () => {
  const currentStep = ref(1)

  const scene = ref<SceneInfo>({ name: '', description: '', version: '1.0' })
  const inputs = ref<InputSource[]>([])
  const processor = ref<ProcessorConfig>({ plugin: 'sql', sql: '', outputTables: [] })
  const output = ref<OutputTarget | null>(null)
  const uploadedFiles = ref<Record<string, UploadedFileMeta>>({})
  const aiSuggestions = ref<Record<string, AiSuggestion>>({})

  const canProceed = computed(() => {
    if (currentStep.value === 1) return scene.value.name.trim().length > 0
    if (currentStep.value === 2) return inputs.value.length > 0
    if (currentStep.value === 3) return processor.value.sql.trim().length > 0 && output.value !== null
    return true
  })

  const stepValidation = computed(() => {
    const msgs: string[] = []
    if (currentStep.value === 1 && !scene.value.name.trim()) msgs.push('场景名称不能为空')
    if (currentStep.value === 2 && inputs.value.length === 0) msgs.push('至少需要 1 个输入源')
    if (currentStep.value === 3 && !processor.value.sql.trim()) msgs.push('SQL 不能为空')
    if (currentStep.value === 3 && !output.value) msgs.push('尚未配置输出')
    return msgs
  })

  function nextStep() { if (canProceed.value && currentStep.value < 4) currentStep.value++ }
  function prevStep() { if (currentStep.value > 1) currentStep.value-- }
  function goToStep(n: number) { if (n <= currentStep.value || n <= 4) currentStep.value = n }

  function addInput(input: InputSource) { inputs.value.push(input) }
  function removeInput(index: number) { inputs.value.splice(index, 1) }
  function updateInput(index: number, input: InputSource) { inputs.value[index] = input }

  function setProcessor(p: ProcessorConfig) { processor.value = p }
  function setOutput(o: OutputTarget) { output.value = o }

  function addFileRef(fileId: string, meta: UploadedFileMeta) { uploadedFiles.value[fileId] = meta }
  function removeFileRef(fileId: string) { delete uploadedFiles.value[fileId] }

  function setSuggestion(category: string, s: AiSuggestion) { aiSuggestions.value[category] = s }
  function acceptSuggestion(category: string) { if (aiSuggestions.value[category]) aiSuggestions.value[category].status = 'accepted' }
  function rejectSuggestion(category: string) { if (aiSuggestions.value[category]) aiSuggestions.value[category].status = 'rejected' }

  return { currentStep, scene, inputs, processor, output, uploadedFiles, aiSuggestions, canProceed, stepValidation, nextStep, prevStep, goToStep, addInput, removeInput, updateInput, setProcessor, setOutput, addFileRef, removeFileRef, setSuggestion, acceptSuggestion, rejectSuggestion }
}, {
  persist: { key: 'wizard_state_v1', storage: localStorage }
})
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd configforge-web && npx vitest run tests/stores/wizard.test.ts`
Expected: PASS (6/6)

- [ ] **Step 6: Commit**

```bash
git add configforge-web/src/types/ configforge-web/src/stores/ configforge-web/tests/
git commit -m "feat: TypeScript types + Pinia WizardStore with persistence"
```


### Task 14: Router + Views (shell)

**Files:**
- Create: `configforge-web/src/router/index.ts`
- Create: `configforge-web/src/views/HomeView.vue`
- Create: `configforge-web/src/views/Step1SceneView.vue`
- Create: `configforge-web/src/views/Step2InputView.vue`
- Create: `configforge-web/src/views/Step3OutputView.vue`
- Create: `configforge-web/src/views/Step4ExportView.vue`

- [ ] **Step 1: Write router/index.ts**

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
    { path: '/step/1', name: 'step1', component: () => import('../views/Step1SceneView.vue') },
    { path: '/step/2', name: 'step2', component: () => import('../views/Step2InputView.vue') },
    { path: '/step/3', name: 'step3', component: () => import('../views/Step3OutputView.vue') },
    { path: '/step/4', name: 'step4', component: () => import('../views/Step4ExportView.vue') },
  ],
})

export default router
```

- [ ] **Step 2: Write HomeView.vue**

```vue
<template>
  <div class="max-w-3xl mx-auto px-4 py-12">
    <div class="text-center">
      <h1 class="text-xl font-semibold">ConfigForge</h1>
      <p class="text-sm text-slate-500 mt-1">PipeForge 配置创建向导</p>
    </div>
    <div class="mt-8 text-center">
      <router-link to="/step/1" class="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors">
        开始创建新配置 &rarr;
      </router-link>
    </div>
  </div>
</template>
```

- [ ] **Step 3: Write Step1SceneView.vue**

```vue
<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <StepIndicator :current-step="1" />
    <SceneInfoForm />
    <div class="flex justify-between items-center pt-6 border-t border-slate-100 mt-6">
      <router-link to="/" class="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md">取消</router-link>
      <button @click="onNext" :disabled="!store.canProceed" class="inline-flex items-center justify-center gap-2 px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">下一步 &rarr;</button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import StepIndicator from '../components/common/StepIndicator.vue'
import SceneInfoForm from '../components/step1/SceneInfoForm.vue'

const router = useRouter()
const store = useWizardStore()

function onNext() {
  if (store.canProceed) {
    store.nextStep()
    router.push('/step/2')
  }
}
</script>
```

- [ ] **Step 4: Write placeholder views for Steps 2-4**

Step2InputView.vue, Step3OutputView.vue, Step4ExportView.vue follow the same pattern — wrap StepIndicator + step-specific component + prev/next footer. See `Step1SceneView.vue` above for the template. Each uses `store.nextStep()` / `store.prevStep()` and `router.push('/step/N')`.

- [ ] **Step 5: Verify routing works**

Run: `cd configforge-web && npx vite build 2>&1 | tail -5`
Expected: `✓ built in ...`

- [ ] **Step 6: Commit**

```bash
git add configforge-web/src/router/ configforge-web/src/views/ configforge-web/src/App.vue configforge-web/src/main.ts
git commit -m "feat: Vue Router + HomeView + Step 1-4 view shells"
```


### Task 15: Common components

**Files:**
- Create: `configforge-web/src/components/common/StepIndicator.vue`
- Create: `configforge-web/src/components/common/AiSuggestPanel.vue`
- Create: `configforge-web/src/components/common/ErrorBanner.vue`
- Create: `configforge-web/src/components/common/LoadingSpinner.vue`

- [ ] **Step 1: Write StepIndicator.vue**

```vue
<template>
  <div class="flex items-center justify-center gap-0 mb-8">
    <div v-for="i in 4" :key="i" class="flex items-center gap-0">
      <div class="flex items-center gap-2 px-3 py-1 rounded-full text-sm cursor-pointer select-none"
           :class="i < currentStep ? 'text-slate-900 cursor-pointer hover:text-blue-600' : i === currentStep ? 'text-blue-600 font-semibold' : 'text-slate-400 cursor-default'"
           @click="i <= currentStep ? $emit('goto', i) : null">
        <span class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border-2"
              :class="i < currentStep ? 'bg-blue-600 border-blue-600 text-white' : i === currentStep ? 'border-blue-600 text-blue-600 shadow-[0_0_0_3px_#EFF6FF]' : 'border-slate-200 text-slate-400 bg-white'">{{ i }}</span>
        {{ labels[i - 1] }}
      </div>
      <div v-if="i < 4" class="w-8 h-0.5 mx-1" :class="i < currentStep ? 'bg-blue-600' : 'bg-slate-200'"></div>
    </div>
  </div>
</template>
<script setup lang="ts">
defineProps<{ currentStep: number }>()
defineEmits<{ goto: [step: number] }>()
const labels = ['场景信息', '数据源配置', '输出定义', '预览与导出']
</script>
```

- [ ] **Step 2: Write AiSuggestPanel.vue**

```vue
<template>
  <div v-if="visible" class="bg-gradient-to-br from-sky-50 to-blue-50 border border-sky-200 rounded-lg p-4 mt-4">
    <div class="flex items-center gap-2 text-sm font-semibold text-sky-700 mb-3">🤖 AI 建议</div>
    <div class="text-sm text-slate-900 mb-3 leading-relaxed" v-html="content"></div>
    <div class="flex gap-2">
      <button @click="$emit('accept')" class="inline-flex items-center justify-center gap-2 px-2.5 py-1 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700">采纳</button>
      <button @click="$emit('regenerate')" class="inline-flex items-center justify-center gap-2 px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">重新生成</button>
    </div>
  </div>
</template>
<script setup lang="ts">
defineProps<{ visible: boolean; content: string }>()
defineEmits<{ accept: []; regenerate: [] }>()
</script>
```

- [ ] **Step 3: Write ErrorBanner.vue and LoadingSpinner.vue**

`ErrorBanner.vue`: Display a colored banner based on `level` prop ("warning" = yellow, "error" = red). Show error message text. Auto-dismiss for warnings after 3s.

`LoadingSpinner.vue`: Simple centered spinner with optional label text.

- [ ] **Step 4: Commit**

```bash
git add configforge-web/src/components/common/
git commit -m "feat: StepIndicator, AiSuggestPanel, ErrorBanner, LoadingSpinner"
```


### Task 16: Step 1 — SceneInfoForm component

**Files:**
- Create: `configforge-web/src/components/step1/SceneInfoForm.vue`
- Create: `configforge-web/src/composables/useFileUpload.ts`
- Test: `configforge-web/tests/composables/useFileUpload.test.ts`

- [ ] **Step 1: Write useFileUpload composable**

`src/composables/useFileUpload.ts`:
```typescript
import { ref } from 'vue'
import type { UploadedFileMeta } from '../types/wizard'

export function useFileUpload() {
  const uploading = ref(false)
  const error = ref<string | null>(null)

  async function upload(file: File): Promise<UploadedFileMeta | null> {
    uploading.value = true
    error.value = null
    try {
      const form = new FormData()
      form.append('file', file)
      const resp = await fetch('/api/files/upload', { method: 'POST', body: form })
      if (!resp.ok) {
        const data = await resp.json()
        error.value = data.error || 'Upload failed'
        return null
      }
      const data = await resp.json()
      return { fileId: data.file_id, originalName: data.original_name }
    } catch (e) {
      error.value = 'Network error'
      return null
    } finally {
      uploading.value = false
    }
  }

  return { uploading, error, upload }
}
```

- [ ] **Step 2: Write SceneInfoForm.vue**

```vue
<template>
  <div class="bg-white border border-slate-200 rounded-lg p-6">
    <h2 class="text-base font-semibold mb-5">场景信息</h2>
    <p class="text-xs text-slate-400 mb-4" style="margin-top:-12px">定义流水线的基本信息，后续步骤中可添加数据源、配置处理逻辑和输出格式</p>
    <div class="grid grid-cols-2 gap-4 mb-4">
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">场景名称</label>
        <input v-model="store.scene.name" class="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md focus:border-blue-600 focus:shadow-[0_0_0_3px_#EFF6FF] outline-none transition-colors h-9" value="月度人员考勤报表" />
      </div>
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">版本</label>
        <input v-model="store.scene.version" class="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md focus:border-blue-600 focus:shadow-[0_0_0_3px_#EFF6FF] outline-none transition-colors h-9" />
      </div>
    </div>
    <div class="mb-4">
      <label class="block text-sm font-medium text-slate-900 mb-1">场景描述</label>
      <input v-model="store.scene.description" class="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md focus:border-blue-600 focus:shadow-[0_0_0_3px_#EFF6FF] outline-none transition-colors h-9" />
    </div>

    <div class="mb-4">
      <label class="block text-sm font-medium text-slate-900 mb-1">上传数据文件</label>
      <div class="border-2 border-dashed border-slate-200 rounded-lg p-6 text-center cursor-pointer bg-slate-50 hover:border-blue-600 hover:bg-blue-50 transition-colors" @click="triggerUpload">
        <div class="text-2xl mb-1 opacity-60">📎</div>
        <div class="text-sm text-slate-500">拖拽或点击上传 Excel 文件</div>
        <div class="text-xs text-slate-400 mt-1">.xlsx .xls &nbsp;|&nbsp; 最大 50MB</div>
        <input type="file" ref="fileInput" class="hidden" accept=".xlsx,.xls" @change="onFileSelected" />
      </div>
      <div class="mt-3" v-if="Object.keys(store.uploadedFiles).length > 0">
        <span v-for="(f, id) in store.uploadedFiles" :key="id" class="inline-flex items-center gap-1 px-3 py-1 bg-green-50 border border-green-200 rounded-full text-sm text-green-700 mr-1 mb-1">
          ✓ {{ f.originalName }}
        </span>
      </div>
    </div>

    <ErrorBanner v-if="uploadError" level="error" :message="uploadError" />
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { useFileUpload } from '../../composables/useFileUpload'
import ErrorBanner from '../common/ErrorBanner.vue'

const store = useWizardStore()
const { uploading, error: uploadError, upload } = useFileUpload()
const fileInput = ref<HTMLInputElement>()

function triggerUpload() { fileInput.value?.click() }

async function onFileSelected(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (!files || files.length === 0) return
  for (const file of Array.from(files)) {
    const meta = await upload(file)
    if (meta) store.addFileRef(meta.fileId, meta)
  }
}
</script>
```

- [ ] **Step 3: Verify Step 1 renders**

Run: `cd configforge-web && npx vite build 2>&1 | tail -5`
Expected: `✓ built in ...`

- [ ] **Step 4: Commit**

```bash
git add configforge-web/src/components/step1/ configforge-web/src/composables/useFileUpload.ts configforge-web/src/views/Step1SceneView.vue
git commit -m "feat: Step 1 - SceneInfoForm with file upload"
```


### Task 17: Step 2 — Input source components

**Files:**
- Create: `configforge-web/src/components/step2/InputSourceCard.vue`
- Create: `configforge-web/src/components/step2/ColumnPreview.vue`
- Create: `configforge-web/src/components/step2/InputSourceList.vue`
- Create: `configforge-web/src/composables/useWizardApi.ts`

- [ ] **Step 1: Write useWizardApi composable**

`src/composables/useWizardApi.ts`:
```typescript
import { ref } from 'vue'

export function useWizardApi() {
  const loading = ref(false)
  const error = ref<{ message: string; code: string } | null>(null)

  async function post<T>(url: string, body: any): Promise<T | null> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      const data = await resp.json()
      if (!resp.ok) { error.value = { message: data.error, code: data.code }; return null }
      return data as T
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  async function initScene(fileIds: string[]) { return post<any>('/api/wizard/init-scene', { file_ids: fileIds }) }

  return { loading, error, initScene }
}
```

- [ ] **Step 2: Write InputSourceCard.vue**

A card component for a single input source. Props: `input: InputSource`, `index: number`. Emits: `remove`, `update`. Shows:
- Header with name + plugin badge + delete button
- Body: file select, sheet name input, table name input, param_key input
- Column preview table (using ColumnPreview sub-component)

`ColumnPreview.vue`: Props: `columns: string[]`, `rows: string[][]`. Renders a `<table>` with thead + tbody.

- [ ] **Step 3: Write InputSourceList.vue**

Lists all `InputSourceCard` components. Has an "add" area:
- Button "+ 添加输入源" that toggles a type selector grid
- Type selector shows Excel (selectable), CSV/Database/PDF/PPT/API (future badges)
- Clicking a type adds a new input source to the store

- [ ] **Step 4: Verify Step 2 builds**

Run: `cd configforge-web && npx vite build 2>&1 | tail -5`
Expected: `✓ built`

- [ ] **Step 5: Commit**

```bash
git add configforge-web/src/components/step2/ configforge-web/src/composables/useWizardApi.ts configforge-web/src/views/Step2InputView.vue
git commit -m "feat: Step 2 - InputSourceList, InputSourceCard, ColumnPreview"
```


### Task 18: Step 3 — SQL editor + Output config (Tab layout)

**Files:**
- Create: `configforge-web/src/components/step3/SqlEditorTab.vue`
- Create: `configforge-web/src/components/step3/OutputConfigTab.vue`
- Create: `configforge-web/src/components/step3/ColumnMapping.vue`

- [ ] **Step 1: Write SqlEditorTab.vue**

```vue
<template>
  <div>
    <!-- Processor type selector: SQL selected, Jinja2/Python future -->
    <div class="type-selector grid grid-cols-3 gap-3 mb-5">
      <div class="p-4 border-2 border-blue-600 bg-blue-50 rounded-lg text-center shadow-[0_0_0_3px_#BFDBFE] cursor-default">
        <span class="text-2xl block mb-2">🧪</span>
        <span class="text-sm font-semibold">SQL</span>
        <span class="text-xs text-slate-500 mt-1 block">SQLite 执行</span>
      </div>
      <div class="p-4 border-2 border-dashed border-slate-200 rounded-lg text-center opacity-55 cursor-not-allowed bg-slate-50">
        <span class="absolute top-1.5 right-1.5 px-1.5 py-0.5 bg-amber-50 text-amber-600 text-[10px] font-medium rounded-sm">v0.3</span>
        <span class="text-2xl block mb-2">🔗</span>
        <span class="text-sm font-semibold">Jinja2</span>
      </div>
      <div class="p-4 border-2 border-dashed border-slate-200 rounded-lg text-center opacity-55 cursor-not-allowed bg-slate-50">
        <span class="absolute top-1.5 right-1.5 px-1.5 py-0.5 bg-amber-50 text-amber-600 text-[10px] font-medium rounded-sm">v0.4</span>
        <span class="text-2xl block mb-2">🖥</span>
        <span class="text-sm font-semibold">Python</span>
      </div>
    </div>

    <!-- SQL textarea -->
    <div class="mb-4">
      <label class="block text-sm font-medium text-slate-900 mb-1">SQL</label>
      <textarea v-model="store.processor.sql" class="w-full min-h-[160px] px-3 py-2 text-sm font-mono border border-slate-200 rounded-md focus:border-blue-600 focus:shadow-[0_0_0_3px_#EFF6FF] outline-none resize-y leading-relaxed"></textarea>
    </div>
    <div class="flex gap-2 items-center mb-4">
      <button class="px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">🤖 AI 生成 SQL</button>
      <button class="px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">🧪 验证语法</button>
      <span v-if="sqlValid" class="text-xs text-green-600 font-medium">✓ 验证通过</span>
    </div>

    <!-- output_tables -->
    <div class="mb-4">
      <label class="block text-sm font-medium text-slate-900 mb-1">输出表名（output_tables）</label>
      <div class="flex flex-wrap gap-2 items-center">
        <span v-for="(t, i) in store.processor.outputTables" :key="i" class="inline-flex items-center gap-1 px-2.5 py-1 bg-purple-50 text-purple-700 text-sm rounded-full font-medium">
          {{ t }} <span class="cursor-pointer ml-1 opacity-60" @click="removeTable(i)">&times;</span>
        </span>
        <button @click="addTable" class="px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-dashed border-slate-200 rounded-md hover:bg-slate-50">+ 添加表名</button>
      </div>
      <p class="text-xs text-slate-400 mt-1">声明此 SQL 创建的表名，供后续输出步骤引用</p>
    </div>

    <AiSuggestPanel visible :content="'检测到 SELECT 语句创建了 1 个结果集，建议 output_tables 设为 <code>monthly_report</code>。'" @accept="() => {}" @regenerate="() => {}" />
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import AiSuggestPanel from '../common/AiSuggestPanel.vue'

const store = useWizardStore()
const sqlValid = computed(() => store.processor.sql.trim().length > 0)

function addTable() {
  const name = prompt('表名:')
  if (name) store.processor.outputTables.push(name)
}
function removeTable(i: number) { store.processor.outputTables.splice(i, 1) }
</script>
```

- [ ] **Step 2: Write OutputConfigTab.vue**

Output type selector (Excel/CSV/Database/PDF/PPT/API with future badges) + dynamic form switching. Excel form fields: template select, source_table select, sheet name, filename template, output_dir, column mapping table, AI auto-map button. CSV form: source_table, filename, encoding, delimiter, header toggle.

`ColumnMapping.vue`: Two-column table (source → target) showing the mapping, editable rows.

- [ ] **Step 3: Update Step3OutputView to use Tab layout**

```vue
<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <StepIndicator :current-step="3" @goto="(s) => { store.goToStep(s); router.push(`/step/${s}`) }" />
    <div class="bg-white border border-slate-200 rounded-lg p-6">
      <div class="flex border-b-2 border-slate-200 mb-5">
        <div class="px-4 py-2 text-sm font-medium cursor-pointer border-b-2 -mb-0.5 transition-colors"
             :class="activeTab === 'processor' ? 'text-blue-600 border-blue-600' : 'text-slate-500 border-transparent hover:text-slate-900'"
             @click="activeTab = 'processor'">SQL 处理</div>
        <div class="px-4 py-2 text-sm font-medium cursor-pointer border-b-2 -mb-0.5 transition-colors"
             :class="activeTab === 'output' ? 'text-blue-600 border-blue-600' : 'text-slate-500 border-transparent hover:text-slate-900'"
             @click="activeTab = 'output'">输出配置</div>
      </div>
      <SqlEditorTab v-if="activeTab === 'processor'" />
      <OutputConfigTab v-if="activeTab === 'output'" />
    </div>
    <div class="flex justify-between items-center pt-6 border-t border-slate-100 mt-6">
      <button @click="store.prevStep(); router.push('/step/2')" class="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md">&larr; 上一步</button>
      <button @click="onNext" :disabled="!store.canProceed" class="inline-flex items-center justify-center gap-2 px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">下一步 &rarr;</button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useWizardStore } from '../../stores/wizard'
import StepIndicator from '../components/common/StepIndicator.vue'
import SqlEditorTab from '../components/step3/SqlEditorTab.vue'
import OutputConfigTab from '../components/step3/OutputConfigTab.vue'

const router = useRouter()
const store = useWizardStore()
const activeTab = ref<'processor' | 'output'>('processor')

function onNext() { if (store.canProceed) { store.nextStep(); router.push('/step/4') } }
</script>
```

- [ ] **Step 4: Verify Step 3 builds**

Run: `cd configforge-web && npx vite build 2>&1 | tail -5`
Expected: `✓ built`

- [ ] **Step 5: Commit**

```bash
git add configforge-web/src/components/step3/ configforge-web/src/views/Step3OutputView.vue
git commit -m "feat: Step 3 - SqlEditorTab + OutputConfigTab with Tab layout"
```


### Task 19: Step 4 — YAML preview + Export

**Files:**
- Create: `configforge-web/src/components/step4/YamlPreview.vue`
- Create: `configforge-web/src/components/step4/ExportActions.vue`

- [ ] **Step 1: Write YamlPreview.vue**

```vue
<template>
  <div class="bg-slate-800 rounded-lg p-5 overflow-x-auto font-mono text-sm leading-relaxed">
    <pre class="text-slate-200"><span class="text-slate-500"># {{ store.scene.name }} v{{ store.scene.version }}</span>
<span class="text-blue-300">scene</span>:
  <span class="text-blue-300">name</span>: <span class="text-green-300">{{ store.scene.name }}</span>
  <span class="text-blue-300">version</span>: <span class="text-green-300">"{{ store.scene.version }}"</span>
  <span class="text-blue-300">description</span>: <span class="text-green-300">{{ store.scene.description }}</span>

<span class="text-blue-300">inputs</span>:
<span v-for="(inp, i) in store.inputs" :key="i">  - <span class="text-blue-300">name</span>: <span class="text-green-300">{{ inp.name }}</span>
    <span class="text-blue-300">plugin</span>: <span class="text-green-300">{{ inp.plugin }}</span>
    <span class="text-blue-300">table</span>: <span class="text-green-300">{{ inp.table }}</span>
    <span class="text-blue-300">param_key</span>: <span class="text-green-300">{{ inp.paramKey }}</span>
    <span class="text-blue-300">config</span>:
      <span class="text-blue-300">sheet</span>: <span class="text-green-300">{{ inp.config.sheet }}</span>
</span>
<span class="text-blue-300">processors</span>:
  - <span class="text-blue-300">name</span>: <span class="text-green-300">{{ store.scene.name }}处理</span>
    <span class="text-blue-300">plugin</span>: <span class="text-green-300">sql</span>
    <span class="text-blue-300">output_tables</span>:
      - <span class="text-green-300">{{ store.processor.outputTables.join(', ') }}</span>
    <span class="text-blue-300">config</span>:
      <span class="text-blue-300">sql</span>: <span class="text-green-300">|</span>
<span class="text-green-300">        CREATE TABLE ...</span>

<span class="text-blue-300">output</span>:
  <span class="text-blue-300">plugin</span>: <span class="text-green-300">excel</span>
  <span class="text-blue-300">config</span>:
    <span class="text-blue-300">template</span>: <span class="text-green-300">templates/{{ store.scene.name }}_template.xlsx</span>
    <span class="text-blue-300">source_table</span>: <span class="text-green-300">{{ store.output?.config.sourceTable }}</span>
    <span class="text-blue-300">sheet</span>: <span class="text-green-300">{{ store.output?.config.sheet }}</span>
    <span class="text-blue-300">output_dir</span>: <span class="text-green-300">{{ store.output?.config.outputDir }}</span>
    <span class="text-blue-300">filename</span>: <span class="text-green-300">{{ store.output?.config.filename }}</span>
    <span class="text-blue-300">columns</span>:
      <span v-for="c in store.output?.config.columns" :key="c.source">- <span class="text-blue-300">source</span>: <span class="text-green-300">{{ c.source }}</span>
        <span class="text-blue-300">target</span>: <span class="text-green-300">{{ c.target }}</span>
      </span></pre>
  </div>
</template>
<script setup lang="ts">
import { useWizardStore } from '../../stores/wizard'
const store = useWizardStore()
</script>
```

- [ ] **Step 2: Write ExportActions.vue**

Export buttons: copy YAML, download .yaml, download template, download all (.zip). Each button calls the `/api/wizard/generate` endpoint to get the final YAML/template.

- [ ] **Step 3: Write Step4ExportView.vue**

```vue
<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <StepIndicator :current-step="4" @goto="(s) => { store.goToStep(s); router.push(`/step/${s}`) }" />
    <div class="bg-white border border-slate-200 rounded-lg p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-base font-semibold">pipeline.yaml</h2>
        <div class="flex gap-2">
          <button @click="refreshPreview" class="px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">🔄 刷新预览</button>
          <button class="px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">📋 复制</button>
          <button class="px-2.5 py-1 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700">📥 下载</button>
        </div>
      </div>
      <YamlPreview />
    </div>
    <ExportActions />
    <div class="flex justify-between items-center pt-6 border-t border-slate-100 mt-6">
      <button @click="store.prevStep(); router.push('/step/3')" class="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md">&larr; 上一步</button>
      <router-link to="/" class="inline-flex items-center justify-center gap-2 px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700">✓ 完成</router-link>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useWizardStore } from '../../stores/wizard'
import StepIndicator from '../components/common/StepIndicator.vue'
import YamlPreview from '../components/step4/YamlPreview.vue'
import ExportActions from '../components/step4/ExportActions.vue'

const router = useRouter()
const store = useWizardStore()
function refreshPreview() { /* trigger re-render */ }
</script>
```

- [ ] **Step 4: Verify Step 4 builds**

Run: `cd configforge-web && npx vite build 2>&1 | tail -5`
Expected: `✓ built`

- [ ] **Step 5: Commit**

```bash
git add configforge-web/src/components/step4/ configforge-web/src/views/Step4ExportView.vue
git commit -m "feat: Step 4 - YamlPreview + ExportActions + Step4ExportView"
```


### Task 20: Integration — full wizard flow + production build

**Files:**
- Modify: `configforge-web/src/composables/useAiSuggest.ts` (wire up /api/ai/suggest)
- Modify: `configforge-web/src/composables/useErrorHandler.ts` (unified error dispatch)
- Modify: `configforge/server.py` (add static file mount for production)

- [ ] **Step 1: Write useAiSuggest composable**

```typescript
import { ref } from 'vue'
import type { AiSuggestion } from '../types/wizard'

export function useAiSuggest() {
  const suggesting = ref(false)
  const suggestion = ref<AiSuggestion | null>(null)
  const error = ref<string | null>(null)
  const aiConfigured = ref(false)

  async function askSuggestion(category: string, context: any) {
    suggesting.value = true; error.value = null
    try {
      const resp = await fetch('/api/ai/suggest', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, context }),
      })
      const data = await resp.json()
      if (!resp.ok) { error.value = data.error; return }
      suggestion.value = { content: data.content, category: data.category, status: 'pending', timestamp: Date.now() }
    } catch {
      error.value = 'AI 服务不可用'
    } finally { suggesting.value = false }
  }

  function accept() { if (suggestion.value) suggestion.value.status = 'accepted' }
  async function regenerate(feedback?: string) { if (suggestion.value) await askSuggestion(suggestion.value.category, { feedback }) }

  return { suggesting, suggestion, error, aiConfigured, askSuggestion, accept, regenerate }
}
```

- [ ] **Step 2: Write useErrorHandler composable**

```typescript
import { ref } from 'vue'

export function useErrorHandler() {
  const warning = ref<string | null>(null)
  const error = ref<string | null>(null)
  const fatal = ref<string | null>(null)

  function handleApiError(err: { message: string; code: string }) {
    if (err.code === 'INTERNAL_ERROR') fatal.value = err.message
    else error.value = err.message
  }

  function clearAll() { warning.value = null; error.value = null; fatal.value = null }

  return { warning, error, fatal, handleApiError, clearAll }
}
```

- [ ] **Step 3: Add static file mount to server.py for production**

```python
from fastapi.staticfiles import StaticFiles
# ... (all route registrations above)
# mount must be last
import os
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

- [ ] **Step 4: Full production build test**

```bash
cd configforge-web && npm run build
cp -r dist/* ../configforge/static/
cd ../configforge
python -m pytest tests/ -v
```

Expected: All backend tests pass. Frontend builds to static/.

- [ ] **Step 5: Quick integration smoke test**

```bash
cd configforge && uvicorn server:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/ | head -5
kill %1
```

Expected: `/api/health` returns `{"status":"ok"}`. `/` returns the Vue app HTML.

- [ ] **Step 6: Commit**

```bash
git add configforge-web/src/composables/ configforge/server.py configforge/static/
git commit -m "feat: integration - full wizard flow, AI composable, production build"
```

---

## Backend test summary (run before merging)

```bash
cd configforge && python -m pytest tests/ -v
```

Expected: all backend tests pass (≥16 tests covering generators, services, API endpoints).

## Frontend test summary (run before merging)

```bash
cd configforge-web && npx vitest run
```

Expected: all frontend tests pass (≥10 tests covering store, composables).

---
