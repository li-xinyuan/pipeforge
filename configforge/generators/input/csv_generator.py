from .excel_input import ExcelInputGenerator
from ...core.registry import GeneratorRegistry


@GeneratorRegistry.register("csv", "input")
class CsvInputGenerator(ExcelInputGenerator):
    """CSV input generator — reuses Excel logic; differences are in config fields."""
    pass
