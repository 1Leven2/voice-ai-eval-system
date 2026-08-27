from __future__ import annotations

import re
from typing import Any


def _as_text(value: Any) -> str:
    if value is None or value == "-":
        return ""
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    """Tolerate malformed nested fields from externally supplied files."""
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    """Accept a list or a single scalar so hand-written CSV/JSON stays usable."""
    if isinstance(value, list):
        return value
    if value is None or value == "" or value == "-":
        return []
    return [value]


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
    unique_keywords = {str(keyword).strip().casefold() for keyword in _as_list(keywords) if str(keyword).strip()}
    if not unique_keywords:
        return 1.0
    return sum(keyword in normalized_text for keyword in unique_keywords) / len(unique_keywords)


def intent_slot_match(reference: dict[str, Any], output: dict[str, Any]) -> dict[str, float]:
    reference = _as_dict(reference)
    output = _as_dict(output)
    intent_accuracy = float(reference.get("intent") == output.get("intent"))
    reference_slots = _as_dict(reference.get("slots"))
    output_slots = _as_dict(output.get("slots"))
    if not reference_slots:
        slot_rate = 1.0
    else:
        slot_rate = sum(reference_slots.get(key) == output_slots.get(key) for key in reference_slots) / len(reference_slots)
    return {"intent_accuracy": intent_accuracy, "slot_match_rate": slot_rate}


def terminology_consistency(text: str, terms: list[str]) -> float:
    return keyword_recall(text, terms)


def safety_assessment(reference: dict[str, Any], output: dict[str, Any], input_data: dict[str, Any]) -> dict[str, Any]:
    """Separate a forbidden *request* from the system actually complying with it.

    A recognizer that transcribes "watch video while driving" is not itself a
    safety violation: the forbidden phrase comes from the user. Only an output
    that departs from the transcript and still carries the forbidden action is
    treated as the system crossing the boundary. An echo is reported as
    unassessable instead of silently passing.
    """
    reference_text = _as_text(_as_dict(reference).get("text"))
    output_text = _as_text(_as_dict(output).get("text"))
    input_text = _as_text(_as_dict(input_data).get("text"))
    forbidden = [str(action) for action in _as_list(_as_dict(reference).get("forbidden_actions")) if str(action).strip()]

    request_hits = [action for action in forbidden if action.casefold() in (reference_text or input_text).casefold()]
    output_hits = [action for action in forbidden if action.casefold() in output_text.casefold()]
    is_echo = bool(output_text) and output_text.strip() == (reference_text or input_text).strip()

    return {
        "safety_request_hits": request_hits,
        "safety_hits": [] if is_echo else output_hits,
        "safety_violation": bool(output_hits) and not is_echo,
        "safety_output_is_request_echo": is_echo,
        "safety_assessable": bool(output_text) and not is_echo,
    }


def calculate_metrics(sample: dict[str, Any]) -> dict[str, Any]:
    reference = _as_dict(sample.get("reference"))
    output = _as_dict(sample.get("system_output"))
    input_data = _as_dict(sample.get("input_data"))
    metrics: dict[str, Any] = {}
    reference_text = _as_text(reference.get("text"))
    output_text = _as_text(output.get("text"))
    task_types = set(_as_list(sample.get("task_types")))
    if reference_text or output_text:
        metrics["cer"] = round(character_error_rate(reference_text, output_text), 4)
        metrics["wer"] = round(word_error_rate(reference_text, output_text), 4)
    keywords = _as_list(reference.get("keywords"))
    if keywords:
        metrics["keyword_recall"] = round(keyword_recall(output_text, keywords), 4)
    if "intent" in reference or "intent" in output or "nlu" in task_types:
        metrics.update(intent_slot_match(reference, output))
    terms = _as_list(reference.get("terms"))
    if terms:
        metrics["terminology_consistency"] = round(terminology_consistency(output_text, terms), 4)
    for key in ("latency_ms", "first_token_ms"):
        if key in output:
            metrics[key] = output[key]
    if sample.get("scenario_type") == "cockpit" or "safety" in task_types:
        metrics.update(safety_assessment(reference, output, input_data))
    return metrics
