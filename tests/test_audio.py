import io
import wave

from app.audio import audio_metadata_from_bytes
from app.services import parse_import_bytes


def wav_bytes(frame_count: int = 1600, rate: int = 16000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frame_count)
    return buffer.getvalue()


def test_wav_metadata_reads_duration_rate_channels_and_format():
    metadata = audio_metadata_from_bytes(wav_bytes(), "meeting.wav")
    assert metadata["format"] == "wav"
    assert metadata["duration_ms"] == 100
    assert metadata["sample_rate"] == 16000
    assert metadata["channels"] == 1


def test_audio_import_creates_traceable_sample_without_inventing_transcript():
    rows = parse_import_bytes(wav_bytes(), "meeting.wav")
    assert rows[0]["sample_id"] == "meeting"
    assert rows[0]["audio_info"]["duration_ms"] == 100
    assert rows[0]["reference"] == "-"
    assert rows[0]["system_output"] == "-"


def test_mp3_import_preserves_file_identity_when_duration_is_unavailable():
    rows = parse_import_bytes(b"ID3fake", "briefing.mp3")
    assert rows[0]["sample_id"] == "briefing"
    assert rows[0]["audio_info"]["format"] == "mp3"
    assert rows[0]["audio_info"]["duration_ms"] == "-"
