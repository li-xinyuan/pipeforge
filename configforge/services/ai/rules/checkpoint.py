"""规则引擎：数据检查点推荐。

从 api/ai.py 抽取，当 AI 未配置时基于列元数据启发式推荐 CheckRule。
"""


def checkpoint_suggestions(columns: list[dict]) -> list[dict]:
    """Rule-based checkpoint suggestions using column metadata heuristics.

    Falls back when AI is not configured. Returns a list of CheckRule dicts.
    """
    suggestions: list[dict] = []
    for col in columns:
        name = (col.get("name") or "").lower()
        col_type = (col.get("type") or "").lower()

        # Email column → suggest regex/uniqueness check
        if "email" in name or "mail" in name:
            suggestions.append({
                "type": "custom_sql",
                "sql": f"SELECT COUNT(*) as cnt FROM {{{{table}}}} WHERE {col.get('name')} NOT LIKE '%@%'",
                "result_column": "cnt",
                "comparison": "==",
                "expected_value": 0,
                "on_failure": "warn",
                "description": f"邮箱格式检查（{col.get('name')}）",
            })

        # Numeric column → suggest range check
        if col_type in ("int", "integer", "float", "double", "decimal", "number"):
            suggestions.append({
                "type": "value_range",
                "table": "{{table}}",
                "column": col.get("name"),
                "min_value": None,
                "max_value": None,
                "on_failure": "warn",
                "description": f"数值范围检查（{col.get('name')}）",
            })

        # ID column → suggest uniqueness check
        if "id" in name or name.endswith("_id") or name == "id":
            suggestions.append({
                "type": "uniqueness",
                "table": "{{table}}",
                "column": col.get("name"),
                "on_failure": "block",
                "description": f"唯一性检查（{col.get('name')}）",
            })

        # Date column → suggest not-null check
        if "date" in name or "time" in name or col_type in ("date", "datetime", "timestamp"):
            suggestions.append({
                "type": "null_rate",
                "table": "{{table}}",
                "column": col.get("name"),
                "max_null_rate": 0.0,
                "on_failure": "warn",
                "description": f"日期非空检查（{col.get('name')}）",
            })

    # Always suggest a row_count check as a baseline
    suggestions.append({
        "type": "row_count",
        "table": "{{table}}",
        "min": 1,
        "max": None,
        "on_failure": "warn",
        "description": "行数检查（确保至少 1 行数据）",
    })

    return suggestions
