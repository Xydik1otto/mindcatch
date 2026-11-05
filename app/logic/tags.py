"""Free-form tags/projects on items.

Tags live in a single comma-joined ``items.tags`` column. ``#hashtags``
typed in the capture line are extracted automatically (a ``#`` followed
by whitespace — e.g. a markdown heading — is not a tag). History hints
rank distinct tags by usage count so the UI can offer filter chips.
"""

from __future__ import annotations

import re

HASHTAG = re.compile(r"#(\w[\w-]*)", re.UNICODE)
MAX_TAGS = 10
MAX_LEN = 32


def extract_hashtags(text: str) -> tuple[str, list[str]]:
    """Split ``#tag`` markers out of the text: returns ``(clean_text, tags)``."""
    found: list[str] = []

    def _grab(m: re.Match) -> str:
        found.append(m.group(1))
        return ""

    clean = HASHTAG.sub(_grab, text)
    clean = re.sub(r"  +", " ", clean).strip(" ,")
    return clean, normalize(found)


def normalize(raw: list[str] | str | None) -> list[str]:
    """Lowercase, strip '#', dedupe; accepts a list or a comma/space string."""
    if raw is None:
        return []
    if isinstance(raw, str):
        parts: list[str] = []
        for chunk in raw.split(","):
            parts.extend(chunk.split())
        raw = parts
    out: list[str] = []
    for tag in raw:
        tag = re.sub(r"\s+", "-", tag.strip().lstrip("#").strip()).lower()
        if not tag or len(tag) > MAX_LEN or tag in out:
            continue
        out.append(tag)
        if len(out) >= MAX_TAGS:
            break
    return out


def join_tags(tags: list[str]) -> str:
    """Storage format for the items.tags column."""
    return ",".join(normalize(tags))


def parse_column(value: str | None) -> list[str]:
    if not value:
        return []
    return [t for t in value.split(",") if t]


def suggest(items: list[dict], limit: int = 12) -> list[dict]:
    """History hints: distinct tags with usage counts, most-used first."""
    counts: dict[str, int] = {}
    for item in items:
        for tag in parse_column(item.get("tags")):
            counts[tag] = counts.get(tag, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"tag": tag, "count": count} for tag, count in ranked[:limit]]


def matches(item: dict, tag: str) -> bool:
    return tag.lower() in parse_column(item.get("tags"))
