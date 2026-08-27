from __future__ import annotations

from typing import Any


def infer_labels(sample: dict[str, Any]) -> dict[str, Any]:
    """Infer missing scene/task labels from supplied content only.

    Explicit labels always win. This is a transparent heuristic, not a model
    prediction; callers can still revise the labels manually.
    """
    enriched = dict(sample)
    input_data = enriched.get("input_data") if isinstance(enriched.get("input_data"), dict) else {}
    reference = enriched.get("reference") if isinstance(enriched.get("reference"), dict) else {}
    output = enriched.get("system_output") if isinstance(enriched.get("system_output"), dict) else {}
    text = " ".join(str(value) for value in (input_data.get("text", ""), reference.get("text", ""), output.get("text", ""))).casefold()
    filename = str(input_data.get("audio_file", "")).casefold()
    existing_tasks = list(enriched.get("task_types") or [])
    scene = str(enriched.get("scenario_type") or "").strip()

    if not existing_tasks:
        if any(term in text for term in ("翻译", "translate", "translation", "译成", "译为")):
            existing_tasks = ["mt"]
        elif any(term in text for term in ("安全", "座舱", "车载", "导航", "行驶", "空调")):
            existing_tasks = ["nlu"]
        elif filename:
            existing_tasks = ["audio_classification"]
        else:
            existing_tasks = ["asr"]
    enriched["task_types"] = existing_tasks

    if not scene:
        if "mt" in existing_tasks or any(term in text for term in ("翻译", "translate", "translation", "译成", "译为")):
            scene = "translation"
        elif "audio_classification" in existing_tasks or filename:
            scene = "audio_classification"
        elif "safety" in existing_tasks or any(term in text for term in ("座舱", "车载", "导航", "行驶", "空调")):
            scene = "cockpit"
        else:
            scene = "interaction"
    enriched["scenario_type"] = scene
    return enriched
