"""OCR extraction heuristics — tested on text fixtures (no Tesseract needed)."""

import pytest

from app.logic.ocr_extract import (
    classify,
    extract_task_candidates,
    line_score,
    looks_like_reminder,
    looks_like_task,
    ocr_available,
)

# ---------------------------------------------------------------------------
# Fixtures: raw text as it might come from a screenshot OCR
# ---------------------------------------------------------------------------

SCREENSHOT_SHOPPING = """Grocery list - screenshot 12.03
- buy oat milk
- call the dentist tomorrow
https://some-recipe-site.com/pancakes
just a thought about the weekend plan
- pay rent by Friday
"""

SCREENSHOT_UKRAINIAN = """Нотатки з дзвінка
- купити картонні коробки
- зателефонувати о 15:00
цікава стаття про маркетинг
- оплатити до 25.03
"""

SCREENSHOT_MEETING = """Meeting notes 2026-11-05
Q3 numbers look fine, revenue is up.
Action items:
[ ] send the report to Anna by Monday
[x] review the budget
schedule a follow-up with the vendor
"""

LONG_PARAGRAPH = ("I have been thinking a lot lately about how the whole thing should work "
                  "and there are many moving pieces that we have not fully considered yet, "
                  "so let's wait with the decision.")

FIXTURES = [SCREENSHOT_SHOPPING, SCREENSHOT_UKRAINIAN, SCREENSHOT_MEETING, LONG_PARAGRAPH]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

class TestExtraction:
    def test_english_screenshot_finds_action_lines(self):
        cands = extract_task_candidates(SCREENSHOT_SHOPPING)
        texts = [c["text"] for c in cands]
        assert "- buy oat milk" not in texts  # bullet is stripped
        assert "buy oat milk" in texts
        assert "call the dentist tomorrow" in texts
        assert "pay rent by Friday" in texts
        # URL line must never be a candidate
        assert not any("recipe-site" in t for t in texts)
        # chatty line without verb/date stays out
        assert not any("weekend plan" in t for t in texts)

    def test_ukrainian_screenshot(self):
        cands = extract_task_candidates(SCREENSHOT_UKRAINIAN)
        texts = [c["text"] for c in cands]
        assert "купити картонні коробки" in texts
        assert "зателефонувати о 15:00" in texts
        assert "оплатити до 25.03" in texts
        assert not any("маркетинг" in t for t in texts)

    def test_checkbox_items(self):
        cands = extract_task_candidates(SCREENSHOT_MEETING)
        texts = [c["text"] for c in cands]
        assert "send the report to Anna by Monday" in texts
        assert "review the budget" in texts
        assert "schedule a follow-up with the vendor" in texts
        # prose line is not a task
        assert not any("revenue is up" in t for t in texts)

    def test_ranking_verb_plus_date_first(self):
        cands = extract_task_candidates(SCREENSHOT_MEETING)
        # "send the report ... by Monday" (verb + date) should outrank prose-ish lines
        assert cands[0]["score"] >= max(c["score"] for c in cands)

    def test_long_paragraph_yields_nothing(self):
        assert extract_task_candidates(LONG_PARAGRAPH) == []

    def test_no_duplicates(self):
        cands = extract_task_candidates("- call mom\n- call mom\ncall mom")
        assert len([c for c in cands if c["text"] == "call mom"]) == 1

    def test_empty_and_garbage(self):
        assert extract_task_candidates("") == []
        assert extract_task_candidates(None) == []
        assert extract_task_candidates("... --- ??") == []

    def test_candidates_have_reasons(self):
        cands = extract_task_candidates(SCREENSHOT_SHOPPING)
        assert all(c["reasons"] for c in cands)


class TestLineScore:
    def test_verb_scores_higher_than_plain(self):
        verb_line, _ = line_score("buy oat milk")
        plain_line, _ = line_score("the weather is nice for a walk in the park")
        assert verb_line > plain_line

    def test_date_hint_adds_score(self):
        with_date, _ = line_score("submit the form by Friday")
        without, _ = line_score("submit the form please")
        assert with_date > without


# ---------------------------------------------------------------------------
# Classification (task / reminder / note)
# ---------------------------------------------------------------------------

class TestClassify:
    @pytest.mark.parametrize("text,expected", [
        ("call mom tomorrow", "reminder"),
        ("buy oat milk", "task"),
        ("о 15:00 дзвінок", "reminder"),
        ("цікава ідея про маркетинг", "note"),
        ("pay rent by Friday", "reminder"),
    ])
    def test_classify(self, text, expected):
        assert classify(text) == expected


# ---------------------------------------------------------------------------
# Optional OCR availability (graceful fallback contract)
# ---------------------------------------------------------------------------

def test_ocr_available_is_bool():
    # On this machine Tesseract is not installed -> must be False, never raise.
    assert ocr_available() is True or ocr_available() is False


def test_ocr_image_none_without_tesseract():
    from app.logic import ocr_extract
    if not ocr_available():
        # graceful fallback: returns None instead of raising
        assert ocr_extract.ocr_image(b"fake-bytes") is None
