"""Mindcatch FastAPI backend (localhost). Serves the PWA frontend and the
JSON API. All data lives in a local SQLite file."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import (create_item, export_all, get_conn, get_item, init_db,
                 list_items, update_status)
from .logic import date_parser, digest, ocr_extract, triage

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Mindcatch", version="0.1.0")


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


class MoveIn(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.post("/api/capture")
def capture(body: CaptureIn, db=DbDep):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "text is empty")
    type_ = ocr_extract.classify(text)
    parsed = date_parser.parse(text)
    remind_at = parsed.remind_at if parsed else None
    due_date = parsed.due_date if parsed else None
    item = create_item(db, text, type_, remind_at, due_date=due_date)
    return item


@app.get("/api/items")
def items(status: str | None = None, db=DbDep):
    if status and status not in triage.STATUSES:
        raise HTTPException(400, f"unknown status: {status}")
    return list_items(db, status)


@app.get("/api/inbox")
def inbox(db=DbDep):
    return list_items(db, "inbox")


@app.get("/api/today")
def today(db=DbDep):
    return list_items(db, "today")


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


@app.get("/api/export")
def export(db=DbDep):
    return Response(export_all(db), media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=mindcatch-export.json"})


# Frontend last, so /api routes take precedence
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
