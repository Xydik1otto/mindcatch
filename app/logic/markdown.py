"""Minimal safe Markdown → HTML for note bodies.

Escapes HTML first, then applies a small subset: headings, bold/italic,
inline code, links (http/https only), unordered/ordered lists, paragraphs
and line breaks. Enough for ADHD notes; XSS-safe by construction.
"""

from __future__ import annotations

import html
import re


def _inline(text: str) -> str:
    """Bold, italic, code, links inside an already-escaped string."""
    # links first: [text](https://…) — only http(s), no javascript:
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                  r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\s][^*]*)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def markdown_to_html(md: str) -> str:
    if not md or not md.strip():
        return ""
    src = html.escape(md.replace("\r\n", "\n"))
    out: list[str] = []
    list_open: str | None = None  # "ul" | "ol"

    def close_list():
        nonlocal list_open
        if list_open:
            out.append(f"</{list_open}>")
            list_open = None

    for line in src.split("\n"):
        stripped = line.strip()
        m = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if m:
            close_list()
            level = len(m[1])
            out.append(f"<h{level}>{_inline(m[2])}</h{level}>")
            continue
        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            if list_open != "ul":
                close_list()
                out.append("<ul>")
                list_open = "ul"
            out.append(f"<li>{_inline(m[1])}</li>")
            continue
        m = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if m:
            if list_open != "ol":
                close_list()
                out.append("<ol>")
                list_open = "ol"
            out.append(f"<li>{_inline(m[1])}</li>")
            continue
        close_list()
        if not stripped:
            continue
        out.append(f"<p>{_inline(stripped)}</p>")

    close_list()
    return "\n".join(out)
