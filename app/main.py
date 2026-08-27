from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import Database
from .services import EvaluationService, parse_import_bytes


def _default_db_path() -> Path:
    return Path(os.getenv("VOICE_AI_DB_PATH", Path(__file__).resolve().parents[1] / "data" / "eval.db"))


def create_app(db_path: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="多场景语音智能体验评测系统", version="0.1.0")
    root = Path(__file__).resolve().parent
    app.mount("/static", StaticFiles(directory=root / "static"), name="static")
    audio_dir = root.parent / "data" / "audios"
    if audio_dir.exists():
        app.mount("/audio-files", StaticFiles(directory=audio_dir), name="audio-files")
    templates = Jinja2Templates(directory=root / "templates")
    app.state.service = EvaluationService(Database(db_path or _default_db_path()))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/import")
    async def import_samples(request: Request, file: UploadFile | None = File(default=None)) -> dict[str, Any]:
        service: EvaluationService = app.state.service
        try:
            if file is not None:
                result = service.import_samples(parse_import_bytes(await file.read(), file.filename or "samples.json"))
            else:
                payload = await request.json()
                samples = payload.get("samples", payload) if isinstance(payload, dict) else payload
                result = service.import_samples(samples)
            return result
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/evaluate")
    async def evaluate() -> dict[str, Any]:
        return app.state.service.evaluate_all()

    @app.get("/api/samples")
    async def samples(scenario_type: str | None = None) -> list[dict[str, Any]]:
        return app.state.service.database.list_samples(scenario_type)

    @app.get("/api/samples/{sample_id}")
    async def sample_detail(sample_id: str) -> dict[str, Any]:
        sample = app.state.service.database.get_sample(sample_id)
        if sample is None:
            raise HTTPException(status_code=404, detail="样例不存在")
        return sample

    @app.patch("/api/samples/{sample_id}/revision")
    async def revise(sample_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        editor = str(payload.pop("editor", "anonymous"))
        revised = app.state.service.revise(sample_id, payload, editor)
        if revised is None:
            raise HTTPException(status_code=404, detail="样例不存在")
        return revised

    @app.get("/api/export/{format_name}")
    async def export(format_name: str):
        service: EvaluationService = app.state.service
        if format_name == "json":
            return JSONResponse(service.export_rows())
        if format_name == "csv":
            return PlainTextResponse(service.export_csv(), media_type="text/csv; charset=utf-8")
        if format_name == "html":
            return HTMLResponse(service.export_html())
        raise HTTPException(status_code=404, detail="不支持的导出格式")

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        rows = app.state.service.export_rows()
        counts: dict[str, int] = {}
        conclusions: dict[str, int] = {}
        for row in rows:
            counts[row["scenario_type"]] = counts.get(row["scenario_type"], 0) + 1
            conclusion = row.get("final_conclusion", "需关注")
            conclusions[conclusion] = conclusions.get(conclusion, 0) + 1
        return templates.TemplateResponse(request=request, name="dashboard.html", context={"counts": counts, "conclusions": conclusions, "total": len(rows)})

    @app.get("/samples", response_class=HTMLResponse)
    async def samples_page(request: Request):
        return templates.TemplateResponse(request=request, name="samples.html", context={"samples": app.state.service.export_rows()})

    @app.get("/samples/{sample_id}", response_class=HTMLResponse)
    async def detail_page(request: Request, sample_id: str):
        sample = app.state.service.database.get_sample(sample_id)
        if sample is None:
            raise HTTPException(status_code=404, detail="样例不存在")
        return templates.TemplateResponse(request=request, name="detail.html", context={"sample": sample})

    @app.get("/import", response_class=HTMLResponse)
    async def import_page(request: Request):
        return templates.TemplateResponse(request=request, name="import.html", context={})

    @app.get("/report", response_class=HTMLResponse)
    async def report_page(request: Request):
        return templates.TemplateResponse(request=request, name="report.html", context={"samples": app.state.service.export_rows()})

    return app


app = create_app()
