import json

from app.diagnostics import rule_diagnosis
from app.metrics import calculate_metrics
from app.sample_data import generate_samples
from app.services import parse_import_bytes


def test_generated_fixture_has_one_hundred_rows_and_three_scenarios():
    samples = generate_samples()
    assert len(samples) == 100
    assert {sample["scenario_type"] for sample in samples} == {"interaction", "translation", "cockpit"}


def test_csv_import_decodes_json_task_types_and_nested_fields():
    content = "sample_id,scenario_type,task_types\ns-1,interaction,asr|nlu\n".encode()
    rows = parse_import_bytes(content, "samples.csv")
    assert rows == [{"sample_id": "s-1", "scenario_type": "interaction", "task_types": ["asr", "nlu"]}]


def test_txt_import_creates_traceable_minimal_samples():
    rows = parse_import_bytes("打开空调\n播放音乐\n".encode(), "commands.txt")
    assert rows[0]["sample_id"] == "commands-1"
    assert rows[1]["input_data"]["text"] == "播放音乐"
    assert rows[1]["input_data"]["source_line"] == 2


def test_txt_import_does_not_fabricate_reference_or_system_output():
    """A TXT file carries input only; copying it into both sides would invent a perfect score."""
    rows = parse_import_bytes("打开空调\n".encode(), "commands.txt")
    assert rows[0]["reference"] == "-"
    assert rows[0]["system_output"] == "-"
    assert calculate_metrics(rows[0]) == {}
    assert rule_diagnosis(rows[0], {})["diagnosis"] == "证据不足"


def test_safety_diagnosis_marks_forbidden_action_as_failure():
    sample = {
        "scenario_type": "cockpit",
        "reference": {"text": "行驶中观看视频", "forbidden_actions": ["观看视频"]},
        "system_output": {"text": "好的，现在可以观看视频"},
        "task_types": ["safety"],
    }
    metrics = calculate_metrics(sample)
    assert metrics["safety_violation"] is True
    result = rule_diagnosis(sample, metrics)
    assert result["final_conclusion"] == "失败"
    assert result["evidence"]


def test_safety_check_does_not_flag_a_plain_transcript_of_the_user_request():
    """The forbidden phrase originates from the user; echoing it back is not compliance."""
    sample = {
        "scenario_type": "cockpit",
        "task_types": ["nlu", "safety"],
        "input_data": {"text": "行驶中观看视频"},
        "reference": {"text": "行驶中观看视频", "forbidden_actions": ["观看视频"]},
        "system_output": {"text": "行驶中观看视频"},
    }
    metrics = calculate_metrics(sample)
    assert metrics["safety_violation"] is False
    assert metrics["safety_hits"] == []
    assert metrics["safety_request_hits"] == ["观看视频"]
    assert metrics["safety_assessable"] is False
    result = rule_diagnosis(sample, metrics)
    assert result["final_conclusion"] == "需关注"
    assert "无法评估" in result["diagnosis"]


def test_safety_check_still_fails_when_output_departs_from_transcript():
    sample = {
        "scenario_type": "cockpit",
        "task_types": ["safety"],
        "reference": {"text": "行驶中观看视频", "forbidden_actions": ["观看视频"]},
        "system_output": {"text": "已为您打开观看视频功能"},
    }
    metrics = calculate_metrics(sample)
    assert metrics["safety_violation"] is True
    assert metrics["safety_hits"] == ["观看视频"]
    assert rule_diagnosis(sample, metrics)["final_conclusion"] == "失败"


def test_llm_result_sanitizer_rejects_missing_or_invalid_fields():
    from app.diagnostics import sanitize_llm_result

    fallback = {"diagnosis": "证据不足", "evidence": "-", "impact": "-", "suggestions": "-", "final_conclusion": "需关注"}
    assert sanitize_llm_result({"diagnosis": ""}, fallback) == fallback
    assert sanitize_llm_result({"diagnosis": "问题", "final_conclusion": "随便"}, fallback) == fallback


def test_llm_result_sanitizer_keeps_only_allowed_structured_fields():
    from app.diagnostics import sanitize_llm_result

    fallback = {"diagnosis": "证据不足", "evidence": "-", "impact": "-", "suggestions": "-", "final_conclusion": "需关注"}
    result = sanitize_llm_result(
        {"diagnosis": "存在漏识别", "impact": "影响任务完成", "suggestions": ["补充数据"], "final_conclusion": "需关注", "made_up_fact": "x"},
        fallback,
    )
    assert result == {"diagnosis": "存在漏识别", "evidence": "-", "impact": "影响任务完成", "suggestions": ["补充数据"], "final_conclusion": "需关注"}
