"""Tests for T-5D-05: AI 辅助增强 — suggest-checkpoint, suggest-mapping, optimize-suggestions.

These tests focus on the rule-based fallback path (when AI is not configured)
because the test environment has no AI backend. The rule-based engine is
responsible for delivering reasonable suggestions without AI.
"""
import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from configforge.api.ai import (
    _rule_based_checkpoint_suggestions,
    _rule_based_mapping_suggestions,
)
from configforge.server import app


@pytest.fixture(autouse=True)
def _isolate_ai_settings():
    """每个测试使用独立临时文件，防止测试间状态泄漏。"""
    import configforge.services.ai.settings as mod
    orig = mod.SETTINGS_FILE
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(tmp)
    mod.SETTINGS_FILE = tmp

    # Also isolate rate limiter storage
    import configforge.api.ai as ai_mod
    orig_limiter = ai_mod._rate_limiter
    from configforge.utils.rate_limit import RateLimiter
    fd2, tmp2 = tempfile.mkstemp(suffix=".json")
    os.close(fd2)
    os.unlink(tmp2)
    ai_mod._rate_limiter = RateLimiter(max_requests=20, window_seconds=60, storage_path=tmp2)

    yield

    mod.SETTINGS_FILE = orig
    ai_mod._rate_limiter = orig_limiter
    if os.path.exists(tmp):
        os.unlink(tmp)
    if os.path.exists(tmp2):
        os.unlink(tmp2)


# ============================================================================
# Rule-based checkpoint suggestions (_rule_based_checkpoint_suggestions)
# ============================================================================


class TestRuleBasedCheckpointSuggestions:
    """测试规则引擎对检查规则的推荐能力。"""

    def test_email_column_triggers_format_check(self):
        columns = [{"name": "email", "type": "varchar", "sample_values": ["a@b.com"]}]
        suggestions = _rule_based_checkpoint_suggestions(columns)
        # 应有 email 格式检查 + 行数检查 baseline
        assert any(s["type"] == "custom_sql" and "@" in s["sql"] for s in suggestions)
        assert any(s["type"] == "row_count" for s in suggestions)

    def test_numeric_column_triggers_range_check(self):
        columns = [{"name": "age", "type": "int", "sample_values": [25]}]
        suggestions = _rule_based_checkpoint_suggestions(columns)
        assert any(s["type"] == "value_range" and s["column"] == "age" for s in suggestions)

    def test_numeric_column_variants(self):
        """测试 int/float/double/decimal/number 各种数值类型。"""
        for col_type in ["int", "integer", "float", "double", "decimal", "number"]:
            columns = [{"name": "amount", "type": col_type, "sample_values": []}]
            suggestions = _rule_based_checkpoint_suggestions(columns)
            assert any(s["type"] == "value_range" for s in suggestions), \
                f"数值类型 {col_type} 应触发范围检查"

    def test_id_column_triggers_uniqueness_check(self):
        columns = [{"name": "user_id", "type": "bigint", "sample_values": []}]
        suggestions = _rule_based_checkpoint_suggestions(columns)
        assert any(
            s["type"] == "uniqueness" and s["column"] == "user_id" for s in suggestions
        )

    def test_pure_id_column_triggers_uniqueness_check(self):
        columns = [{"name": "id", "type": "int", "sample_values": []}]
        suggestions = _rule_based_checkpoint_suggestions(columns)
        # id 也是数值类型，应有 uniqueness + value_range + row_count
        assert any(s["type"] == "uniqueness" and s["column"] == "id" for s in suggestions)

    def test_date_column_triggers_null_rate_check(self):
        columns = [{"name": "created_at", "type": "datetime", "sample_values": []}]
        suggestions = _rule_based_checkpoint_suggestions(columns)
        assert any(
            s["type"] == "null_rate" and s["column"] == "created_at"
            for s in suggestions
        )

    def test_date_in_name_triggers_null_rate(self):
        columns = [{"name": "signup_date", "type": "varchar", "sample_values": []}]
        suggestions = _rule_based_checkpoint_suggestions(columns)
        assert any(
            s["type"] == "null_rate" and s["column"] == "signup_date"
            for s in suggestions
        )

    def test_always_baseline_row_count_check(self):
        """即使没有特殊列，也应该有 baseline 行数检查。"""
        columns = [{"name": "data", "type": "text", "sample_values": []}]
        suggestions = _rule_based_checkpoint_suggestions(columns)
        assert len(suggestions) >= 1
        assert suggestions[-1]["type"] == "row_count"
        assert suggestions[-1]["min"] == 1

    def test_mixed_columns_generates_multiple_suggestions(self):
        columns = [
            {"name": "id", "type": "int", "sample_values": []},
            {"name": "email", "type": "varchar", "sample_values": []},
            {"name": "age", "type": "int", "sample_values": []},
            {"name": "created_at", "type": "datetime", "sample_values": []},
        ]
        suggestions = _rule_based_checkpoint_suggestions(columns)
        types = {s["type"] for s in suggestions}
        assert "custom_sql" in types  # email
        assert "value_range" in types  # age
        assert "uniqueness" in types  # id
        assert "null_rate" in types  # created_at
        assert "row_count" in types  # baseline

    def test_empty_columns_returns_only_baseline(self):
        """空列数组仅返回 baseline 行数检查。"""
        suggestions = _rule_based_checkpoint_suggestions([])
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "row_count"

    def test_placeholder_table_token_in_suggestions(self):
        """规则引擎生成的 sql 应包含 {{table}} 占位符。"""
        columns = [{"name": "email", "type": "varchar", "sample_values": []}]
        suggestions = _rule_based_checkpoint_suggestions(columns)
        email_rule = next(s for s in suggestions if s["type"] == "custom_sql")
        assert "{{table}}" in email_rule["sql"]


# ============================================================================
# Rule-based mapping suggestions (_rule_based_mapping_suggestions)
# ============================================================================


class TestRuleBasedMappingSuggestions:
    """测试规则引擎的列映射匹配能力。"""

    def test_exact_match(self):
        """完全相同的列名应得到 1.0 置信度。"""
        mappings = _rule_based_mapping_suggestions(
            source_columns=["name", "email"],
            target_columns=["name", "email"],
        )
        assert len(mappings) == 2
        for m in mappings:
            assert m["confidence"] == 1.0
            assert m["reason"] == "名称完全匹配"

    def test_synonym_match_chinese_english(self):
        """中英文同义词匹配应得到 0.9 置信度。"""
        mappings = _rule_based_mapping_suggestions(
            source_columns=["name"],
            target_columns=["名称"],
        )
        assert len(mappings) == 1
        assert mappings[0]["source"] == "name"
        assert mappings[0]["target"] == "名称"
        assert mappings[0]["confidence"] == 0.9
        assert mappings[0]["reason"] == "同义词匹配"

    def test_synonym_match_email(self):
        mappings = _rule_based_mapping_suggestions(
            source_columns=["email"],
            target_columns=["邮箱"],
        )
        assert mappings[0]["confidence"] == 0.9

    def test_synonym_match_phone(self):
        mappings = _rule_based_mapping_suggestions(
            source_columns=["phone"],
            target_columns=["电话"],
        )
        assert mappings[0]["confidence"] == 0.9

    def test_synonym_match_address(self):
        mappings = _rule_based_mapping_suggestions(
            source_columns=["address"],
            target_columns=["地址"],
        )
        assert mappings[0]["confidence"] == 0.9

    def test_normalized_match_underscore(self):
        """规范化后匹配（下划线/空格差异）—— 由于 normalize 已移除下划线，视为完全匹配。"""
        mappings = _rule_based_mapping_suggestions(
            source_columns=["user_name"],
            target_columns=["username"],
        )
        assert len(mappings) == 1
        # _normalize already strips underscores, so user_name ≡ username → exact match (1.0)
        assert mappings[0]["confidence"] == 1.0
        assert mappings[0]["reason"] == "名称完全匹配"

    def test_substring_match(self):
        """子串匹配应得到 0.6 置信度。"""
        mappings = _rule_based_mapping_suggestions(
            source_columns=["name"],
            target_columns=["full_user_name"],
        )
        assert len(mappings) == 1
        assert mappings[0]["confidence"] == 0.6
        assert mappings[0]["reason"] == "子串匹配"

    def test_no_match_returns_empty(self):
        """完全不相关的列名应没有匹配。"""
        mappings = _rule_based_mapping_suggestions(
            source_columns=["xyz_unknown"],
            target_columns=["abc_random"],
        )
        assert mappings == []

    def test_used_targets_not_reused(self):
        """已被占用的目标列不应被重复匹配。"""
        mappings = _rule_based_mapping_suggestions(
            source_columns=["name", "username"],
            target_columns=["name"],
        )
        # 第一个 name 完全匹配占用了 name，第二个 username 没有目标可匹配
        assert len(mappings) == 1
        assert mappings[0]["source"] == "name"
        assert mappings[0]["target"] == "name"

    def test_priority_exact_over_substring(self):
        """精确匹配优先于子串匹配。"""
        mappings = _rule_based_mapping_suggestions(
            source_columns=["name"],
            target_columns=["name", "full_name"],
        )
        assert len(mappings) == 1
        assert mappings[0]["target"] == "name"
        assert mappings[0]["confidence"] == 1.0

    def test_many_synonyms(self):
        """测试多个同义词组同时工作。"""
        mappings = _rule_based_mapping_suggestions(
            source_columns=["name", "email", "phone", "address"],
            target_columns=["姓名", "邮箱", "电话", "地址"],
        )
        assert len(mappings) == 4
        for m in mappings:
            assert m["confidence"] == 0.9

    def test_mixed_match_types(self):
        """混合匹配类型：精确 + 同义词 + 子串。"""
        mappings = _rule_based_mapping_suggestions(
            source_columns=["email", "name", "code"],
            target_columns=["email", "名称", "barcode"],
        )
        # email 精确匹配 email
        # name → 名称 同义词匹配
        # code → barcode 子串匹配
        assert len(mappings) == 3
        confidences = sorted(m["confidence"] for m in mappings)
        assert confidences == [0.6, 0.9, 1.0]


# ============================================================================
# POST /api/ai/suggest-checkpoint endpoint
# ============================================================================


class TestSuggestCheckpointEndpoint:
    """测试 POST /api/ai/suggest-checkpoint 端点。"""

    @pytest.mark.anyio
    async def test_returns_rules_when_ai_disabled(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/suggest-checkpoint", json={
                "columns": [
                    {"name": "email", "type": "varchar"},
                    {"name": "age", "type": "int"},
                ],
                "table_name": "users",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "rules"
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) > 0
        # {{table}} 占位符应被替换为 table_name
        for s in data["suggestions"]:
            if "table" in s:
                assert s["table"] == "users"
            if "sql" in s:
                assert "{{table}}" not in s["sql"]

    @pytest.mark.anyio
    async def test_uses_default_table_when_missing(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/suggest-checkpoint", json={
                "columns": [{"name": "id", "type": "int"}],
            })
        assert resp.status_code == 200
        data = resp.json()
        for s in data["suggestions"]:
            if "table" in s:
                assert s["table"] == "result"

    @pytest.mark.anyio
    async def test_invalid_json_body(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/ai/suggest-checkpoint",
                content="not json",
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_empty_columns_rejected(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/suggest-checkpoint", json={
                "columns": [],
                "table_name": "users",
            })
        assert resp.status_code == 400
        assert "columns" in resp.json()["error"]

    @pytest.mark.anyio
    async def test_missing_columns_field_rejected(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/suggest-checkpoint", json={
                "table_name": "users",
            })
        assert resp.status_code == 400


# ============================================================================
# POST /api/ai/suggest-mapping endpoint
# ============================================================================


class TestSuggestMappingEndpoint:
    """测试 POST /api/ai/suggest-mapping 端点。"""

    @pytest.mark.anyio
    async def test_returns_rules_when_ai_disabled(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/suggest-mapping", json={
                "source_columns": ["name", "email"],
                "target_columns": ["名称", "邮箱"],
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "rules"
        assert len(data["mappings"]) == 2
        for m in data["mappings"]:
            assert m["confidence"] == 0.9

    @pytest.mark.anyio
    async def test_exact_match_via_endpoint(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/suggest-mapping", json={
                "source_columns": ["id", "name"],
                "target_columns": ["id", "name"],
            })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["mappings"]) == 2
        assert all(m["confidence"] == 1.0 for m in data["mappings"])

    @pytest.mark.anyio
    async def test_invalid_json_body(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/ai/suggest-mapping",
                content="bad",
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_empty_source_columns_rejected(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/suggest-mapping", json={
                "source_columns": [],
                "target_columns": ["name"],
            })
        assert resp.status_code == 400
        assert "source_columns" in resp.json()["error"]

    @pytest.mark.anyio
    async def test_empty_target_columns_rejected(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/suggest-mapping", json={
                "source_columns": ["name"],
                "target_columns": [],
            })
        assert resp.status_code == 400
        assert "target_columns" in resp.json()["error"]


# ============================================================================
# POST /api/ai/optimize-suggestions endpoint
# ============================================================================


class TestOptimizeSuggestionsEndpoint:
    """测试 POST /api/ai/optimize-suggestions 端点。"""

    @pytest.mark.anyio
    async def test_pipeline_without_checkpoints_gets_high_priority_suggestion(self):
        """缺少 checkpoints 应得到 high 优先级建议。"""
        state = {
            "scene": {"name": "test"},
            "inputs": [{"plugin": "csv"}],
            "processors": [{"plugin": "filter"}],
            "output": {"plugin": "excel"},
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/optimize-suggestions", json={"state": state})
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "rules"
        suggestions = data["suggestions"]
        # 应该有 checkpoints 建议和 dedup 建议
        assert any(s["priority"] == "high" and "检查点" in s["suggestion"] for s in suggestions)

    @pytest.mark.anyio
    async def test_pipeline_without_dedup_gets_medium_priority(self):
        """缺少 dedup 应得到 medium 优先级建议。"""
        state = {
            "scene": {"name": "test"},
            "inputs": [{"plugin": "csv"}],
            "processors": [{"plugin": "check"}],
            "output": {"plugin": "excel"},
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/optimize-suggestions", json={"state": state})
        data = resp.json()
        suggestions = data["suggestions"]
        assert any(s["priority"] == "medium" and "去重" in s["suggestion"] for s in suggestions)

    @pytest.mark.anyio
    async def test_pipeline_with_no_processors_gets_suggestion(self):
        """没有任何 processor 应得到 medium 优先级建议。"""
        state = {
            "scene": {"name": "test"},
            "inputs": [{"plugin": "csv"}],
            "processors": [],
            "output": {"plugin": "excel"},
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/optimize-suggestions", json={"state": state})
        data = resp.json()
        suggestions = data["suggestions"]
        assert any("处理步骤" in s["suggestion"] for s in suggestions)

    @pytest.mark.anyio
    async def test_pipeline_with_too_many_processors_gets_low_priority(self):
        """处理步骤过多（>5）应得到 low 优先级性能建议。"""
        state = {
            "scene": {"name": "test"},
            "inputs": [{"plugin": "csv"}],
            "processors": [{"plugin": f"p{i}"} for i in range(6)],
            "output": {"plugin": "excel"},
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/optimize-suggestions", json={"state": state})
        data = resp.json()
        suggestions = data["suggestions"]
        assert any(
            s["priority"] == "low" and "性能" in s["category"]
            for s in suggestions
        )

    @pytest.mark.anyio
    async def test_complete_pipeline_returns_overall_comment(self):
        """结构合理的 Pipeline 应返回总体评价建议。"""
        state = {
            "scene": {"name": "test"},
            "inputs": [{"plugin": "csv"}],
            "processors": [
                {"plugin": "check"},
                {"plugin": "dedup"},
                {"plugin": "filter"},
            ],
            "output": {"plugin": "excel"},
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/optimize-suggestions", json={"state": state})
        data = resp.json()
        suggestions = data["suggestions"]
        # 应有"总体评价"建议
        assert any(s["category"] == "总体评价" for s in suggestions)

    @pytest.mark.anyio
    async def test_invalid_json_body(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/ai/optimize-suggestions",
                content="bad",
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_state_not_object_rejected(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/ai/optimize-suggestions", json={
                "state": "not an object",
            })
        assert resp.status_code == 400
        assert "state" in resp.json()["error"]


# ============================================================================
# Rate limiting
# ============================================================================


class TestRateLimiting:
    """测试新端点的限流逻辑。"""

    @pytest.mark.anyio
    async def test_suggest_checkpoint_rate_limited(self):
        """连续发送超过 20 次请求应触发限流。"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 20 次应允许（fixture 中 max_requests=20）
            for _ in range(20):
                resp = await client.post("/api/ai/suggest-checkpoint", json={
                    "columns": [{"name": "id", "type": "int"}],
                })
                assert resp.status_code == 200
            # 第 21 次应被限流
            resp = await client.post("/api/ai/suggest-checkpoint", json={
                "columns": [{"name": "id", "type": "int"}],
            })
        assert resp.status_code == 429
