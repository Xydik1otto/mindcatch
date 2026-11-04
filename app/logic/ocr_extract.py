"""OCR extraction heuristics: turn raw text (e.g. from a screenshot) into
task candidates.

Tesseract via pytesseract is OPTIONAL: if it is not installed, ``ocr_image``
returns None and the UI falls back to manual input. The heuristics below work
on any plain text, so they are fully testable without OCR.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Heuristic signals
# ---------------------------------------------------------------------------

ACTION_VERBS = {
    # English
    "call", "buy", "order", "email", "send", "pay", "fix", "write", "schedule",
    "book", "pick", "submit", "renew", "cancel", "reply", "finish", "check",
    "get", "take", "bring", "register", "apply", "return", "file", "clean",
    "visit", "meeting", "review", "sign", "print", "scan", "deposit",
    # Ukrainian
    "зателефонувати", "подзвонити", "купити", "замовити", "написати",
    "надіслати", "відправити", "оплатити", "заплатити", "зробити", "сходити",
    "забрати", "подати", "перевірити", "оформити", "записатися", "дозвонитися",
    "зустріч", "дзвінок", "сплатити", "викупити",
}

# Date / time-like fragments: weekdays, "today/tomorrow", dd.mm, hh:mm, "by Fri"
DATE_RE = re.compile(
    r"(\b(today|tomorrow|tonight|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun"
    r"|monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|сьогодні|завтра|пн|вт|ср|чт|пт|сб|нд)\b"
    r"|\b\d{1,2}[./-]\d{1,2}([./-]\d{2,4})?\b"
    r"|\b\d{1,2}:\d{2}\b"
    r"|\b(by|until|до)\s+\w{3,10}\b)",
    re.IGNORECASE,
)

_BULLET_RE = re.compile(r"^[\s\-\*•·>]*((?:\[\s?[xX]?\s?\])?)\s*")
_NOISE_RE = re.compile(r"^(https?://|www\.)", re.IGNORECASE)

# A line needs at least this score to become a candidate.
CANDIDATE_THRESHOLD = 2


def _clean_line(line: str) -> str:
    """Strip bullets, checkbox marks and surrounding whitespace."""
    return _BULLET_RE.sub("", line).strip()


def line_score(line: str) -> tuple[int, list[str]]:
    """Score a single line; higher = more task-like. Returns (score, reasons)."""
    text = _clean_line(line)
    reasons: list[str] = []
    if not text or _NOISE_RE.match(text):
        return 0, reasons
    score = 0
    first = text.split()[0].lower().strip(",.!?…")
    if first in ACTION_VERBS:
        score += 2
        reasons.append("starts with action verb")
    elif any(v in text.lower().split() for v in ACTION_VERBS):
        score += 1
        reasons.append("contains action verb")
    if DATE_RE.search(text):
        score += 2
        reasons.append("contains date/time hint")
    if len(text.split()) >= 2 and text.endswith((".", "!", "?")) is False and len(text) <= 120:
        score += 1  # short imperative-ish line
    if len(text) < 3 or len(text) > 200:
        return 0, reasons
    return score, reasons


def extract_task_candidates(text: str) -> list[dict]:
    """Extract lines that look like tasks/notes from free text.

    Returns a list of dicts: {text, score, reasons}. Lines scoring >=
    CANDIDATE_THRESHOLD are candidates; results are sorted by score desc.
    """
    candidates = []
    seen = set()
    for line in (text or "").splitlines():
        clean = _clean_line(line)
        if not clean or clean.lower() in seen:
            continue
        score, reasons = line_score(line)
        if score >= CANDIDATE_THRESHOLD:
            seen.add(clean.lower())
            candidates.append({"text": clean, "score": score, "reasons": reasons})
    candidates.sort(key=lambda c: -c["score"])
    return candidates


def looks_like_reminder(text: str) -> bool:
    """True if the text carries an explicit date/time hint -> reminder type."""
    return bool(DATE_RE.search(text or ""))


def looks_like_task(text: str) -> bool:
    """True if the text starts with or contains an action verb -> task type."""
    words = [w.lower().strip(",.!?…") for w in (text or "").split()]
    return bool(words and (words[0] in ACTION_VERBS or any(w in ACTION_VERBS for w in words)))


def classify(text: str) -> str:
    """One-tap capture classification: task | reminder | note."""
    if looks_like_reminder(text):
        return "reminder"
    if looks_like_task(text):
        return "task"
    return "note"


# ---------------------------------------------------------------------------
# Optional OCR (pytesseract + Tesseract binary)
# ---------------------------------------------------------------------------

def ocr_available() -> bool:
    """True only if pytesseract is importable AND the Tesseract binary works."""
    try:
        import pytesseract  # type: ignore
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_image(image_bytes: bytes) -> str | None:
    """OCR an image (png/jpg bytes). Returns extracted text or None when
    Tesseract is unavailable — the caller must fall back to manual input."""
    if not ocr_available():
        return None
    import io
    try:
        from PIL import Image  # type: ignore
        import pytesseract  # type: ignore
        img = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(img)
    except Exception:
        return None
