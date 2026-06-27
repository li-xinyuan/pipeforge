"""限制③C：JSON 输入插件（reader 适配器）。

基于 pipeforge.readers.json 的全量读取接口，将 JSON 文件加载到 SQLite。
"""
from pipeforge.config.models import JsonInputConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.input._reader_backed import ReaderBackedInputPlugin
from pipeforge.readers.json import iter_json_rows


@register_plugin("json", "input")
class JsonInputPlugin(ReaderBackedInputPlugin):
    """JSON 文件输入插件。"""

    @classmethod
    def config_model(cls) -> type[JsonInputConfig]:
        return JsonInputConfig

    def _read_rows(self, filepath: str, config: JsonInputConfig):
        with open(filepath, "rb") as f:
            file_content = f.read()
        return iter_json_rows(file_content, flatten_separator=config.flatten_separator)
