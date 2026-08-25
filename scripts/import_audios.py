#!/usr/bin/env python3
"""Index data/audios into transparent JSONL records without changing audio files."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.audio_dataset import index_audio_directory


if __name__ == "__main__":
    samples, errors = index_audio_directory(ROOT / "data" / "audios", ROOT)
    output = ROOT / "data" / "audio_samples.jsonl"
    output.write_text("".join(json.dumps(sample, ensure_ascii=False) + "\n" for sample in samples), encoding="utf-8")
    print(json.dumps({"indexed": len(samples), "errors": errors, "output": str(output)}, ensure_ascii=False))
