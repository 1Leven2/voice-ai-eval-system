import json

from app.diagnostics import rule_diagnosis
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
    assert rows[0]["sample_id"] == "txt-1"
    assert rows[1]["reference"]["text"] == "播放音乐"


def test_safety_diagnosis_marks_forbidden_action_as_failure():
    sample = {
        "scenario_type": "cockpit",
        "reference": {"text": "行驶中观看视频", "forbidden_actions": ["观看视频"]},
        "system_output": {"text": "好的，现在可以观看视频"},
        "task_types": ["safety"],
    }
    result = rule_diagnosis(sample, {"safety_violation": True, "safety_hits": ["观看视频"]})
    assert result["final_conclusion"] == "失败"
    assert result["evidence"]
