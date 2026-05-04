from typing import Literal
from ..base import ConfigGenerator
from ...models.wizard import ExcelInputConfig
from ...core.registry import GeneratorRegistry


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
