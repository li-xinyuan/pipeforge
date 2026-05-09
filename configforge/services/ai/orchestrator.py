import json
import re


SYSTEM_PROMPTS = {
    "scene": (
        "你是一个数据流水线配置专家。根据用户上传的文件信息，生成简洁的中文场景名（5-15字）"
        "和一句话描述（20-50字）。返回 JSON: {\"name\": \"...\", \"description\": \"...\"}。"
        "不要输出其他内容。"
    ),
    "columns": (
        "你是一个数据分析专家。根据文件列名和样本数据，推荐列的类型、检测可能的关联键。"
        "返回 JSON: {\"columnTypes\": {\"列名\": \"string|number|date|boolean\"}, "
        "\"joinKeys\": [{\"file1\": \"列名\", \"file2\": \"列名\"}], "
        "\"suggestedTableNames\": [\"...\"], \"suggestedParamKeys\": [\"...\"]}。"
    ),
    "sql": (
        "你是一个 SQL 专家，针对 SQLite 数据库。根据表结构和用户的自然语言需求，生成 SQLite 兼容的 SQL。"
        "注意：表名用双引号包裹，列名必须来自表结构不要编造，使用 SQLite 支持的函数"
        "（GROUP BY, COUNT, JOIN, CASE WHEN 等）。"
        "返回 JSON: {\"sql\": \"...\", \"outputTables\": [\"...\"], \"explanation\": \"简短说明\"}。"
    ),
    "mapping": (
        "你是一个数据映射专家。根据源列名和目标列名列表，推断最佳映射关系。"
        "匹配规则：语义相似（同义词、中英文对应）、名称相似（编辑距离、包含关系）、位置顺序。"
        "返回 JSON: {\"mappings\": [{\"source\": \"源列名\", \"target\": \"目标列名\"}]}。"
        "源列没有对应目标列的不要强行映射。"
    ),
    "diagnose": (
        "你是一个数据管道调试专家。根据 YAML 配置和错误日志，分析失败原因并给出修复建议。"
        "返回 JSON: {\"cause\": \"根因一句话\", \"suggestions\": [\"具体修复步骤\"], \"severity\": \"error|warning\"}。"
    ),
}


def build_prompt(category: str, context: dict) -> str:
    if category not in SYSTEM_PROMPTS:
        raise ValueError(f"Unknown AI category: {category}")
    if not isinstance(context, dict):
        raise TypeError(f"context must be dict, got {type(context).__name__}")

    system = SYSTEM_PROMPTS[category]
    prompt = system + "\n\n"

    if category == "scene":
        prompt += f"用户上传了 {context.get('fileCount', 0)} 个文件: {context.get('fileNames', [])}。"
        prompt += f"各文件列名: {context.get('columnsByFile', {})}。"
    elif category == "columns":
        prompt += f"文件列名: {context.get('fileColumns', [])}。"
        prompt += f"样本数据: {context.get('sampleRows', [])}。"
    elif category == "sql":
        prompt += f"表结构: {context.get('inputs', [])}。"
        prompt += f"需求: {context.get('naturalLanguage', '')}。"
    elif category == "mapping":
        prompt += f"源列: {context.get('sourceColumns', [])}。"
        prompt += f"目标列: {context.get('targetColumns', [])}。"
    elif category == "diagnose":
        prompt += f"YAML: {context.get('yaml', '')}。"
        prompt += f"错误: {context.get('errorLog', '')}。"

    return prompt


def parse_response(text: str) -> str:
    text = text.strip()
    # Try direct JSON parse first
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    # Try extract from markdown ```json block
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        block = m.group(1).strip()
        try:
            json.loads(block)
            return block
        except json.JSONDecodeError:
            pass
    # Return wrapped so frontend knows it's non-JSON
    return json.dumps({"raw": text, "is_json": False})
