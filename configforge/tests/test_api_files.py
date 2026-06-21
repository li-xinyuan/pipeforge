import io

import pytest
from httpx import ASGITransport, AsyncClient

from configforge.server import app


async def make_xlsx_content():
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["A"])
    b = io.BytesIO()
    wb.save(b)
    b.seek(0)
    return b.read()


@pytest.mark.asyncio
async def test_upload_valid_xlsx_returns_file_id():
    content = await make_xlsx_content()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/files/upload",
            files={
                "file": (
                    "test.xlsx",
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "file_id" in data
    assert data["original_name"] == "test.xlsx"


@pytest.mark.asyncio
async def test_upload_unsupported_format():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/files/upload",
            files={"file": ("test.pdf", b"test", "application/pdf")},
        )
    assert resp.status_code == 422
    assert resp.json()["code"] == "FILE_FORMAT_UNSUPPORTED"


@pytest.mark.asyncio
async def test_upload_no_file():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/files/upload")
    assert resp.status_code == 422
