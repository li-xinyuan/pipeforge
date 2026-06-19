import xml.etree.ElementTree as ET


MAX_XML_ROWS = 50000


def read_xml_info(
    file_content: bytes,
    row_element: str = "",
    max_sample_rows: int = 10,
) -> dict:
    """Read XML file content, return columns and sample_rows (same interface as read_excel_info).

    Args:
        file_content: Raw XML bytes
        row_element: XPath-like path to the repeating element (e.g. "items/item").
                     If empty, auto-detect by finding the most frequent child element.
        max_sample_rows: Max number of sample rows to return
    """
    root = ET.fromstring(file_content.decode("utf-8"))

    # Find row elements
    row_elems = _find_row_elements(root, row_element)
    if not row_elems:
        return {"sheets": [], "columns": [], "sample_rows": []}

    # Extract data from row elements
    all_keys: list[str] = []
    rows_data: list[dict] = []

    for i, elem in enumerate(row_elems):
        if i >= MAX_XML_ROWS:
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
