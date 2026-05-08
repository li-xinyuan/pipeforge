from configforge.models.wizard import (
    WizardState,
    SceneInfo,
    SceneInitRequest,
    SceneInitResponse,
    InputInferRequest,
    InputInferResponse,
    OutputInferRequest,
    OutputInferResponse,
    ColumnMappingItem,
)
from configforge.services.excel_reader import read_excel_info
from configforge.services.csv_reader import read_csv_info
from configforge.services.yaml_builder import build_yaml
import os

UPLOAD_DIR = "tmp/uploads"


def init_scene(req: SceneInitRequest) -> SceneInitResponse:
    return SceneInitResponse(
        scene=SceneInfo(name="新场景", description="", version="1.0")
    )


def infer_input(
    input_name: str, req: InputInferRequest
) -> InputInferResponse:
    path = os.path.join(UPLOAD_DIR, req.file_id)
    with open(path, "rb") as f:
        content = f.read()
    if req.type == "csv":
        info = read_csv_info(content)
    else:
        import io
        info = read_excel_info(io.BytesIO(content))
    return InputInferResponse(
        columns=[
            {
                "name": c,
                "sample_values": (
                    info["sample_rows"][0][:3] if info["sample_rows"] else []
                ),
            }
            for c in info["columns"]
        ],
        suggested_table=input_name,
        suggested_param_key=f"{input_name}_file",
    )


def infer_output(req: OutputInferRequest) -> OutputInferResponse:
    cols = []
    return OutputInferResponse(suggested_columns=cols)


def generate(state: WizardState) -> dict:
    yaml = build_yaml(state)
    return {"yaml": yaml}
