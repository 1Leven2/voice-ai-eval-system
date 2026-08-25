from __future__ import annotations

import re
from typing import Any


def _as_text(value: Any) -> str:
    if value is None or value == "-":
        return ""
    return str(value)


def _distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for i, ref_item in enumerate(reference, start=1):
        current = [i]
        for j, hyp_item in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (ref_item != hyp_item),
                )
            )
        previous = current
    return previous[-1]


def character_error_rate(reference: str, hypothesis: str) -> float:
    reference_chars = list(_as_text(reference))
    hypothesis_chars = list(_as_text(hypothesis))
    if not reference_chars:
        return 0.0 if not hypothesis_chars else 1.0
    return _distance(reference_chars, hypothesis_chars) / len(reference_chars)


def word_error_rate(reference: str, hypothesis: str) -> float:
    reference_words = _as_text(reference).split()
    hypothesis_words = _as_text(hypothesis).split()
    if not reference_words:
        return 0.0 if not hypothesis_words else 1.0
    return _distance(reference_words, hypothesis_words) / len(reference_words)


def keyword_recall(text: str, keywords: list[str]) -> float:
    normalized_text = _as_text(text).casefold()
    unique_keywords = {str(keyword).strip().casefold() for keyword in keywords if str(keyword).strip()}
    if not unique_keywords:
        return 1.0
    return sum(keyword in normalized_text for keyword in unique_keywords) / len(unique_keywords)


def intent_slot_match(reference: dict[str, Any], output: dict[str, Any]) -> dict[str, float]:
    intent_accuracy = float(reference.get("intent") == output.get("intent"))
    reference_slots = reference.get("slots") or {}
    output_slots = output.get("slots") or {}
    if not reference_slots:
        slot_rate = 1.0
    else:
        slot_rate = sum(reference_slots.get(key) == output_slots.get(key) for key in reference_slots) / len(reference_slots)
    return {"intent_accuracy": intent_accuracy, "slot_match_rate": slot_rate}


def terminology_consistency(text: str, terms: list[str]) -> float:
    return keyword_recall(text, terms)


def calculate_metrics(sample: dict[str, Any]) -> dict[str, Any]:
    reference = sample.get("reference") if isinstance(sample.get("reference"), dict) else {}
    output = sample.get("system_output") if isinstance(sample.get("system_output"), dict) else {}
    metrics: dict[str, Any] = {}
    reference_text = reference.get("text", "")
    output_text = output.get("text", "")
    task_types = set(sample.get("task_types") or [])
    if reference_text or output_text:
        metrics["cer"] = round(character_error_rate(reference_text, output_text), 4)
        metrics["wer"] = round(word_error_rate(reference_text, output_text), 4)
    keywords = reference.get("keywords") or []
    if keywords:
        metrics["keyword_recall"] = round(keyword_recall(output_text, keywords), 4)
    if "intent" in reference or "intent" in output or "nlu" in task_types:
        metrics.update(intent_slot_match(reference, output))
    terms = reference.get("terms") or []
    if terms:
        metrics["terminology_consistency"] = round(terminology_consistency(output_text, terms), 4)
    for key in ("latency_ms", "first_token_ms"):
        if key in output:
            metrics[key] = output[key]
    if sample.get("scenario_type") == "cockpit" or "safety" in task_types:
        forbidden = reference.get("forbidden_actions") or []
        hits = [action for action in forbidden if action.casefold() in output_text.casefold()]
        metrics["safety_violation"] = bool(hits)
        metrics["safety_hits"] = hits
    return metrics
