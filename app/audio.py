from __future__ import annotations

import io
import wave
from pathlib import Path
from typing import Any


def audio_metadata_from_bytes(content: bytes, filename: str) -> dict[str, Any]:
    """Extract safe metadata without attempting to invent a transcript.

    WAV metadata is decoded with the standard library. MP3 identity and size are
    preserved, while duration remains '-' unless an external decoder is added.
    """
    suffix = Path(filename).suffix.lower().lstrip(".") or "unknown"
    metadata: dict[str, Any] = {"format": suffix, "file_name": Path(filename).name, "file_size_bytes": len(content)}
    if suffix == "wav":
        try:
            with wave.open(io.BytesIO(content), "rb") as handle:
                frame_rate = handle.getframerate()
                frame_count = handle.getnframes()
                metadata.update(
                    {
                        "duration_ms": round(frame_count * 1000 / frame_rate) if frame_rate else "-",
                        "sample_rate": frame_rate or "-",
                        "channels": handle.getnchannels(),
                        "sample_width_bytes": handle.getsampwidth(),
                    }
                )
        except (wave.Error, EOFError):
            metadata.update({"duration_ms": "-", "sample_rate": "-", "channels": "-"})
    elif suffix == "mp3":
        metadata.update({"duration_ms": "-", "sample_rate": "-", "channels": "-"})
    else:
        metadata.update({"duration_ms": "-", "sample_rate": "-", "channels": "-"})
    return metadata
