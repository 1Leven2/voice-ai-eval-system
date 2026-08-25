from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


def _evidence(sample: dict[str, Any], metrics: dict[str, Any]) -> list[str]:
    reference = sample.get("reference") if isinstance(sample.get("reference"), dict) else {}
    output = sample.get("system_output") if isinstance(sample.get("system_output"), dict) else {}
    evidence: list[str] = []
    if reference.get("text") or output.get("text"):
        evidence.append(f"参考文本: {reference.get('text', '-')}; 系统输出: {output.get('text', '-')}")
    if metrics.get("cer", 0) > 0:
        evidence.append(f"CER={metrics['cer']}")
    if metrics.get("wer", 0) > 0:
        evidence.append(f"WER={metrics['wer']}")
    if metrics.get("safety_violation"):
        evidence.append(f"安全规则命中: {', '.join(metrics.get('safety_hits', []))}")
    return evidence


def rule_diagnosis(sample: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    evidence = _evidence(sample, metrics)
    issues: list[str] = []
    suggestions: list[str] = []
    if metrics.get("cer", 0) > 0.2 or metrics.get("wer", 0) > 0.2:
        issues.append("识别结果与参考文本存在较大差异")
        suggestions.append("补充噪声、口音和领域热词数据，并检查后处理规则")
    if metrics.get("keyword_recall", 1) < 1:
        issues.append("关键词漏识别")
        suggestions.append("增加关键词召回评测和热词表")
    if metrics.get("slot_match_rate", 1) < 1:
        issues.append("槽位填充不完整或不一致")
        suggestions.append("优化槽位抽取提示词并增加边界样例")
    if metrics.get("terminology_consistency", 1) < 1:
        issues.append("译文术语不一致")
        suggestions.append("维护术语表并在翻译后处理阶段统一术语")
    if metrics.get("safety_violation"):
        issues.append("回复触发车载安全边界")
        suggestions.append("增加安全拒答规则并在危险操作前进行链路降级")
    if not evidence:
        return {
            "diagnosis": "证据不足",
            "evidence": [],
            "impact": "无法基于当前原始数据判断影响",
            "suggestions": [],
            "final_conclusion": "需关注",
        }
    return {
        "diagnosis": "；".join(issues) if issues else "未发现明确问题",
        "evidence": evidence,
        "impact": "可能影响任务完成率、可理解性或车载安全" if issues else "当前样例达到规则阈值",
        "suggestions": suggestions,
        "final_conclusion": "失败" if metrics.get("safety_violation") else ("需关注" if issues else "通过"),
    }


def optional_llm_diagnosis(sample: dict[str, Any], metrics: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    """Use an OpenAI-compatible endpoint only when explicitly configured.

    The offline fallback is returned for missing configuration or any network/API error.
    Evidence from the fallback is retained as the source of truth.
    """
    base_url = os.getenv("VOICE_AI_LLM_BASE_URL", "").strip()
    api_key = os.getenv("VOICE_AI_LLM_API_KEY", "").strip()
    model = os.getenv("VOICE_AI_LLM_MODEL", "").strip()
    if not (base_url and api_key and model):
        return fallback
    prompt = {
        "instruction": "仅基于 evidence 判断问题，不得补造事实。返回 JSON diagnosis, impact, suggestions, final_conclusion。",
        "sample": sample,
        "metrics": metrics,
        "evidence": fallback["evidence"],
    }
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": model, "messages": [{"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}]}).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = json.loads(response.read().decode())
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        parsed["evidence"] = fallback["evidence"]
        return parsed
    except Exception:
        return fallback
