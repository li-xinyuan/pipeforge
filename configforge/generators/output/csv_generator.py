from .excel_output import ExcelOutputGenerator
from ...models.wizard import CsvOutputConfig
from ...core.registry import GeneratorRegistry


@GeneratorRegistry.register("csv", "output")
class CsvOutputGenerator(ExcelOutputGenerator):
    """CSV output generator — reuses Excel logic; differences are in config fields."""

    @classmethod
    def config_model(cls):
        return CsvOutputConfig
