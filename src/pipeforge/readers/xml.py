"""XML 流式读取器（pipeforge 层）。

限制③C：为 ReaderBackedInputPlugin 提供全量读取接口。
纯数据工具，不依赖 configforge。
"""
import io
import xml.etree.ElementTree as ET
from typing import Iterator

MAX_XML_ROWS = 50000


def iter_xml_rows(
    file_content: bytes,
    row_element: str = "",
) -> tuple[list[str], Iterator[tuple]]:
    """全量读取 XML，返回 (列名列表, 行迭代器)。

    限制③C reader 适配器第一步：为 ReaderBackedInputPlugin 提供全量读取接口。
    与 read_xml_info（轻量预览）不同，本函数流式产出所有行，供 pipeline 执行。

    两遍扫描（file_content 已在内存）：
    1. 第一遍：收集所有列名（不同行元素可能有不同子元素，取并集）
    2. 第二遍：按列名顺序产出每行为 tuple（缺失键 → ""）

    Args:
        file_content: XML 文件原始字节
        row_element: 行元素路径（如 "items/item"），空则自动检测最高频子元素

    Returns:
        (columns, row_iterator): 列名列表 + 行元组迭代器
    """
    columns = _collect_xml_columns(file_content, row_element)
    return columns, _iter_xml_rows(file_content, row_element, columns)


def _collect_xml_columns(file_content: bytes, row_element: str) -> list[str]:
    """第一遍：收集所有列名（键的并集）。"""
    all_keys: list[str] = []
    seen: set[str] = set()

    for row_dict in _iter_xml_dicts(file_content, row_element):
        for key in row_dict:
            if key not in seen:
                seen.add(key)
                all_keys.append(key)

    return all_keys


def _iter_xml_rows(
    file_content: bytes,
    row_element: str,
    columns: list[str],
) -> Iterator[tuple]:
    """第二遍：按列名顺序产出每行为 tuple。"""
    for row_dict in _iter_xml_dicts(file_content, row_element):
        yield tuple(str(row_dict.get(col, "")) if row_dict.get(col, "") is not None else "" for col in columns)


def _iter_xml_dicts(file_content: bytes, row_element: str) -> Iterator[dict]:
    """流式产出 XML 行元素转 dict。

    显式 row_element 用 iterparse（真正流式，边解析边释放）；
    自动检测需先解析 root（非流式），但行元素转 dict 仍迭代产出。
    """
    if row_element:
        target_tag = row_element.strip("/").split("/")[-1]
        context = ET.iterparse(io.BytesIO(file_content), events=("end",))
        for _event, elem in context:
            if elem.tag == target_tag:
                yield _element_to_dict(elem)
                elem.clear()
    else:
        root = ET.fromstring(file_content.decode("utf-8"))
        row_elems = _find_row_elements(root, row_element)
        for elem in row_elems:
            yield _element_to_dict(elem)


def read_xml_info(
    file_content: bytes,
    row_element: str = "",
    max_sample_rows: int = 10,
    max_rows: int = MAX_XML_ROWS,
) -> dict:
    """Read XML file content, return columns and sample_rows (preview interface).

    Args:
        file_content: Raw XML bytes
        row_element: XPath-like path to the repeating element (e.g. "items/item").
                     If empty, auto-detect by finding the most frequent child element.
        max_sample_rows: Max number of sample rows to return
        max_rows: Max number of row elements to process (streaming stops after this)
    """
    # Use iterparse for incremental parsing — only process up to max_rows elements
    all_keys: list[str] = []
    rows_data: list[dict] = []

    if row_element:
        # Path-based: use iterparse to find matching elements incrementally
        target_tag = row_element.strip("/").split("/")[-1]
        context = ET.iterparse(io.BytesIO(file_content), events=("end",))
        for _event, elem in context:
            if elem.tag == target_tag:
                if len(rows_data) >= max_rows:
                    elem.clear()
                    continue
                row_dict = _element_to_dict(elem)
                rows_data.append(row_dict)
                for key in row_dict:
                    if key not in all_keys:
                        all_keys.append(key)
                elem.clear()
    else:
        # Auto-detect: need to parse root first to find the most frequent tag
        root = ET.fromstring(file_content.decode("utf-8"))
        row_elems = _find_row_elements(root, row_element)
        if not row_elems:
            return {"sheets": [], "columns": [], "sample_rows": []}

        for i, elem in enumerate(row_elems):
            if i >= max_rows:
                break
            row_dict = _element_to_dict(elem)
            rows_data.append(row_dict)
            for key in row_dict:
                if key not in all_keys:
                    all_keys.append(key)

    if not rows_data:
        return {"sheets": [], "columns": [], "sample_rows": []}

    columns = all_keys
    sample_rows = []
    for row in rows_data[:max_sample_rows]:
        sample_rows.append([str(row.get(col, "")) for col in columns])

    return {
        "sheets": [],
        "columns": columns,
        "sample_rows": sample_rows,
    }


def _find_row_elements(root: ET.Element, row_element: str) -> list[ET.Element]:
    """Find the repeating row elements in the XML tree."""
    if row_element:
        # Support simple path like "items/item"
        parts = row_element.strip("/").split("/")
        current = [root]
        for part in parts[:-1]:
            next_level = []
            for elem in current:
                next_level.extend(elem.findall(part))
            current = next_level
            if not current:
                return []
        last_part = parts[-1]
        result = []
        for elem in current:
            result.extend(elem.findall(last_part))
        return result

    # Auto-detect: find the child element that appears most frequently
    child_counts: dict[str, int] = {}
    for child in root:
        tag = child.tag
        child_counts[tag] = child_counts.get(tag, 0) + 1

    if not child_counts:
        return []

    # Pick the most frequent tag as row element
    most_frequent = max(child_counts, key=child_counts.get)
    return root.findall(most_frequent)


def _element_to_dict(elem: ET.Element) -> dict:
    """Convert an XML element to a flat dict, extracting attributes and text."""
    result: dict = {}

    # Add attributes with @ prefix
    for attr_key, attr_val in elem.attrib.items():
        result[f"@{attr_key}"] = attr_val

    # Add text content
    if elem.text and elem.text.strip():
        result["text"] = elem.text.strip()

    # Add child elements
    for child in elem:
        tag = child.tag
        if len(child) > 0:
            # Nested element: flatten with dot notation
            nested = _element_to_dict(child)
            for nested_key, nested_val in nested.items():
                result[f"{tag}.{nested_key}"] = nested_val
        else:
            # Leaf element
            value = child.text.strip() if child.text and child.text.strip() else ""
            if tag in result:
                # Duplicate tag: convert to list representation
                existing = result[tag]
                if not isinstance(existing, list):
                    result[tag] = [existing]
                result[tag].append(value)
            else:
                result[tag] = value

    return result
