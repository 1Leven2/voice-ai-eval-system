from __future__ import annotations

import csv
import io
import json
import logging
from html import escape
from typing import Any

from .audio import audio_metadata_from_bytes
from .db import Database
from .diagnostics import optional_llm_diagnosis, rule_diagnosis
from .metrics import calculate_metrics
from .models import validate_samples

logger = logging.getLogger(__name__)


def parse_import_bytes(content: bytes, filename: str = "samples.json") -> list[dict[str, Any]]:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else "json"
    if suffix in {"wav", "mp3"}:
        sample_id = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].rsplit(".", 1)[0]
        return [
            {
                "sample_id": sample_id or "audio-sample",
                "scenario_type": "audio_unclassified",
                "task_types": ["asr"],
                "input_data": {"audio_file": filename, "file_size_bytes": len(content)},
                "audio_info": audio_metadata_from_bytes(content, filename),
                "reference": "-",
                "system_output": "-",
            }
        ]
    text = content.decode("utf-8-sig")
    if suffix in {"json", "jsonl"}:
        if suffix == "jsonl":
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        payload = json.loads(text)
        return payload.get("samples", payload) if isinstance(payload, dict) else payload
    if suffix == "csv":
        rows: list[dict[str, Any]] = []
        for row in csv.DictReader(io.StringIO(text)):
            parsed: dict[str, Any] = {}
            for key, value in row.items():
                value = value or ""
                if key == "task_types":
                    try:
                        parsed[key] = json.loads(value) if value.startswith("[") else [item for item in value.split("|") if item]
                    except json.JSONDecodeError:
                        parsed[key] = [item for item in value.split("|") if item]
                elif value.startswith("{") or value.startswith("["):
                    try:
                        parsed[key] = json.loads(value)
                    except json.JSONDecodeError:
                        parsed[key] = value
                else:
                    parsed[key] = value
            rows.append(parsed)
        return rows
    if suffix == "txt":
        # A plain text line is input only. Reference annotation and system output
        # are not present in the file, so they stay '-' instead of being copied
        # from the input, which would fabricate a perfect (CER=0) result.
        stem = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].rsplit(".", 1)[0] or "txt"
        return [
            {
                "sample_id": f"{stem}-{index}",
                "task_types": ["asr"],
                "input_data": {"text": line.strip(), "source_file": filename, "source_line": index},
                "reference": "-",
                "system_output": "-",
            }
            for index, line in enumerate(text.splitlines(), start=1)
            if line.strip()
        ]
    raise ValueError(f"不支持的文件格式: .{suffix}")


class EvaluationService:
    def __init__(self, database: Database):
        self.database = database

    def import_samples(self, samples: list[dict[str, Any]]) -> dict[str, Any]:
        accepted, errors = validate_samples(samples)
        if accepted:
            self.database.upsert_samples(accepted)
        return {"accepted": len(accepted), "rejected": len(samples) - len(accepted), "errors": [error.to_dict() for error in errors]}

    def evaluate_all(self) -> dict[str, Any]:
        samples = self.database.list_samples()
        evaluated = 0
        failures: list[dict[str, str]] = []
        for sample in samples:
            sample_id = str(sample.get("sample_id", "-"))
            try:
                metrics = calculate_metrics(sample)
                diagnosis = optional_llm_diagnosis(sample, metrics, rule_diagnosis(sample, metrics))
                sample["metrics"] = metrics if metrics else "-"
                sample.update(diagnosis)
                self.database.update_sample(sample)
                evaluated += 1
            except Exception as exc:  # one malformed record must not abort the batch
                logger.exception("样例评测失败: %s", sample_id)
                failures.append({"sample_id": sample_id, "message": f"{type(exc).__name__}: {exc}"})
                self._mark_evaluation_failure(sample, exc)
        return {"evaluated": evaluated, "failed": len(failures), "failures": failures}

    def _mark_evaluation_failure(self, sample: dict[str, Any], exc: Exception) -> None:
        """Persist the failure on the record so it stays visible in exports."""
        try:
            sample["metrics"] = "-"
            sample["diagnosis"] = f"评测失败：{type(exc).__name__}"
            sample["evidence"] = "-"
            sample["impact"] = "该样例未完成评测，无法给出影响判断"
            sample["suggestions"] = "检查该样例的字段结构是否符合导入规范"
            sample["final_conclusion"] = "需关注"
            self.database.update_sample(sample)
        except Exception:
            logger.exception("无法保存评测失败状态: %s", sample.get("sample_id", "-"))

    def revise(self, sample_id: str, changes: dict[str, Any], editor: str) -> dict[str, Any] | None:
        before = self.database.get_sample(sample_id)
        if before is None:
            return None
        after = dict(before)
        for field in ("diagnosis", "evidence", "impact", "suggestions", "final_conclusion"):
            if field in changes:
                after[field] = changes[field]
        after["human_revision"] = {"editor": editor, "changed_fields": sorted(set(changes) & set(after))}
        self.database.save_revision(sample_id, before, after, editor)
        self.database.update_sample(after)
        return after

    def export_rows(self) -> list[dict[str, Any]]:
        return self.database.list_samples()

    def export_csv(self) -> str:
        rows = self.export_rows()
        fields = ["sample_id", "scenario_type", "task_types", "metrics", "diagnosis", "evidence", "impact", "suggestions", "final_conclusion"]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: json.dumps(row.get(field), ensure_ascii=False) if isinstance(row.get(field), (dict, list)) else row.get(field, "-") for field in fields})
        return output.getvalue()

    def export_html(self) -> str:
        rows = self.export_rows()
        table_rows = "".join(
            "<tr>" + "".join(f"<td>{escape(str(row.get(field, '-')))}</td>" for field in ("sample_id", "scenario_type", "final_conclusion", "diagnosis")) + "</tr>"
            for row in rows
        )
        return "<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>语音评测报告</title><style>body{font-family:system-ui;margin:2rem}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:.5rem;text-align:left}</style><h1>多场景语音智能体验评测报告</h1><table><thead><tr><th>ID</th><th>场景</th><th>结论</th><th>诊断</th></tr></thead><tbody>" + table_rows + "</tbody></table></html>"
