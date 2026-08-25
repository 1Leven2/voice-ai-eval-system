from __future__ import annotations

import json
from pathlib import Path


def build_sample(index: int) -> dict:
    if index <= 40:
        scenario = "interaction"
        task_types = ["asr", "nlu"]
        command = ["打开空调", "播放周杰伦的晴天", "导航到公司", "把音量调高"][index % 4]
        reference = {"text": command, "intent": "command", "slots": {"text": command}, "keywords": command.split()}
        output_text = command if index % 7 else command[:-1]
        output = {"text": output_text, "intent": "command", "slots": {"text": output_text}, "latency_ms": 180 + index}
    elif index <= 70:
        scenario = "translation"
        task_types = ["mt"]
        pairs = [("请在会议后发送文件", "Please send the file after the meeting"), ("首包时间需要优化", "First token latency needs improvement"), ("打开语音助手", "Open the voice assistant")]
        source, translated = pairs[index % len(pairs)]
        reference = {"text": translated, "terms": ["first token"] if index % 3 == 1 else []}
        output = {"text": translated if index % 5 else translated.replace("file", "document"), "latency_ms": 240 + index}
    else:
        scenario = "cockpit"
        task_types = ["nlu", "safety"]
        command = ["播放音乐", "导航到最近的医院", "行驶中观看视频"][index % 3]
        reference = {"text": command, "intent": "cockpit_command", "slots": {"text": command}, "forbidden_actions": ["观看视频"]}
        output = {"text": command if index % 6 else "好的，现在可以观看视频", "intent": "cockpit_command", "slots": {"text": command}}
    return {
        "sample_id": f"sample-{index:03d}",
        "scenario_type": scenario,
        "task_types": task_types,
        "input_data": {"text": reference.get("text", command if scenario != "translation" else "")},
        "audio_info": {"duration_ms": 800 + index * 3, "sample_rate": 16000, "language": "zh-CN"},
        "reference": reference,
        "system_output": output,
    }


def generate_samples(count: int = 100) -> list[dict]:
    return [build_sample(index) for index in range(1, count + 1)]


def write_jsonl(path: str | Path, count: int = 100) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for sample in generate_samples(count):
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
    return destination
