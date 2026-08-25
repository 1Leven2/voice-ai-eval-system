from app.db import Database


def test_clear_all_removes_demo_records_and_audit_history(tmp_path):
    db = Database(tmp_path / "eval.db")
    db.upsert_samples([{"sample_id": "s-1", "scenario_type": "audio_classification", "task_types": ["audio_classification"]}])
    assert len(db.list_samples()) == 1
    db.clear_all()
    assert db.list_samples() == []
