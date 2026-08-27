from app.models import normalize_sample, validate_sample, validate_samples


def test_validate_sample_requires_id_scenario_and_task_types():
    errors = validate_sample({"sample_id": "", "scenario_type": "", "task_types": []})
    assert {error.field for error in errors} == {"sample_id", "scenario_type", "task_types"}


def test_validate_samples_reports_duplicate_ids_without_dropping_rows():
    rows = [
        {"sample_id": "s-1", "scenario_type": "interaction", "task_types": ["asr"]},
        {"sample_id": "s-1", "scenario_type": "translation", "task_types": ["mt"]},
    ]
    accepted, errors = validate_samples(rows)
    assert len(accepted) == 1
    assert errors[0].row == 2
    assert errors[0].field == "sample_id"


def test_normalize_sample_marks_unprovided_structured_fields_as_dash():
    sample = normalize_sample({"sample_id": "s-1", "scenario_type": "interaction", "task_types": ["asr"]})
    for field in ("input_data", "audio_info", "reference", "system_output", "metrics", "diagnosis", "evidence", "impact", "suggestions", "human_revision"):
        assert sample[field] == "-", field


def test_validate_samples_infers_translation_scene_and_task_from_input_text():
    accepted, errors = validate_samples(
        [{"sample_id": "translate-1", "input_data": {"text": "请把这句话翻译成英文"}}]
    )
    assert errors == []
    assert accepted[0]["scenario_type"] == "translation"
    assert accepted[0]["task_types"] == ["mt"]
