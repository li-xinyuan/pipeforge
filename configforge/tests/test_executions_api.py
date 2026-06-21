import json
import os

import pytest
from httpx import ASGITransport, AsyncClient

from configforge.api import executions as exec_module
from configforge.server import app


def _make_exec_record(
    exec_id="abc12345",
    config_id="cfg001",
    scene_name="Test Scene",
    status="success",
    output_file_name=None,
):
    """Create a minimal execution record dict."""
    return {
        "id": exec_id,
        "config_id": config_id,
        "config_version": 1,
        "scene_name": scene_name,
        "status": status,
        "started_at": "2025-01-01T00:00:00+00:00",
        "finished_at": "2025-01-01T00:00:01+00:00",
        "duration_ms": 1000,
        "inputs_summary": [],
        "processors_summary": [],
        "output_type": "csv",
        "checks_summary": [],
        "error_message": None,
        "output_file_name": output_file_name,
        "diagnosis": None,
    }


def _create_exec_dir(exec_dir, exec_id, record=None, output_content=None, output_filename=None):
    """Helper: create an execution directory with result.json and optional output file."""
    if record is None:
        record = _make_exec_record(exec_id=exec_id)
    exec_path = os.path.join(exec_dir, exec_id)
    os.makedirs(exec_path, exist_ok=True)
    with open(os.path.join(exec_path, "result.json"), "w") as f:
        json.dump(record, f)
    if output_content is not None and output_filename is not None:
        with open(os.path.join(exec_path, output_filename), "w") as f:
            f.write(output_content)
    return record


def _write_index(index_path, records):
    """Helper: write the index.json file."""
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w") as f:
        json.dump(records, f)


@pytest.fixture(autouse=True)
def _redirect_dirs(tmp_path, monkeypatch):
    """Redirect DATA_DIR, EXEC_DIR, EXEC_INDEX to tmp_path."""
    data_dir = str(tmp_path / "data")
    exec_dir = os.path.join(data_dir, "executions")
    exec_index = os.path.join(exec_dir, "index.json")
    monkeypatch.setattr(exec_module, "DATA_DIR", data_dir)
    monkeypatch.setattr(exec_module, "EXEC_DIR", exec_dir)
    monkeypatch.setattr(exec_module, "EXEC_INDEX", exec_index)
    return {"data_dir": data_dir, "exec_dir": exec_dir, "exec_index": exec_index}


# ── TestListExecutions ──


class TestListExecutions:
    @pytest.mark.anyio
    async def test_empty_list(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/executions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["total_pages"] == 0

    @pytest.mark.anyio
    async def test_with_records(self, _redirect_dirs):
        exec_dir = _redirect_dirs["exec_dir"]
        exec_index = _redirect_dirs["exec_index"]
        r1 = _make_exec_record(exec_id="exec001", scene_name="Scene A")
        r2 = _make_exec_record(exec_id="exec002", scene_name="Scene B")
        _create_exec_dir(exec_dir, "exec001", r1)
        _create_exec_dir(exec_dir, "exec002", r2)
        _write_index(exec_index, [r1, r2])

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/executions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.anyio
    async def test_search_filter(self, _redirect_dirs):
        _exec_dir = _redirect_dirs["exec_dir"]
        exec_index = _redirect_dirs["exec_index"]
        r1 = _make_exec_record(exec_id="exec001", scene_name="Alpha Scene")
        r2 = _make_exec_record(exec_id="exec002", scene_name="Beta Scene")
        _write_index(exec_index, [r1, r2])

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/executions", params={"search": "alpha"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["scene_name"] == "Alpha Scene"

    @pytest.mark.anyio
    async def test_config_id_filter(self, _redirect_dirs):
        _exec_dir = _redirect_dirs["exec_dir"]
        exec_index = _redirect_dirs["exec_index"]
        r1 = _make_exec_record(exec_id="exec001", config_id="cfg_a")
        r2 = _make_exec_record(exec_id="exec002", config_id="cfg_b")
        _write_index(exec_index, [r1, r2])

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/executions", params={"config_id": "cfg_a"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["config_id"] == "cfg_a"

    @pytest.mark.anyio
    async def test_pagination(self, _redirect_dirs):
        exec_index = _redirect_dirs["exec_index"]
        records = [
            _make_exec_record(exec_id=f"exec{i:03d}", scene_name=f"Scene {i}")
            for i in range(5)
        ]
        _write_index(exec_index, records)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/executions", params={"page": 1, "page_size": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3
        assert len(data["items"]) == 2


# ── TestGetExecution ──


class TestGetExecution:
    @pytest.mark.anyio
    async def test_success(self, _redirect_dirs):
        exec_dir = _redirect_dirs["exec_dir"]
        record = _make_exec_record(exec_id="exec001")
        _create_exec_dir(exec_dir, "exec001", record)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/executions/exec001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "exec001"
        assert data["scene_name"] == "Test Scene"

    @pytest.mark.anyio
    async def test_not_found(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/executions/nonexistent")
        assert resp.status_code == 404


# ── TestDeleteExecution ──


class TestDeleteExecution:
    @pytest.mark.anyio
    async def test_success(self, _redirect_dirs):
        exec_dir = _redirect_dirs["exec_dir"]
        exec_index = _redirect_dirs["exec_index"]
        record = _make_exec_record(exec_id="exec001")
        _create_exec_dir(exec_dir, "exec001", record)
        _write_index(exec_index, [record])

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete("/api/executions/exec001")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        # Directory should be removed
        assert not os.path.exists(os.path.join(exec_dir, "exec001"))

    @pytest.mark.anyio
    async def test_not_found(self, _redirect_dirs):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete("/api/executions/nonexistent")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    @pytest.mark.anyio
    async def test_removes_from_index(self, _redirect_dirs):
        exec_dir = _redirect_dirs["exec_dir"]
        exec_index = _redirect_dirs["exec_index"]
        r1 = _make_exec_record(exec_id="exec001")
        r2 = _make_exec_record(exec_id="exec002")
        _create_exec_dir(exec_dir, "exec001", r1)
        _create_exec_dir(exec_dir, "exec002", r2)
        _write_index(exec_index, [r1, r2])

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.delete("/api/executions/exec001")

        with open(exec_index) as f:
            index = json.load(f)
        assert len(index) == 1
        assert index[0]["id"] == "exec002"


# ── TestDownloadExecution ──


class TestDownloadExecution:
    @pytest.mark.anyio
    async def test_no_output_file(self, _redirect_dirs):
        exec_dir = _redirect_dirs["exec_dir"]
        record = _make_exec_record(exec_id="exec001", output_file_name=None)
        _create_exec_dir(exec_dir, "exec001", record)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/executions/exec001/download")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_download_csv(self, _redirect_dirs):
        exec_dir = _redirect_dirs["exec_dir"]
        record = _make_exec_record(exec_id="exec001", output_file_name="output.csv")
        _create_exec_dir(
            exec_dir, "exec001", record,
            output_content="a,b\n1,2", output_filename="output.csv",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/executions/exec001/download")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        assert "a,b" in resp.text

    @pytest.mark.anyio
    async def test_download_xlsx(self, _redirect_dirs):
        exec_dir = _redirect_dirs["exec_dir"]
        record = _make_exec_record(exec_id="exec001", output_file_name="output.xlsx")
        _create_exec_dir(
            exec_dir, "exec001", record,
            output_content="fake-xlsx-bytes", output_filename="output.xlsx",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/executions/exec001/download")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")


# ── TestSanitizeSummary ──


class TestSanitizeSummary:
    def test_masks_connection_strings(self):
        summary = [{"conn": "mysql://user:secretpass@host/db"}]
        result = exec_module._sanitize_summary(summary)
        assert result[0]["conn"] == "mysql://user:***@host/db"

    def test_leaves_non_connection_values_unchanged(self):
        summary = [{"name": "my_scene", "count": 42}]
        result = exec_module._sanitize_summary(summary)
        assert result[0]["name"] == "my_scene"
        # Non-matching values retain their original type
        assert result[0]["count"] == 42

    def test_multiple_connection_strings(self):
        summary = [
            {"src": "mysql://admin:pwd123@db1/mydb", "dst": "postgresql://root:abc@db2/other"},
        ]
        result = exec_module._sanitize_summary(summary)
        assert result[0]["src"] == "mysql://admin:***@db1/mydb"
        assert result[0]["dst"] == "postgresql://root:***@db2/other"


# ── TestSaveFailedExecution ──


class TestSaveFailedExecution:
    def test_creates_result_json_and_updates_index(self, _redirect_dirs):
        exec_dir = _redirect_dirs["exec_dir"]
        exec_index = _redirect_dirs["exec_index"]

        exec_module._save_failed_execution(
            exec_id="fail001",
            started_at="2025-06-01T10:00:00+00:00",
            config_id="cfg001",
            config_version=1,
            scene_name="Fail Scene",
            inputs_summary=[{"conn": "mysql://user:pass@host/db"}],
            processors_summary=[{"name": "proc1"}],
            output_type="csv",
            error_message="Something went wrong",
        )

        # result.json should exist
        result_path = os.path.join(exec_dir, "fail001", "result.json")
        assert os.path.exists(result_path)
        with open(result_path) as f:
            record = json.load(f)
        assert record["id"] == "fail001"
        assert record["status"] == "failed"
        assert record["error_message"] == "Something went wrong"
        # Connection string should be sanitized
        assert record["inputs_summary"][0]["conn"] == "mysql://user:***@host/db"
        assert record["duration_ms"] > 0

        # index.json should be updated
        assert os.path.exists(exec_index)
        with open(exec_index) as f:
            index = json.load(f)
        assert len(index) == 1
        assert index[0]["id"] == "fail001"
        assert index[0]["status"] == "failed"
