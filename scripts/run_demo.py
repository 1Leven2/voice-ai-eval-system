#!/usr/bin/env python3
"""Load the bundled fixture, evaluate it, and write all report formats."""

import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import Database
from app.audio_dataset import index_audio_directory
from app.services import EvaluationService


def main() -> None:
    parser = argparse.ArgumentParser(description="准备合成样例和真实音频索引")
    parser.add_argument("--reset", action="store_true", help="清空本地 Demo 数据库后重新导入")
    args = parser.parse_args()
    samples_path = ROOT / "data" / "samples.jsonl"
    if not samples_path.exists():
        from app.sample_data import write_jsonl

        write_jsonl(samples_path)
    samples = [json.loads(line) for line in samples_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    database = Database(ROOT / "data" / "eval.db")
    if args.reset:
        database.clear_all()
    service = EvaluationService(database)
    result = service.import_samples(samples)
    audio_samples, audio_errors = index_audio_directory(ROOT / "data" / "audios", ROOT)
    audio_result = service.import_samples(audio_samples) if audio_samples else {"accepted": 0, "rejected": 0, "errors": []}
    if audio_samples:
        (ROOT / "data" / "audio_samples.jsonl").write_text(
            "".join(json.dumps(sample, ensure_ascii=False) + "\n" for sample in audio_samples),
            encoding="utf-8",
        )
    evaluated = service.evaluate_all()
    exports = ROOT / "data" / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    (exports / "evaluation.json").write_text(json.dumps(service.export_rows(), ensure_ascii=False, indent=2), encoding="utf-8")
    (exports / "evaluation.csv").write_text(service.export_csv(), encoding="utf-8")
    (exports / "evaluation.html").write_text(service.export_html(), encoding="utf-8")
    print(json.dumps({"import": result, "audio_import": audio_result, "audio_errors": audio_errors, "evaluate": evaluated, "exports": str(exports)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
