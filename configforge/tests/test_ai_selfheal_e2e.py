"""E2E tests for AI self-healing: auto_diagnose integration with execution flow."""
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from configforge.server import app


@pytest.fixture(autouse=True)
def _isolate_data():
    """Use a temp directory for execution data."""
    import configforge.api.executions as exec_mod
    orig = exec_mod.DATA_DIR
    tmp = tempfile.mkdtemp()
    exec_mod.DATA_DIR = tmp
    exec_mod.EXEC_DIR = os.path.join(tmp, "executions")
    exec_mod.EXEC_INDEX = os.path.join(exec_mod.EXEC_DIR, "index.json")
    yield
    exec_mod.DATA_DIR = orig
    exec_mod.EXEC_DIR = os.path.join(orig, "executions")
    exec_mod.EXEC_INDEX = os.path.join(orig, "executions", "index.json")


@pytest.fixture(autouse=True)
def _isolate_ai_settings():
    """Isolate AI settings to prevent test interference."""
    import configforge.services.ai.settings as mod
    orig = mod.SETTINGS_FILE
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(tmp)
    mod.SETTINGS_FILE = tmp
    yield
    mod.SETTINGS_FILE = orig
    if os.path.exists(tmp):
        os.unlink(tmp)


@pytest.mark.anyio
async def test_execution_list_includes_diagnosis():
    """Execution history list should include diagnosis field for failed executions."""
    from configforge.api.executions import _save_failed_execution

    diagnosis = {
        "cause": "表名不存在",
        "suggestions": ["检查表名拼写", "确认表已创建"],
        "severity": "error",
        "step": 3,
    }
    _save_failed_execution(
        exec_id="test-diag-001",
        started_at="2025-01-01T00:00:00+00:00",
        config_id="cfg-001",
        config_version=1,
        scene_name="测试诊断",
        inputs_summary=[{"name": "input1", "plugin": "csv"}],
        processors_summary=[{"plugin": "sql", "name": "proc1"}],
        output_type="csv",
        error_message="no such table: users",
        diagnosis=diagnosis,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/executions")
    assert resp.status_code == 200
    items = resp.json()["items"]
    found = next((e for e in items if e["id"] == "test-diag-001"), None)
    assert found is not None
    assert found["diagnosis"] is not None
    assert found["diagnosis"]["cause"] == "表名不存在"
    assert found["diagnosis"]["severity"] == "error"


@pytest.mark.anyio
async def test_execution_detail_includes_diagnosis():
    """Execution detail endpoint should include diagnosis."""
    from configforge.api.executions import _save_failed_execution

    diagnosis = {
        "cause": "SQL语法错误",
        "suggestions": ["检查SQL括号是否匹配"],
        "severity": "warning",
        "step": 3,
    }
    _save_failed_execution(
        exec_id="test-diag-002",
        started_at="2025-01-01T00:00:00+00:00",
        config_id="cfg-002",
        config_version=1,
        scene_name="SQL测试",
        inputs_summary=[],
        processors_summary=[],
        output_type="csv",
        error_message="syntax error near SELECT",
        diagnosis=diagnosis,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/executions/test-diag-002")
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagnosis"] is not None
    assert data["diagnosis"]["cause"] == "SQL语法错误"
    assert data["diagnosis"]["step"] == 3


@pytest.mark.anyio
async def test_execution_without_diagnosis():
    """Execution without diagnosis should have null/missing diagnosis field."""
    from configforge.api.executions import _save_failed_execution

    _save_failed_execution(
        exec_id="test-no-diag",
        started_at="2025-01-01T00:00:00+00:00",
        config_id="cfg-003",
        config_version=1,
        scene_name="无诊断",
        inputs_summary=[],
        processors_summary=[],
        output_type="csv",
        error_message="some error",
        diagnosis=None,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/executions/test-no-diag")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("diagnosis") is None


@pytest.mark.anyio
async def test_ai_suggest_diagnose_category():
    """AI suggest endpoint should accept diagnose category."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/ai/suggest", json={
            "category": "diagnose",
            "context": {"yaml": "test", "errorLog": "no such table"},
        })
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_ai_suggest_autofix_category():
    """AI suggest endpoint should accept autofix category."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/ai/suggest", json={
            "category": "autofix",
            "context": {"diagnosis": '{"cause": "test"}', "errorLog": "error"},
        })
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_ai_suggest_anomaly_category():
    """AI suggest endpoint should accept anomaly category."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/ai/suggest", json={
            "category": "anomaly",
            "context": {"sample_rows": "[]", "stats": "{}", "columns": ["id"]},
        })
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_auto_diagnose_integration_with_mock():
    """Test auto_diagnose is called and result saved when execution fails."""
    _mock_diagnosis = {
        "cause": "列名不存在",
        "suggestions": ["检查列名拼写"],
        "severity": "error",
        "step": 3,
    }

    with patch("configforge.services.ai.auto_diagnose.load_settings") as mock_load, \
         patch("configforge.services.ai.auto_diagnose.create_backend") as mock_create:
        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_load.return_value = mock_settings

        mock_backend = AsyncMock()
        mock_backend.generate.return_value = '{"cause": "列名不存在", "suggestions": ["检查列名拼写"], "severity": "error"}'
        mock_backend.close = AsyncMock()
        mock_create.return_value = mock_backend

        from configforge.services.ai.auto_diagnose import auto_diagnose
        result = await auto_diagnose(
            yaml_text="inputs:\n  - name: test",
            error_message="no such column: usr_name",
            scene_name="用户统计",
        )

    assert result is not None
    assert result["cause"] == "列名不存在"
    assert result["step"] == 3  # SQL error -> step 3


@pytest.mark.anyio
async def test_auto_diagnose_disabled_returns_none():
    """When AI is disabled, auto_diagnose should return None without calling backend."""
    with patch("configforge.services.ai.auto_diagnose.load_settings") as mock_load:
        mock_settings = MagicMock()
        mock_settings.enabled = False
        mock_load.return_value = mock_settings

        from configforge.services.ai.auto_diagnose import auto_diagnose
        result = await auto_diagnose("yaml", "error msg")

    assert result is None
