"""端到端全流程测试 — 从用户角度验证重构后的完整功能链路。

覆盖场景：
1. 配置生命周期（CRUD + 版本管理 + 回滚 + diff）
2. 导入/导出往返（YAML / JSON）
3. 配置执行（CSV 输出，真实 pipeline 执行）
4. SSE 流式执行（execute_with_progress 事件序列 — Bug 1 修复关键路径）
5. SSE 检查点失败错误事件
6. AI 规则引擎兜底（AI 未启用时 fallback 到 rules/）

数据隔离：autouse fixture patch 所有相关模块的目录常量到 tmp_path，
确保测试不污染真实数据目录。
"""

from __future__ import annotations

import io
import json

import pytest
from httpx import ASGITransport, AsyncClient

from configforge.api import configs as configs_mod
from configforge.api import executions as exec_api_mod
from configforge.api import files as files_api_mod
from configforge.core import pipeline as pipeline_mod
from configforge.models.wizard import (
    ColumnMappingItem,
    CsvInputConfig,
    CsvOutputConfig,
    InputSource,
    OutputTarget,
    ProcessorConfig,
    SaveConfigRequest,
    SceneInfo,
    WizardState,
)
from configforge.server import app
from configforge.services import config_store as config_store_mod
from configforge.services import execution_store as exec_store_mod
from configforge.services.ai import settings as ai_settings_mod
from configforge.services.notifier import store as notifier_store_mod
from pipeforge.config.models import RowCountRule

# ---------------------------------------------------------------------------
# Data isolation autouse fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_dirs(tmp_path, monkeypatch):
    """隔离所有数据目录到 tmp_path，避免污染真实文件系统。"""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    exec_dir = tmp_path / "executions"
    exec_dir.mkdir()
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    index_path = configs_dir / "index.json"

    # config_store + api.configs (re-export)
    monkeypatch.setattr(config_store_mod, "CONFIGS_DIR", str(configs_dir))
    monkeypatch.setattr(config_store_mod, "INDEX_PATH", str(index_path))
    config_store_mod._cache.invalidate("index")
    monkeypatch.setattr(configs_mod, "CONFIGS_DIR", str(configs_dir))
    monkeypatch.setattr(configs_mod, "INDEX_PATH", str(index_path))

    # execution_store + api.executions
    for mod in (exec_store_mod, exec_api_mod):
        monkeypatch.setattr(mod, "DATA_DIR", str(tmp_path))
        monkeypatch.setattr(mod, "EXEC_DIR", str(exec_dir))
        monkeypatch.setattr(mod, "EXEC_INDEX", str(exec_dir / "index.json"))

    # notifier history
    monkeypatch.setattr(
        notifier_store_mod, "NOTIFICATIONS_PATH", tmp_path / "notifications.json"
    )
    monkeypatch.setattr(
        notifier_store_mod, "HISTORY_PATH", tmp_path / "notification_history.json"
    )

    # pipeline upload/output dirs
    monkeypatch.setattr(pipeline_mod, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(files_api_mod, "UPLOAD_DIR", str(upload_dir))

    # Disable AI to ensure rule-based fallback path is exercised
    from configforge.models.ai import AiSettings

    def _disabled_ai_settings() -> AiSettings:
        return AiSettings()  # enabled=False by default

    monkeypatch.setattr(ai_settings_mod, "load_settings", _disabled_ai_settings)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


CSV_BYTES = b"name,age\nAlice,30\nBob,25\nCharlie,35\n"


async def _upload_csv(client: AsyncClient, content: bytes = CSV_BYTES) -> str:
    """上传 CSV 文件，返回 file_id。"""
    resp = await client.post(
        "/api/files/upload",
        files={"file": ("input.csv", io.BytesIO(content), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["file_id"]


def _make_executable_state(file_id: str) -> WizardState:
    """构造可执行的 WizardState：CSV input + SQL processor + CSV output。"""
    return WizardState(
        scene=SceneInfo(name="E2E测试", description="端到端全流程", version="1.0"),
        inputs=[
            InputSource(
                name="csv输入",
                plugin="csv",
                table="csv_t",
                param_key="csv_file",
                file_id=file_id,
                config=CsvInputConfig(),
            )
        ],
        processors=[
            ProcessorConfig(
                name="过滤成年人",
                plugin="sql",
                sql="CREATE TABLE result AS SELECT name, age FROM csv_t WHERE age >= 25",
                output_tables=["result"],
            )
        ],
        output=OutputTarget(
            plugin="csv",
            config=CsvOutputConfig(
                source_table="result",
                filename="output.csv",
                columns=[
                    ColumnMappingItem(source="name", target="姓名"),
                    ColumnMappingItem(source="age", target="年龄"),
                ],
            ),
        ),
    )


async def _save_config(client: AsyncClient, state: WizardState, config_id: str | None = None) -> str:
    """保存配置，返回 config_id。"""
    resp = await client.post(
        "/api/configs",
        json=SaveConfigRequest(state=state, config_id=config_id).model_dump(by_alias=True),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# 1. 配置生命周期
# ---------------------------------------------------------------------------


class TestConfigLifecycle:
    """配置 CRUD + 版本管理 + 回滚 + diff 全流程。"""

    @pytest.mark.anyio
    async def test_full_lifecycle(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. 空列表
            resp = await client.get("/api/configs")
            assert resp.status_code == 200
            assert resp.json()["total"] == 0

            # 2. 创建配置
            state = WizardState(scene=SceneInfo(name="生命周期测试", version="1.0"))
            cid = await _save_config(client, state)
            assert cid

            # 3. 列表含新配置
            resp = await client.get("/api/configs")
            assert resp.json()["total"] == 1
            assert resp.json()["configs"][0]["id"] == cid

            # 4. 详情
            resp = await client.get(f"/api/configs/{cid}")
            assert resp.status_code == 200
            assert resp.json()["scene"]["name"] == "生命周期测试"

            # 5. 更新配置（产生 v2）
            state2 = WizardState(scene=SceneInfo(name="更新后名称", version="1.1"))
            await _save_config(client, state2, config_id=cid)

            # 6. 版本列表
            resp = await client.get(f"/api/configs/{cid}/versions")
            assert resp.status_code == 200
            versions = resp.json()
            # v1 已归档 + v2 当前 = 2 个版本
            assert len(versions) == 2
            version_numbers = [v["version"] for v in versions]
            assert 1 in version_numbers  # v1 归档
            assert 2 in version_numbers  # v2 当前

            # 7. 版本对比
            # 当前是 v2，对比 v1 vs v2
            resp = await client.get(f"/api/configs/{cid}/versions/diff?v1=1&v2=2")
            assert resp.status_code == 200
            diff = resp.json()
            # scene.name 从 "生命周期测试" 改为 "更新后名称"
            modified_paths = [m["path"] for m in diff["modified"]]
            assert any("scene.name" in p for p in modified_paths)

            # 8. 回滚到 v1
            resp = await client.post(f"/api/configs/{cid}/versions/1/rollback")
            assert resp.status_code == 200
            rollback = resp.json()
            assert rollback["rolled_back_to"] == 1
            assert rollback["new_version"] == 3  # 回滚产生新版本 v3

            # 9. 验证回滚后 scene.name 恢复
            resp = await client.get(f"/api/configs/{cid}")
            assert resp.json()["scene"]["name"] == "生命周期测试"

            # 10. 删除
            resp = await client.delete(f"/api/configs/{cid}")
            assert resp.status_code == 200
            resp = await client.get(f"/api/configs/{cid}")
            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 2. 导入/导出往返
# ---------------------------------------------------------------------------


class TestImportExport:
    """导出 YAML/JSON → 导入 → 验证往返一致性。"""

    @pytest.mark.anyio
    async def test_yaml_roundtrip(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            state = WizardState(
                scene=SceneInfo(name="导出测试", description="yaml roundtrip"),
            )
            cid = await _save_config(client, state)

            # 导出 YAML
            resp = await client.get(f"/api/configs/{cid}/export?format=yaml")
            assert resp.status_code == 200
            yaml_content = resp.content

            # 导入 YAML
            resp = await client.post(
                "/api/configs/import",
                files={"file": ("exported.yaml", io.BytesIO(yaml_content), "application/x-yaml")},
            )
            assert resp.status_code == 200
            imported = resp.json()
            assert imported["scene_name"] == "导出测试"
            new_cid = imported["id"]
            assert new_cid != cid  # 新 ID

            # 验证导入的配置
            resp = await client.get(f"/api/configs/{new_cid}")
            assert resp.json()["scene"]["description"] == "yaml roundtrip"

    @pytest.mark.anyio
    async def test_json_roundtrip(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            state = WizardState(scene=SceneInfo(name="JSON导出"))
            cid = await _save_config(client, state)

            resp = await client.get(f"/api/configs/{cid}/export?format=json")
            assert resp.status_code == 200
            json_content = resp.content

            resp = await client.post(
                "/api/configs/import",
                files={"file": ("exported.json", io.BytesIO(json_content), "application/json")},
            )
            assert resp.status_code == 200
            assert resp.json()["scene_name"] == "JSON导出"


# ---------------------------------------------------------------------------
# 3. 配置执行（真实 pipeline）
# ---------------------------------------------------------------------------


class TestExecuteConfig:
    """通过 /api/configs/{id}/execute 执行已保存配置。"""

    @pytest.mark.anyio
    async def test_execute_csv_output(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            file_id = await _upload_csv(client)
            state = _make_executable_state(file_id)
            cid = await _save_config(client, state)

            # 执行（param_key=csv_file → file_id）
            resp = await client.post(
                f"/api/configs/{cid}/execute",
                json={"files": {"csv_file": file_id}},
            )
            assert resp.status_code == 200, resp.text
            # CSV 输出应返回文件
            assert "attachment" in resp.headers.get("content-disposition", "")
            assert b"Alice" in resp.content  # age=30 >= 25


# ---------------------------------------------------------------------------
# 4. SSE 流式执行（Bug 1 修复关键路径）
# ---------------------------------------------------------------------------


def _parse_sse_events(text: str) -> list[dict]:
    """解析 SSE 文本流为 [{event, data}, ...]。"""
    events = []
    current_event = ""
    current_data = ""
    for line in text.split("\n"):
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            current_data = line[5:].strip()
        elif line.strip() == "" and (current_event or current_data):
            events.append({"event": current_event, "data": current_data})
            current_event = ""
            current_data = ""
    return events


class TestSSEExecuteStream:
    """SSE 流式执行 — 验证 execute_with_progress 事件序列。

    这是 Bug 1 修复的关键路径：execution_service.py:472 调用
    engine.execute_processor()，修复前会 AttributeError。
    """

    @pytest.mark.anyio
    async def test_sse_full_event_sequence(self):
        """验证 SSE 事件序列包含 processor_start/processor_done（Bug 1 回归点）。"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            file_id = await _upload_csv(client)
            state = _make_executable_state(file_id)

            # POST /api/wizard/execute/stream
            async with client.stream(
                "POST",
                "/api/wizard/execute/stream",
                json={"state": state.model_dump(by_alias=True)},
            ) as response:
                assert response.status_code == 200
                text = ""
                async for chunk in response.aiter_text():
                    text += chunk

            events = _parse_sse_events(text)
            event_types = [e["event"] for e in events]

            # 必须包含完整事件序列
            assert "start" in event_types, f"missing start event: {event_types}"
            assert "input_start" in event_types
            assert "input_done" in event_types
            # Bug 1 核心验证：processor 阶段不崩溃
            assert "processor_start" in event_types, (
                f"processor_start missing — Bug 1 regression? events: {event_types}"
            )
            assert "processor_done" in event_types, (
                f"processor_done missing — Bug 1 regression? events: {event_types}"
            )
            assert "output_start" in event_types
            assert "output_done" in event_types
            assert "complete" in event_types

            # 验证 complete 事件数据
            complete_event = next(e for e in events if e["event"] == "complete")
            data = json.loads(complete_event["data"])
            assert data.get("status") == "success" or "output_file" in data

    @pytest.mark.anyio
    async def test_sse_checkpoint_failure_emits_error(self):
        """检查点未通过时 SSE 应发射 error 事件。"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            file_id = await _upload_csv(client)

            state = _make_executable_state(file_id)
            # 添加一个必定失败的检查点（要求 1000 行，实际只有 3 行）
            # CheckRule 是 Annotated union 类型别名，须用具体子类 RowCountRule 构造
            state.processors[0].checkpoints = [
                RowCountRule(table="result", min=1000, on_failure="block"),
            ]

            async with client.stream(
                "POST",
                "/api/wizard/execute/stream",
                json={"state": state.model_dump(by_alias=True)},
            ) as response:
                assert response.status_code == 200
                text = ""
                async for chunk in response.aiter_text():
                    text += chunk

            events = _parse_sse_events(text)
            event_types = [e["event"] for e in events]
            assert "error" in event_types, f"missing error event: {event_types}"

            error_event = next(e for e in events if e["event"] == "error")
            data = json.loads(error_event["data"])
            assert "checks" in data
            assert any(not c["passed"] for c in data["checks"])


# ---------------------------------------------------------------------------
# 5. AI 规则引擎兜底（AI 未启用时 fallback）
# ---------------------------------------------------------------------------


class TestAIRulesFallback:
    """AI 未启用时，规则引擎应正常返回建议。"""

    @pytest.mark.anyio
    async def test_suggest_checkpoint_rules(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/ai/suggest-checkpoint",
                json={
                    "columns": [
                        {"name": "email", "type": "varchar", "sample_values": ["a@b.com"]},
                        {"name": "age", "type": "int", "sample_values": [25]},
                    ],
                    "table_name": "users",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["source"] == "rules"
            assert len(data["suggestions"]) > 0

    @pytest.mark.anyio
    async def test_suggest_mapping_rules(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/ai/suggest-mapping",
                json={
                    "source_columns": ["user_name", "email_addr"],
                    "target_columns": ["username", "email"],
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["source"] == "rules"
            # /suggest-mapping 返回 mappings（而非 suggestions）
            assert len(data["mappings"]) > 0

    @pytest.mark.anyio
    async def test_optimize_suggestions_rules(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/ai/optimize-suggestions",
                json={
                    "state": {
                        "processors": [],
                        "inputs": [{"name": "in1"}],
                    }
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["source"] == "rules"
            # 无 processor → 应建议添加检查点
            suggestions = data["suggestions"]
            assert any("检查点" in s.get("suggestion", "") for s in suggestions)
