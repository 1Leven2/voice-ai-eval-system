from app.models import validate_sample, validate_samples


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
