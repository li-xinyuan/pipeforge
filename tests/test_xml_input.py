"""限制③C：XML 输入插件端到端测试。

验证：上传 xml 文件 → 配置输入源 → 执行 pipeline → 数据正确写入 SQLite。
对应方案 3.4 第二阶段步骤 6。
"""


from pipeforge.config.models import XmlInputConfig
from pipeforge.core.registry import PluginRegistry
from pipeforge.plugins.input.xml import XmlInputPlugin


class TestXmlInputPlugin:
    def test_config_model(self):
        assert XmlInputPlugin.config_model() == XmlInputConfig

    def test_registered_as_xml_input(self):
        cls = PluginRegistry.get("xml", "input")
        assert cls.config_model() is XmlInputConfig

    def test_read_rows_explicit_element(self, tmp_path):
        content = b"""<root>
            <item><a>1</a><b>2</b></item>
            <item><a>3</a><b>4</b></item>
        </root>"""
        file_path = tmp_path / "test.xml"
        file_path.write_bytes(content)

        plugin = XmlInputPlugin()
        config = XmlInputConfig(file=str(file_path), row_element="item")
        columns, rows = plugin._read_rows(str(file_path), config)
        assert set(columns) == {"a", "b"}
        rows_list = list(rows)
        assert len(rows_list) == 2

    def test_read_rows_auto_detect(self, tmp_path):
        content = b"""<root>
            <item><a>1</a></item>
            <item><a>2</a></item>
        </root>"""
        file_path = tmp_path / "auto.xml"
        file_path.write_bytes(content)

        plugin = XmlInputPlugin()
        config = XmlInputConfig(file=str(file_path))
        columns, rows = plugin._read_rows(str(file_path), config)
        rows_list = list(rows)
        assert len(rows_list) == 2


class TestXmlPipelineEndToEnd:
    """端到端：XML 输入 → SQL 处理 → 验证结果。"""

    def test_xml_input_to_sqlite(self, tmp_path):
        content = b"""<root>
            <item><name>Alice</name><age>30</age></item>
            <item><name>Bob</name><age>25</age></item>
        </root>"""
        xml_path = tmp_path / "input.xml"
        xml_path.write_bytes(content)

        yaml_content = """
scene:
  name: xml_test
  version: "1.0"

inputs:
  - name: people
    plugin: xml
    table: person
    param_key: people_file
    config:
      type: xml
      row_element: item

processors:
  - name: filter
    plugin: sql
    output_tables:
      - adults
    config:
      sql: |
        CREATE TABLE adults AS
        SELECT name, age FROM person WHERE age > 26
    checkpoints:
      - type: row_count
        table: adults
        min: 1
        max: 1
        on_failure: block
"""
        yaml_path = tmp_path / "pipeline.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        from pipeforge.core.engine import PipelineEngine

        engine = PipelineEngine(str(yaml_path))
        result = engine.execute(params={"people_file": str(xml_path)})

        assert "people" in result.inputs
        assert result.inputs["people"].rows_loaded == 2
        assert result.processors[0].tables_created == ["adults"]
        # checkpoint 验证 adults 表恰好 1 行
        assert len(result.checks) == 1
        assert result.checks[0].passed is True

    def test_xml_input_auto_detect(self, tmp_path):
        """自动检测行元素（无 row_element）。"""
        content = b"""<root>
            <item><name>Alice</name></item>
            <item><name>Bob</name></item>
        </root>"""
        xml_path = tmp_path / "auto.xml"
        xml_path.write_bytes(content)

        yaml_content = """
scene:
  name: xml_auto_test
  version: "1.0"

inputs:
  - name: people
    plugin: xml
    table: person
    param_key: people_file
    config:
      type: xml
"""
        yaml_path = tmp_path / "pipeline.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        from pipeforge.core.engine import PipelineEngine

        engine = PipelineEngine(str(yaml_path))
        result = engine.execute(params={"people_file": str(xml_path)})

        assert result.inputs["people"].rows_loaded == 2
