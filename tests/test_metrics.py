from app.metrics import (
    character_error_rate,
    keyword_recall,
    intent_slot_match,
    terminology_consistency,
)


def test_character_error_rate_counts_insertions_deletions_and_substitutions():
    assert character_error_rate("你好世界", "你好世") == 0.25


def test_keyword_recall_is_case_insensitive_and_deduplicated():
    assert keyword_recall("Open Door, open window", ["open", "window", "alarm"]) == 2 / 3


def test_intent_slot_match_returns_separate_scores():
    result = intent_slot_match(
        {"intent": "play_music", "slots": {"artist": "周杰伦", "song": "晴天"}},
        {"intent": "play_music", "slots": {"artist": "周杰伦", "song": "稻香"}},
    )
    assert result == {"intent_accuracy": 1.0, "slot_match_rate": 0.5}


def test_terminology_consistency_compares_required_terms():
    assert terminology_consistency("Use latency and first token", ["latency", "first token", "WER"]) == 2 / 3
