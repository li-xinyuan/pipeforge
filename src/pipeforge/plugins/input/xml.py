"""限制③C：XML 输入插件（reader 适配器）。

基于 pipeforge.readers.xml 的全量读取接口，将 XML 文件加载到 SQLite。
"""
from pipeforge.config.models import XmlInputConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.input._reader_backed import ReaderBackedInputPlugin
from pipeforge.readers.xml import iter_xml_rows


@register_plugin("xml", "input")
class XmlInputPlugin(ReaderBackedInputPlugin):
    """XML 文件输入插件。"""

    @classmethod
    def config_model(cls) -> type[XmlInputConfig]:
        return XmlInputConfig

    def _read_rows(self, filepath: str, config: XmlInputConfig):
        with open(filepath, "rb") as f:
            file_content = f.read()
        return iter_xml_rows(file_content, row_element=config.row_element)
