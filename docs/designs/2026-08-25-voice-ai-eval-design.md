# 多场景语音智能体验评测与问题分析系统设计

## 1. 目标与边界

系统面向语音交互、翻译和车载座舱三类场景，完成样例导入、场景/任务识别、指标计算、质量诊断、人工修订和报告导出。项目内置结构化合成数据用于离线演示，同时支持外部 JSON/JSONL、CSV、TXT、WAV 和 MP3 文件导入；输出支持 JSON、CSV 和 HTML。

## 2. 数据流

`导入 → 校验 → 持久化 → 指标计算 → 诊断 → 人工修订 → 导出`

原始字段缺失时使用 `-`。诊断只能引用输入记录中存在的参考文本、系统输出、日志字段或时间戳；没有证据时返回“证据不足”。单独导入 WAV/MP3 时只提取文件身份和可获得的音频元数据，不生成转写或参考答案。导入 TXT 时每行只作为 `input_data.text`，参考标注和系统输出保持 `-`——不得把输入复制成参考或输出，否则会凭空产生 CER=0 的“通过”结论。

评测阶段逐条隔离异常：单条样例计算失败时记录 `failures` 明细并把失败状态写回该记录，不中断整批评测，`failed` 反映真实失败数。

## 3. 统一记录

每条样例包含 `sample_id`、`scenario_type`、`task_types`、`input_data`、`audio_info`、`reference`、`system_output`、`metrics`、`diagnosis`、`evidence`、`impact`、`suggestions`、`human_revision` 和 `final_conclusion`。

样例分布为交互 40 条、翻译 30 条、座舱 30 条，覆盖单轮/多轮交互、中英互译、术语一致性、媒体/导航指令和安全边界。

## 4. 指标与诊断

- 识别：CER、WER、关键词召回率。
- 语义：意图准确率、槽位匹配率。
- 翻译：术语一致性。
- 体验：响应延迟、首包时间；缺失时为 `-`。
- 座舱：安全规则命中和违规检查。禁止操作词区分来源——出自用户请求（`safety_request_hits`）不构成系统违规；仅当系统输出偏离请求转写且仍含禁止操作时判 `safety_violation`。输出等于请求原文时标记 `safety_assessable=false`，结论为需关注而非通过，避免假阳性与假阴性。

规则诊断保证离线可复现；可选 LLM 适配器通过环境变量配置 OpenAI-compatible 服务。LLM 输出必须通过证据约束校验。

## 5. API 与页面

API 包括 `/api/import`、`/api/evaluate`、`/api/samples`、`/api/samples/{id}`、`/api/samples/{id}/revision`、`/api/export/{format}` 和 `/health`。页面包括总览、导入、样例详情、人工修订和报告导出。

## 6. 持久化与异常处理

SQLite 保存样例、评测、修订和审计事件；导入文件与导出结果位于 `data/`。重复 ID、缺失必填字段和不支持格式在导入阶段逐条报告。单条失败不阻断批处理，所有请求写入结构化日志。
