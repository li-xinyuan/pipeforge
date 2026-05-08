from .excel_output import ExcelOutputGenerator
from ...core.registry import GeneratorRegistry


@GeneratorRegistry.register("csv", "output")
class CsvOutputGenerator(ExcelOutputGenerator):
    """CSV output generator — reuses Excel logic; differences are in config fields."""
    pass
