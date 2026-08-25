from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationErrorItem:
    row: int
    field: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_FIELDS: dict[str, Any] = {
    "input_data": {},
    "audio_info": "-",
    "reference": {},
    "system_output": {},
    "metrics": {},
    "diagnosis": "-",
    "evidence": [],
    "impact": "-",
    "suggestions": [],
    "human_revision": None,
    "final_conclusion": "需关注",
}


def normalize_sample(sample: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(DEFAULT_FIELDS)
    normalized.update(sample)
    normalized["task_types"] = list(normalized.get("task_types") or [])
    return normalized


def validate_sample(sample: dict[str, Any], row: int = 1) -> list[ValidationErrorItem]:
    errors: list[ValidationErrorItem] = []
    if not isinstance(sample, dict):
        return [ValidationErrorItem(row, "sample", "必须是对象")]
    for field, message in (
        ("sample_id", "不能为空"),
        ("scenario_type", "不能为空"),
    ):
        value = sample.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(ValidationErrorItem(row, field, message))
    task_types = sample.get("task_types")
    if not isinstance(task_types, list) or not task_types:
        errors.append(ValidationErrorItem(row, "task_types", "必须是非空数组"))
    return errors


def validate_samples(samples: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[ValidationErrorItem]]:
    accepted: list[dict[str, Any]] = []
    errors: list[ValidationErrorItem] = []
    seen: set[str] = set()
    for row_number, sample in enumerate(samples, start=1):
        row_errors = validate_sample(sample, row_number)
        sample_id = sample.get("sample_id") if isinstance(sample, dict) else None
        if not row_errors and sample_id in seen:
            row_errors.append(ValidationErrorItem(row_number, "sample_id", "重复样例 ID"))
        if row_errors:
            errors.extend(row_errors)
            continue
        seen.add(sample_id)
        accepted.append(normalize_sample(sample))
    return accepted, errors
