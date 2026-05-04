from ..base import ConfigGenerator
from ...models.wizard import ExcelOutputConfig, ColumnMappingItem
from ...core.registry import GeneratorRegistry


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
            errors.append("at least one columns mapping is required")
        return errors
