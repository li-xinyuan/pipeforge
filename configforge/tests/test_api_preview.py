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
    fid = uuid.uuid4().hex + ".xlsx"
    os.makedirs("tmp/uploads", exist_ok=True)
    with open(f"tmp/uploads/{fid}", "wb") as f:
        f.write(b.read())
    return fid


@pytest.mark.anyio
async def test_preview_file_returns_columns():
    fid = await upload_test_xlsx()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/preview/file", json={"file_id": fid})
    assert resp.status_code == 200
    data = resp.json()
    assert "姓名" in data["columns"]


@pytest.mark.anyio
async def test_preview_nonexistent_file():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/preview/file", json={"file_id": "nonexistent"})
    assert resp.status_code == 404
