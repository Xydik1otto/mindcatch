"""Mindcatch FastAPI backend (localhost). Serves the PWA frontend and the
JSON API. All data lives in a local SQLite file."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import (all_time_logs, create_item, export_all, get_conn, get_item,
                 init_db, list_items, search_items, start_timer, stop_timer,
                 timer_state, update_fields, update_status)
from .logic import (csv_export, date_parser, digest, focus_stats, ics_export,
                    markdown, ocr_extract, recurring, review, tags,
                    task_export, time_tracker, triage)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Mindcatch", version="1.0.0")


def get_db():
    conn = get_conn()
    try:
        init_db(conn)
        yield conn
    finally:
        conn.close()


DbDep = Depends(get_db)


class CaptureIn(BaseModel):
    text: str
    tags: list[str] | None = None


class TagsIn(BaseModel):
    tags: list[str] | str = []


class MoveIn(BaseModel):
    status: str


class RecurrenceIn(BaseModel):
    recurrence: str | None  # None | daily | weekly


class BodyIn(BaseModel):
    body: str


class EstimateIn(BaseModel):
    minutes: int | None


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.post("/api/capture")
def capture(body: CaptureIn, db=DbDep):
    return _capture(body, db)


@app.post("/api/quick")
def quick_capture(body: CaptureIn, db=DbDep):
    """Headless capture for curl / launchers / shortcuts — same pipeline, no UI.

    Example: curl -s http://localhost:8000/api/quick \\
      -H 'Content-Type: application/json' -d '{"text":"подзвонити мамі завтра 15:00"}'
    """
    return _capture(body, db)


def _capture(body: CaptureIn, db) -> dict:
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "text is empty")
    clean_text, hashtag_tags = tags.extract_hashtags(text)
    type_ = ocr_extract.classify(clean_text)
    parsed = date_parser.parse(clean_text)
    remind_at = parsed.remind_at if parsed else None
    due_date = parsed.due_date if parsed else None
    merged = tags.normalize((body.tags or []) + hashtag_tags)
    item = create_item(db, clean_text, type_, remind_at, due_date=due_date,
                       tags=tags.join_tags(merged))
    return item


@app.put("/api/items/{item_id}/tags")
def set_tags(item_id: int, body: TagsIn, db=DbDep):
    """Replace the tag list (empty list clears)."""
    if get_item(db, item_id) is None:
        raise HTTPException(404, "item not found")
    return update_fields(db, item_id, tags=tags.join_tags(body.tags))


@app.get("/api/tags")
def tag_suggestions(db=DbDep):
    """History hints: distinct tags with usage counts, most-used first."""
    return tags.suggest(list_items(db))


@app.get("/api/items")
def items(status: str | None = None, tag: str | None = None, db=DbDep):
    if status and status not in triage.STATUSES:
        raise HTTPException(400, f"unknown status: {status}")
    result = list_items(db, status)
    if tag:
        result = [i for i in result if tags.matches(i, tag)]
    return result


@app.get("/api/inbox")
def inbox(db=DbDep):
    return list_items(db, "inbox")


@app.get("/api/today")
def today(db=DbDep):
    return list_items(db, "today")


@app.get("/api/search")
def search(q: str = "", db=DbDep):
    """Full-text search (substring, case-insensitive) over title + note body."""
    return search_items(db, q)


@app.get("/api/archive")
def archive(db=DbDep):
    """Done items, newest first — the archive of completed work."""
    return list(reversed(list_items(db, "done")))


@app.get("/api/digest")
def daily_digest(db=DbDep):
    """'Сьогодні: N задач, M нагадувань' for the Today view + notifications."""
    items = list_items(db)
    counts = digest.digest_counts(items)
    return {**counts, "due_today": digest.due_today(items)}


@app.post("/api/items/{item_id}/move")
def move_item(item_id: int, body: MoveIn, db=DbDep):
    item = get_item(db, item_id)
    if not item:
        raise HTTPException(404, "item not found")
    try:
        updated = triage.move(item, body.status)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return update_status(db, item_id, updated["status"])


@app.put("/api/items/{item_id}/body")
def set_body(item_id: int, body: BodyIn, db=DbDep):
    """Full note text (markdown)."""
    if get_item(db, item_id) is None:
        raise HTTPException(404, "item not found")
    return update_fields(db, item_id, body=body.body)


@app.post("/api/md/preview")
def md_preview(body: BodyIn):
    """Server-rendered markdown preview for the note editor."""
    return {"html": markdown.markdown_to_html(body.body)}


@app.post("/api/items/{item_id}/recurrence")
def set_recurrence(item_id: int, body: RecurrenceIn, db=DbDep):
    """Set recurrence: None | daily | weekly | every:N | weekdays."""
    item = get_item(db, item_id)
    if not item:
        raise HTTPException(404, "item not found")
    try:
        rec = recurring.validate(body.recurrence)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return update_fields(db, item_id, recurrence=rec)


@app.post("/api/items/{item_id}/complete")
def complete_item(item_id: int, db=DbDep):
    """Mark done; recurring items immediately spawn their next occurrence."""
    item = get_item(db, item_id)
    if not item:
        raise HTTPException(404, "item not found")
    updated = update_status(db, item_id, "done")
    nxt = recurring.spawn_next(item)
    if nxt:
        spawned = create_item(db, nxt["text"], nxt["type"], nxt["remind_at"],
                              status=nxt["status"], due_date=nxt["due_date"])
        db.execute("UPDATE items SET recurrence = ? WHERE id = ?",
                   (nxt["recurrence"], spawned["id"]))
        db.commit()
        spawned = get_item(db, spawned["id"])
    else:
        spawned = None
    return {"completed": updated, "next": spawned}


@app.post("/api/items/{item_id}/estimate")
def set_estimate(item_id: int, body: EstimateIn, db=DbDep):
    """Planned minutes for the task."""
    if get_item(db, item_id) is None:
        raise HTTPException(404, "item not found")
    try:
        minutes = time_tracker.validate_estimate(body.minutes)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return update_fields(db, item_id, estimate_minutes=minutes)


@app.post("/api/items/{item_id}/timer/start")
def timer_start(item_id: int, db=DbDep):
    if get_item(db, item_id) is None:
        raise HTTPException(404, "item not found")
    try:
        return start_timer(db, item_id)
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.post("/api/items/{item_id}/timer/stop")
def timer_stop(item_id: int, db=DbDep):
    try:
        return stop_timer(db, item_id)
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.get("/api/items/{item_id}/timer")
def timer_get(item_id: int, db=DbDep):
    if get_item(db, item_id) is None:
        raise HTTPException(404, "item not found")
    return timer_state(db, item_id)


@app.post("/api/ocr")
async def ocr(file: UploadFile = File(...)):
    """Extract task candidates from a screenshot.

    If Tesseract/pytesseract is not installed the API answers 200 with
    ocr_available=false so the UI can fall back to manual input gracefully.
    """
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if not ocr_extract.ocr_available():
        return JSONResponse({
            "ocr_available": False,
            "message": "Tesseract не встановлений — введіть текст вручну.",
            "candidates": [],
        })
    text = ocr_extract.ocr_image(data)
    if text is None:
        return JSONResponse({
            "ocr_available": False,
            "message": "OCR не вдався — введіть текст вручну.",
            "candidates": [],
        })
    return {
        "ocr_available": True,
        "raw_text": text,
        "candidates": ocr_extract.extract_task_candidates(text),
    }


@app.get("/api/ocr-status")
def ocr_status():
    return {"ocr_available": ocr_extract.ocr_available()}


@app.get("/api/stats/focus")
def focus_stats_api(days: int = 7, db=DbDep):
    """Focus minutes per day (last N days) + SVG bar chart."""
    days = max(1, min(days, 90))
    bars = focus_stats.minutes_by_day(all_time_logs(db), days)
    return {
        "days": bars,
        "total_minutes": focus_stats.total_minutes(bars),
        "svg": focus_stats.bar_chart_svg(bars),
    }


@app.get("/api/review/weekly")
def weekly_review_api(db=DbDep):
    """Weekly review: what was done this week, what carried over."""
    return review.weekly_review(list_items(db))


@app.get("/api/export/calendar.ics")
def export_ics(db=DbDep):
    """All dated items as an iCalendar file for the user's calendar app."""
    ics = ics_export.items_to_ics(list_items(db))
    return Response(ics, media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition":
                             "attachment; filename=mindcatch.ics"})


@app.get("/api/export/todoist.md")
def export_todoist(db=DbDep):
    """Tasks as a Todoist-compatible Markdown checklist (paste into Todoist)."""
    md = task_export.to_todoist(list_items(db))
    return Response(md, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition":
                             "attachment; filename=mindcatch-todoist.md"})


@app.get("/api/export/markdown")
def export_markdown(db=DbDep):
    """All items grouped by status as a Markdown document."""
    md = task_export.to_markdown(list_items(db))
    return Response(md, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition":
                             "attachment; filename=mindcatch.md"})


@app.get("/api/export/items.csv")
def export_csv(db=DbDep):
    """All items as CSV (UTF-8 BOM) — opens in Excel/Sheets without a wizard."""
    csv_text = csv_export.items_to_csv(list_items(db))
    return Response(csv_text, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition":
                             "attachment; filename=mindcatch-items.csv"})


@app.get("/api/export")
def export(db=DbDep):
    return Response(export_all(db), media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=mindcatch-export.json"})


# Frontend last, so /api routes take precedence
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
