import io
import wave

from app.audio_dataset import index_audio_directory


def write_wav(path, duration_ms=250):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * (16000 * duration_ms // 1000))


def test_index_uses_filename_as_reference_label_and_keeps_model_output_empty(tmp_path):
    audio_dir = tmp_path / "audios"
    audio_dir.mkdir()
    write_wav(audio_dir / "窃窃私语.wav")
    samples, errors = index_audio_directory(audio_dir, tmp_path)
    assert errors == []
    assert samples[0]["sample_id"] == "窃窃私语"
    assert samples[0]["reference"]["label"] == "窃窃私语"
    assert samples[0]["system_output"] == "-"
    assert samples[0]["input_data"]["audio_path"] == "audios/窃窃私语.wav"
    assert samples[0]["audio_info"]["duration_ms"] == 250


def test_index_reports_unsupported_files_without_blocking_valid_audio(tmp_path):
    audio_dir = tmp_path / "audios"
    audio_dir.mkdir()
    write_wav(audio_dir / "说话.wav")
    (audio_dir / "notes.pdf").write_bytes(b"not audio")
    samples, errors = index_audio_directory(audio_dir, tmp_path)
    assert len(samples) == 1
    assert errors[0]["file"] == "notes.pdf"
    assert "不支持" in errors[0]["message"]
