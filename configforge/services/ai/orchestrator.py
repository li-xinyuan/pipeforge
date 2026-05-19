import json
import re


SYSTEM_PROMPTS = {
    "scene": (
        "你是一个数据流水线配置专家。根据用户提供的流水线配置信息（输入源、SQL 处理、输出目标），"
        "生成一句简洁的中文场景描述（20-50字），概括这个数据流水线的用途和核心处理逻辑。"
        "返回 JSON: {\"description\": \"...\"}。不要输出其他内容。"
    ),
    "columns": (
        "你是一个数据分析专家。根据文件列名和样本数据，推荐列的类型、生成中文名称、推荐表名和参数键。"
        "返回纯 JSON，不要包含任何解释文字、markdown 标记或代码块。"
        "格式: {\"columnTypes\": {\"列名\": \"string|number|date|boolean\"}, "
        "\"name\": \"数据源中文名称\", "
        "\"tableName\": \"英文表名\", "
        "\"paramKeys\": [\"参数键1\"], "
        "\"joinKeys\": [{\"file\": \"文件名\", \"column\": \"列名\", \"file2\": \"文件名\", \"column2\": \"列名\"}]}。"
    ),
    "sql": (
        "你是一个 SQL 专家，针对 SQLite 数据库。根据表结构和用户的自然语言需求，生成 SQLite 兼容的 SQL。"
        "注意：表名用双引号包裹，列名必须来自表结构不要编造，使用 SQLite 支持的函数"
        "（GROUP BY, COUNT, JOIN, CASE WHEN 等）。"
        "重要：所有函数调用和计算列必须加 AS 别名（中文优先，用双引号包裹），"
        "例如 COUNT(*) AS \"人数\"、AVG(age) AS \"平均年龄\"。"
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
        inputs = context.get("inputs", [])
        sql = context.get("sql", "")
        output = context.get("output", {})
        output_tables = context.get("outputTables", [])

        # Pipeline-level context (Step 5)
        if inputs or sql:
            prompt += f"输入源: {json.dumps(inputs, ensure_ascii=False)}。"
            prompt += f"SQL 处理: {sql}。"
            prompt += f"输出表: {json.dumps(output_tables, ensure_ascii=False)}。"
            prompt += f"输出目标: {json.dumps(output, ensure_ascii=False)}。"
        else:
            # File-level context (backward compat)
            prompt += f"用户上传了 {context.get('fileCount', 0)} 个文件: {context.get('fileNames', [])}。"
            prompt += f"各文件列名: {context.get('columnsByFile', {})}。"
    elif category == "columns":
        inputs = context.get("inputs", [])
        if inputs:
            for inp in inputs:
                prompt += f"文件名: {inp.get('name', '')}。"
                prompt += f"列名: {inp.get('columns', [])}。"
                prompt += f"表名: {inp.get('table', '')}。"
                sample_rows = inp.get("sampleRows", [])
                if sample_rows:
                    prompt += f"样本数据(前5行): {json.dumps(sample_rows[:5], ensure_ascii=False)}。"
        else:
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
