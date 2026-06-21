import io
import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from configforge.server import app


async def upload_test_xlsx():
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["姓名", "部门"])
    ws.append(["张三", "研发"])
    b = io.BytesIO()
    wb.save(b)
    b.seek(0)
    fid = uuid.uuid4().hex
    os.makedirs("tmp/uploads", exist_ok=True)
    with open(f"tmp/uploads/{fid}", "wb") as f:
        f.write(b.read())
    return fid


@pytest.mark.anyio
async def test_init_scene():
    fid = await upload_test_xlsx()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/wizard/init-scene", json={"file_ids": [fid]}
        )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_infer_input():
    fid = await upload_test_xlsx()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/wizard/infer-input/test_input",
            json={"file_id": fid, "type": "excel"},
        )
    assert resp.status_code == 200
    assert "columns" in resp.json()


@pytest.mark.anyio
async def test_infer_output():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/wizard/infer-output", json={"inputs": []}
        )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_generate():
    state = {
        "scene": {"name": "测试", "description": "", "version": "1.0"},
        "inputs": [],
        "processors": [{
            "plugin": "sql",
            "sql": "SELECT 1",
            "output_tables": ["t1"],
        }],
        "output": None,
        "current_step": 4,
        "uploaded_files": {},
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/wizard/generate", json={"state": state})
    assert resp.status_code == 200
    assert "yaml" in resp.json()


@pytest.mark.anyio
async def test_infer_input_csv():
    """infer_input should work with type=csv on a CSV file."""
    fid = uuid.uuid4().hex
    os.makedirs("tmp/uploads", exist_ok=True)
    with open(f"tmp/uploads/{fid}", "w") as f:
        f.write("name,age\nAlice,30")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/wizard/infer-input/test_csv",
            json={"file_id": fid, "type": "csv"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "columns" in data
    assert len(data["columns"]) == 2
    assert data["columns"][0]["name"] == "name"
