#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.sample_data import write_jsonl


if __name__ == "__main__":
    output = Path(__file__).resolve().parents[1] / "data" / "samples.jsonl"
    print(f"generated {write_jsonl(output)}")
