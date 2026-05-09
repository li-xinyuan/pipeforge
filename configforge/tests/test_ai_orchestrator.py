from configforge.services.ai.orchestrator import build_prompt, parse_response


def test_build_prompt_sql():
    prompt = build_prompt("sql", {
        "inputs": [{"name": "person", "table": "t", "columns": ["name", "age"]}],
        "naturalLanguage": "查询所有年龄大于30的人",
    })
    assert "person" in prompt
    assert "t" in prompt
    assert "年龄大于30" in prompt


def test_build_prompt_mapping():
    prompt = build_prompt("mapping", {
        "sourceColumns": ["姓名", "年龄"],
        "targetColumns": ["员工姓名", "员工年龄"],
    })
    assert "姓名" in prompt
    assert "员工姓名" in prompt


def test_parse_direct_json():
    result = parse_response('{"sql": "SELECT * FROM t"}')
    assert "SELECT" in result


def test_parse_json_from_markdown():
    result = parse_response('```json\n{"sql": "SELECT 1"}\n```')
    assert "SELECT 1" in result


def test_parse_non_json_wraps_in_raw():
    result = parse_response("plain text without json")
    import json
    parsed = json.loads(result)
    assert parsed["raw"] == "plain text without json"
    assert parsed["is_json"] is False
