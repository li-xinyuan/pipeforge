"""Tests for XML reader."""
import pytest
from configforge.services.xml_reader import read_xml_info, _find_row_elements, _element_to_dict


class TestFindRowElements:
    def test_auto_detect(self):
        import xml.etree.ElementTree as ET
        root = ET.fromstring("<root><item>1</item><item>2</item><item>3</item></root>")
        rows = _find_row_elements(root, "")
        assert len(rows) == 3

    def test_path_based(self):
        import xml.etree.ElementTree as ET
        root = ET.fromstring("<root><items><item>1</item><item>2</item></items></root>")
        rows = _find_row_elements(root, "items/item")
        assert len(rows) == 2

    def test_no_match(self):
        import xml.etree.ElementTree as ET
        root = ET.fromstring("<root><other>1</other></root>")
        rows = _find_row_elements(root, "items/item")
        assert len(rows) == 0


class TestElementToDict:
    def test_attributes(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<item id="1" name="test">text</item>')
        result = _element_to_dict(elem)
        assert result["@id"] == "1"
        assert result["@name"] == "test"
        assert result["text"] == "text"

    def test_child_elements(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring("<item><name>Alice</name><age>30</age></item>")
        result = _element_to_dict(elem)
        assert result["name"] == "Alice"
        assert result["age"] == "30"

    def test_nested_elements(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring("<item><address><city>Beijing</city></address></item>")
        result = _element_to_dict(elem)
        assert result["address.city"] == "Beijing"


class TestReadXmlInfo:
    def test_simple_array(self):
        xml = """<root><item><name>Alice</name><age>30</age></item><item><name>Bob</name><age>25</age></item></root>"""
        result = read_xml_info(xml.encode("utf-8"))
        assert "name" in result["columns"]
        assert "age" in result["columns"]
        assert len(result["sample_rows"]) == 2

    def test_with_row_element(self):
        xml = """<root><items><item><name>Alice</name></item><item><name>Bob</name></item></items></root>"""
        result = read_xml_info(xml.encode("utf-8"), row_element="items/item")
        assert "name" in result["columns"]
        assert len(result["sample_rows"]) == 2

    def test_attributes(self):
        xml = """<root><item id="1" name="test"/><item id="2" name="test2"/></root>"""
        result = read_xml_info(xml.encode("utf-8"))
        assert "@id" in result["columns"]
        assert "@name" in result["columns"]

    def test_empty_result(self):
        xml = """<root></root>"""
        result = read_xml_info(xml.encode("utf-8"))
        assert result["columns"] == []
        assert result["sample_rows"] == []

    def test_invalid_xml(self):
        with pytest.raises(Exception):
            read_xml_info(b"not xml")

    def test_max_sample_rows(self):
        items = "".join(f"<item><name>v{i}</name></item>" for i in range(20))
        xml = f"<root>{items}</root>"
        result = read_xml_info(xml.encode("utf-8"), max_sample_rows=5)
        assert len(result["sample_rows"]) == 5
