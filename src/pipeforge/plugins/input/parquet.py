"""限制③C：Parquet 输入插件（reader 适配器）。

基于 pipeforge.readers.parquet 的全量读取接口，将 Parquet 文件加载到 SQLite。
"""
from pipeforge.config.models import ParquetInputConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.input._reader_backed import ReaderBackedInputPlugin
from pipeforge.readers.parquet import iter_parquet_rows


@register_plugin("parquet", "input")
class ParquetInputPlugin(ReaderBackedInputPlugin):
    """Parquet 文件输入插件。"""

    @classmethod
    def config_model(cls) -> type[ParquetInputConfig]:
        return ParquetInputConfig

    def _read_rows(self, filepath: str, config: ParquetInputConfig):
        return iter_parquet_rows(filepath)
