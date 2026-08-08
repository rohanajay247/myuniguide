"""
MyUniGuide — FastAPI wrapper around the retrieval pipeline.

The index is loaded once at startup and held in memory. At 573 KB there is no
database and no external state, which is why the whole thing ships as one
container.

The Gemini API key stays server-side and is never sent to the browser.

Run locally from the project root:
    uvicorn app.main:app --reload
"""

import os
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from answer import answer
from search import load_index

MAX_CHARS = 300

# Measured cost is about Rs 0.94 per question on gemini-3.6-flash, so 50 per
# day bounds the worst case at roughly Rs 47/day.
#
# Known limitation: these counters live in memory and reset whenever the
# container restarts. Deploy with --min-instances=1 --max-instances=1 so a
# single long-lived container holds a single counter.
PER_IP_PER_HOUR = 10
DAILY_TOTAL = 50

# Kill switch. Set DISABLED=1 in the environment and redeploy (or restart) to
# stop every Gemini call without taking the site down. No code change needed.
DISABLED = os.getenv("DISABLED", "").strip() not in ("", "0", "false", "False")

INDEX_HTML = Path(__file__).parent / "index.html"

app = FastAPI(title="MyUniGuide")

matrix, chunks = load_index()

_hits = defaultdict(deque)
_day = {"date": time.strftime("%Y-%m-%d"), "count": 0}


def check_limits(ip):
    """Rate limiting. Without this, the API key behind this endpoint is
    anyone's to spend."""
    today = time.strftime("%Y-%m-%d")
    if _day["date"] != today:
        _day.update(date=today, count=0)

    if _day["count"] >= DAILY_TOTAL:
        raise HTTPException(429, "Daily limit reached. Please try again tomorrow.")

    now = time.time()
    recent = _hits[ip]
    while recent and now - recent[0] > 3600:
        recent.popleft()

    if len(recent) >= PER_IP_PER_HOUR:
        raise HTTPException(429, "Too many requests. Please try again later.")

    recent.append(now)
    _day["count"] += 1

    # Surfaced in the Cloud Run logs so unusual traffic is visible.
    if _day["count"] in (25, 40, 49):
        print(f"NOTICE: {_day['count']} questions today, latest from {ip}")


class Question(BaseModel):
    question: str


@app.get("/", response_class=HTMLResponse)
def home():
    # Read per request rather than once at startup so edits show on refresh,
    # and no-store so the browser does not serve a stale copy.
    return HTMLResponse(
        INDEX_HTML.read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store"},
    )


@app.post("/ask")
def ask(body: Question, request: Request):
    if DISABLED:
        raise HTTPException(503, "This demo is temporarily paused.")

    text = body.question.strip()
    if not text:
        raise HTTPException(400, "Please enter a question.")
    if len(text) > MAX_CHARS:
        raise HTTPException(400, f"Question too long (max {MAX_CHARS} characters).")

    check_limits(request.client.host)

    reply, results = answer(text, matrix, chunks)

    return {
        "answer": reply,
        "sources": [
            {
                "citation": chunk["citation"],
                "authority": chunk["authority"],
                "text": chunk["text"][:400],
                "score": round(float(score), 3),
            }
            for score, chunk in results
        ],
    }


@app.get("/health")
def health():
    return {
        "status": "paused" if DISABLED else "ok",
        "chunks": len(chunks),
        "today": _day["count"],
    }