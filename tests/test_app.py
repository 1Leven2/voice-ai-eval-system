import io
import wave

import httpx
import pytest

from app.main import create_app
from app.sample_data import generate_samples


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_endpoint_reports_ready(tmp_path):
    transport = httpx.ASGITransport(app=create_app(tmp_path / "eval.db"))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_import_evaluate_and_export_flow(tmp_path):
    transport = httpx.ASGITransport(app=create_app(tmp_path / "eval.db"))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "samples": [
                {
                    "sample_id": "demo-1",
                    "scenario_type": "interaction",
                    "task_types": ["asr", "nlu"],
                    "reference": {"text": "打开空调", "intent": "turn_on_ac", "slots": {}},
                    "system_output": {"text": "打开空调"},
                    "input_data": {"text": "打开空调"},
                }
            ]
        }
        imported = await client.post("/api/import", json=payload)
        assert imported.status_code == 200
        assert imported.json()["accepted"] == 1

        evaluated = await client.post("/api/evaluate")
        assert evaluated.status_code == 200
        assert evaluated.json()["evaluated"] == 1

        revised = await client.patch(
            "/api/samples/demo-1/revision",
            json={"diagnosis": "人工确认通过", "final_conclusion": "通过", "editor": "reviewer"},
        )
        assert revised.status_code == 200
        assert revised.json()["human_revision"]["editor"] == "reviewer"

        exported = await client.get("/api/export/json")
        assert exported.status_code == 200
        assert exported.json()[0]["sample_id"] == "demo-1"


@pytest.mark.anyio
async def test_one_hundred_sample_acceptance_flow(tmp_path):
    transport = httpx.ASGITransport(app=create_app(tmp_path / "eval.db"))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        imported = await client.post("/api/import", json={"samples": generate_samples()})
        assert imported.json()["accepted"] == 100
        evaluated = await client.post("/api/evaluate")
        assert evaluated.json() == {"evaluated": 100, "failed": 0}
        exported = await client.get("/api/export/html")
        assert exported.status_code == 200
        assert "sample-100" in exported.text


@pytest.mark.anyio
async def test_multipart_csv_import_is_supported(tmp_path):
    transport = httpx.ASGITransport(app=create_app(tmp_path / "eval.db"))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/import",
            files={"file": ("samples.csv", b"sample_id,scenario_type,task_types\ns-1,interaction,asr|nlu\n", "text/csv")},
        )
        assert response.status_code == 200
        assert response.json()["accepted"] == 1


@pytest.mark.anyio
async def test_multipart_wav_import_preserves_audio_metadata(tmp_path):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 800)
    transport = httpx.ASGITransport(app=create_app(tmp_path / "eval.db"))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/import",
            files={"file": ("call.wav", buffer.getvalue(), "audio/wav")},
        )
        assert response.status_code == 200
        assert response.json()["accepted"] == 1
        detail = await client.get("/api/samples/call")
        assert detail.json()["audio_info"]["duration_ms"] == 100


@pytest.mark.anyio
async def test_all_demo_pages_render(tmp_path):
    transport = httpx.ASGITransport(app=create_app(tmp_path / "eval.db"))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ("/", "/samples", "/import", "/report"):
            response = await client.get(path)
            assert response.status_code == 200, path
            assert "语音" in response.text, path


@pytest.mark.anyio
async def test_sample_detail_page_renders_json_fields(tmp_path):
    transport = httpx.ASGITransport(app=create_app(tmp_path / "eval.db"))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/import", json={"samples": generate_samples(1)})
        await client.post("/api/evaluate")
        response = await client.get("/samples/sample-001")
        assert response.status_code == 200
        assert "量化指标" in response.text
