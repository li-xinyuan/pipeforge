import json
import re

MAX_USER_INPUT_LENGTH = 2000


def _sanitize_user_input(text: str) -> str:
    """Truncate and delimit user-supplied text to prevent prompt injection."""
    if not isinstance(text, str):
        return str(text)
    # Truncate to prevent prompt flooding
    if len(text) > MAX_USER_INPUT_LENGTH:
        text = text[:MAX_USER_INPUT_LENGTH]
    # Strip common injection patterns
    text = re.sub(r'(?i)(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|messages?|context)', '[FILTERED]', text)
    text = re.sub(r'(?i)(you\s+are\s+now|from\s+now\s+on\s+you\s+are|your\s+new\s+role\s+is)', '[FILTERED]', text)
    return text


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
    "chat": (
        "你是 ConfigForge 的 AI 助手，内嵌在一个数据管道配置平台中。"
        "该平台通过可视化向导帮用户将多种数据源（Excel、CSV、数据库）加工转换为标准化输出。"
        "用户当前正在一个 5 步向导中：场景信息 → 输入源 → SQL 处理 → 输出配置 → 预览导出。\n\n"
        "## 你能做什么\n"
        "- 根据用户的中文描述生成 SQLite 兼容的 SQL 查询（GROUP BY、JOIN、CASE WHEN、窗口函数等）\n"
        "- 分析上传文件的列结构，推断列类型（string/number/date/boolean）和业务含义\n"
        "- 自动推断源列与目标列的映射关系\n"
        "- 根据流水线配置生成场景名称和描述\n\n"
        "## 你应该如何回复\n"
        "1. 如果用户描述了一个数据查询需求（如「统计各部门人数」「查询上月销售总额」），"
        "请生成 SQLite SQL 并返回 JSON: {\"sql\": \"...\", \"outputTables\": [\"...\"], \"explanation\": \"...\"}。\n"
        "2. 如果用户是打招呼、闲聊、询问你的身份或能力、问与数据管道无关的问题，"
        "请友好地自我介绍，告诉用户你能帮他做什么，引导他在对应步骤使用你的能力。"
        "例如：用户在第 2 步上传文件后可以让你「分析列结构」，在第 3 步描述查询需求让你「生成 SQL」。\n"
        "3. 如果用户的问题模糊不清、缺少必要信息（如表结构），请追问澄清，不要猜测编造。\n\n"
        "## 重要约束\n"
        "- 生成的 SQL 必须兼容 SQLite 语法，表名用双引号包裹\n"
        "- 列名必须来自用户提供的表结构，不要编造列名\n"
        "- 所有计算列和函数调用必须加 AS 别名，中文别名用双引号包裹：COUNT(*) AS \"人数\"\n"
        "- 当返回 JSON 时，不要包裹在 markdown 代码块中（不要用 ```json），直接输出纯 JSON 文本\n"
        "- 保持回复简洁、有针对性，不要堆砌大量文字"
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
        prompt += f"需求: {_sanitize_user_input(context.get('naturalLanguage', ''))}。"
    elif category == "mapping":
        prompt += f"源列: {context.get('sourceColumns', [])}。"
        prompt += f"目标列: {context.get('targetColumns', [])}。"
    elif category == "diagnose":
        prompt += f"YAML: {context.get('yaml', '')}。"
        prompt += f"错误: {context.get('errorLog', '')}。"
    elif category == "chat":
        current_step = context.get("currentStep", 1)
        scene_name = context.get("sceneName", "")
        inputs = context.get("inputs", [])
        sql = context.get("processorSql", "")
        output_tables = context.get("outputTables", [])
        prompt += f"用户当前在第 {current_step} 步。"
        if scene_name:
            prompt += f"场景名称: {scene_name}。"
        if inputs:
            input_info = []
            for inp in inputs:
                info: dict = {"plugin": inp.get("plugin"), "table": inp.get("table")}
                cols = inp.get("columns")
                if cols:
                    info["columns"] = cols
                input_info.append(info)
            prompt += f"已添加的输入源: {json.dumps(input_info, ensure_ascii=False)}。"
        if sql:
            prompt += f"当前 SQL: {sql[:500]}。"
        if output_tables:
            prompt += f"输出表: {output_tables}。"
        prompt += f"用户消息: {_sanitize_user_input(context.get('naturalLanguage', ''))}"

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
