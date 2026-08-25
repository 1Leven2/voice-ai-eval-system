from __future__ import annotations

from pathlib import Path
from typing import Any

from .audio import audio_metadata_from_bytes


SUPPORTED_AUDIO_SUFFIXES = {".wav", ".mp3"}


def index_audio_directory(directory: str | Path, project_root: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Create transparent evaluation records for audio files on disk.

    The filename stem is stored as a reference label and the model output is
    intentionally left as '-' until an actual recognizer/classifier is run.
    """
    audio_root = Path(directory)
    root = Path(project_root)
    samples: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    if not audio_root.exists():
        return [], [{"file": str(audio_root), "message": "音频目录不存在"}]
    for path in sorted(audio_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
            errors.append({"file": path.name, "message": f"不支持的音频格式: {path.suffix or '无扩展名'}"})
            continue
        sample_id = path.stem
        if sample_id in seen_ids:
            errors.append({"file": path.name, "message": f"重复样例 ID: {sample_id}"})
            continue
        try:
            content = path.read_bytes()
            relative_path = path.relative_to(root).as_posix()
            samples.append(
                {
                    "sample_id": sample_id,
                    "scenario_type": "audio_classification",
                    "task_types": ["audio_classification"],
                    "input_data": {"audio_file": path.name, "audio_path": relative_path},
                    "audio_info": audio_metadata_from_bytes(content, path.name),
                    "reference": {"label": sample_id, "label_source": "filename"},
                    "system_output": "-",
                }
            )
            seen_ids.add(sample_id)
        except OSError as exc:
            errors.append({"file": path.name, "message": f"读取失败: {exc}"})
    return samples, errors
