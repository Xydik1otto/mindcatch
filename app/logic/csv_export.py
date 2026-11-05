"""CSV export of all items — one-click data safety (opens in Excel/Sheets).

UTF-8 with BOM so Excel detects Cyrillic correctly without an import wizard.
"""

from __future__ import annotations

import csv
import io

COLUMNS = ("id", "type", "text", "status", "due_date", "remind_at",
           "tags", "estimate_minutes", "spent_minutes", "created_at", "updated_at")


def items_to_csv(items: list[dict]) -> str:
    """All items as CSV text (\\r\\n line endings, UTF-8 BOM prepended)."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(COLUMNS)
    for item in items:
        writer.writerow([item.get(col) if item.get(col) is not None else ""
                         for col in COLUMNS])
    return "﻿" + buf.getvalue()
