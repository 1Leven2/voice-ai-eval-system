# 多场景语音智能体验评测与问题分析系统

一个可离线运行的 FastAPI Demo，覆盖语音交互、翻译和车载座舱三类场景。系统支持样例导入、指标计算、证据约束诊断、人工修订和结构化报告导出。项目内置样例是合成数据，但外部真实 JSON/CSV/TXT/WAV/MP3 文件可以直接导入。

## 普通用户使用（推荐）

如果你不熟悉 Python、API 或命令行：

1. 安装 Python 3.10 或更高版本，并在安装界面勾选“Add Python to PATH”。
2. Windows 用户双击项目根目录的 `start.bat`；macOS/Linux 用户双击或运行 `start.sh`。
3. 首次启动会自动安装依赖、准备合成样例和真实音频索引，然后自动打开浏览器。
4. 在页面中点击“样例”查看数据，点击具体样例的“打开音频文件”试听真实音频，点击“报告”下载结果。

启动脚本也支持：

```bash
python3 scripts/start.py                 # 自动准备并打开浏览器
python3 scripts/start.py --no-browser    # 只启动服务，不打开浏览器
python3 scripts/start.py --no-install    # 不自动安装依赖
```

## 开发者快速开始

当前环境使用 Python 3.10。若系统已安装依赖，可直接运行：

```bash
python3 -m pip install --user -e '.[dev]'
python3 scripts/generate_samples.py
python3 scripts/import_audios.py
python3 scripts/run_demo.py --reset
uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000/`。推荐演示流程：

```bash
# `run_demo.py` 已完成导入、指标计算和离线诊断，并写入 data/exports/。
# 首次演示或需要清理旧数据时使用 --reset；普通启动不会清理已有人工修订。

# 查看或下载结果
curl http://127.0.0.1:8000/api/export/json > data/evaluation.json
curl http://127.0.0.1:8000/api/export/csv > data/evaluation.csv
curl http://127.0.0.1:8000/api/export/html > data/evaluation.html
```

也可以从导入页面上传 JSON、JSONL、CSV、TXT、WAV 或 MP3 文件。放入 `data/audios/` 的音频会被 `scripts/import_audios.py` 自动索引：文件名去掉扩展名后作为参考标签，原始音频通过详情页的“打开音频文件”访问。单独上传音频时，系统只保存文件名、格式、大小和 WAV 可读元数据；没有参考转写和系统输出的字段会保持 `-`，不会自动编造文本。CSV 的 `task_types` 支持 `asr|nlu` 或 JSON 数组格式。

## 主要 API

| API | 用途 |
| --- | --- |
| `GET /health` | 健康检查 |
| `POST /api/import` | JSON 请求或 multipart 文件导入 |
| `POST /api/evaluate` | 批量指标计算和诊断 |
| `GET /api/samples` | 查询样例 |
| `GET /api/samples/{sample_id}` | 查询详情 |
| `PATCH /api/samples/{sample_id}/revision` | 保存人工修订和审计差异 |
| `GET /api/export/json\|csv\|html` | 下载结构化结果 |

## 评测与证据规则

- 识别链路计算 CER、WER、关键词召回率。
- 语义链路计算意图准确率和槽位匹配率。
- 翻译链路计算术语一致性。
- 有响应日志时保存延迟和首包时间；没有原始字段时使用 `-`。
- 座舱样例检查禁止操作，命中安全规则时结论为“失败”。
- 诊断文本只引用样例中的参考文本、系统输出、日志或规则命中；没有证据时返回“证据不足”。

## 可选 LLM

默认使用离线规则诊断。配置以下环境变量后，系统会尝试调用 OpenAI-compatible `/chat/completions` 接口；任何网络、密钥或返回格式错误都会自动回退到离线诊断：

```bash
export VOICE_AI_LLM_BASE_URL=https://example.com/v1
export VOICE_AI_LLM_API_KEY=your-key
export VOICE_AI_LLM_MODEL=your-model
```

## 测试

```bash
pytest -q
```

测试覆盖指标、样例校验、重复 ID、JSON/CSV/TXT 导入、三类样例生成、API 全链路、人工修订、安全诊断和导出。

## 项目文档

- `docs/designs/`：设计文档
- `docs/plans/`：实现计划
- `docs/reviews/`：设计、计划实现和代码审查
- `docs/reports/`：最终 AI 提效实践报告及 HTML 版本
- `data/samples.jsonl`：100 条可追溯合成样例
- `data/audios/`：真实 WAV 音频目录（**未纳入版本控制**，见下方说明）
- `data/audio_samples.jsonl`：由文件名标签生成的真实音频索引（同样未纳入版本控制，可本地重建）
- `start.sh`、`start.bat`、`scripts/start.py`：面向普通用户的一键启动入口

## 关于真实音频数据

`data/audios/` 及其派生索引 `data/audio_samples.jsonl` **不在本仓库中**：部分文件名包含设备标识和采集时间戳，内容为真实用户录音，因此仅保留在本地，不对外发布。

这意味着直接克隆本仓库后运行，只会得到 100 条合成样例。如需复现包含真实音频的 143 条完整结果：

1. 将 WAV/MP3 文件放入 `data/audios/`；
2. 运行 `python3 scripts/import_audios.py` 重建索引；
3. 运行 `python3 scripts/run_demo.py --reset`。

缺少该目录时系统会正常降级：`index_audio_directory` 返回“音频目录不存在”并继续处理合成样例，不会中断。
