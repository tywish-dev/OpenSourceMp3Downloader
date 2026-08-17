"""HTTP API and optional bundled UI for the self-hosted MP3 extractor."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock
from typing import Deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from app.extractor import (
    ALLOWED_BITRATES,
    ExtractionError,
    extract_mp3,
    ffmpeg_available,
    probe_media,
    temporary_workspace,
)
from app.security import UnsafeURLError, validate_media_url

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
MAX_CONCURRENT_JOBS = int(os.environ.get("OSMP3_MAX_CONCURRENT", "2"))
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("OSMP3_RATE_LIMIT", "8"))


def _cors_origins() -> list[str]:
    raw = os.environ.get("OSMP3_CORS_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(
    title="Open Source MP3 Downloader",
    description="Self-hosted extractor. Download only media you have the right to copy.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    expose_headers=["Content-Disposition"],
)

_job_lock = Lock()
_active_jobs = 0
_rate_lock = Lock()
_hits: dict[str, Deque[float]] = defaultdict(deque)


class UrlPayload(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class DownloadPayload(UrlPayload):
    bitrate: int = 192


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(request: Request) -> None:
    ip = _client_ip(request)
    now = time.monotonic()
    with _rate_lock:
        bucket = _hits[ip]
        while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail="Slow down — too many requests from this address.",
            )
        bucket.append(now)


def _acquire_job() -> None:
    global _active_jobs
    with _job_lock:
        if _active_jobs >= MAX_CONCURRENT_JOBS:
            raise HTTPException(
                status_code=503,
                detail="The extractor is busy. Try again in a moment.",
            )
        _active_jobs += 1


def _release_job() -> None:
    global _active_jobs
    with _job_lock:
        _active_jobs = max(0, _active_jobs - 1)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "ffmpeg": ffmpeg_available(),
        "active_jobs": _active_jobs,
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.post("/api/info")
def media_info(payload: UrlPayload, request: Request) -> dict[str, object]:
    _enforce_rate_limit(request)
    try:
        url = validate_media_url(payload.url)
        info = probe_media(url)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "title": info.title,
        "duration": info.duration,
        "extractor": info.extractor,
        "webpage_url": info.webpage_url,
        "thumbnail": info.thumbnail,
    }


@app.post("/api/download")
def download(payload: DownloadPayload, request: Request) -> FileResponse:
    _enforce_rate_limit(request)
    if payload.bitrate not in ALLOWED_BITRATES:
        raise HTTPException(status_code=400, detail="Choose 128, 192, or 320 kbps.")

    try:
        url = validate_media_url(payload.url)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _acquire_job()
    workspace = temporary_workspace()
    try:
        mp3_path = extract_mp3(url, payload.bitrate, Path(workspace.name))
    except ExtractionError as exc:
        workspace.cleanup()
        _release_job()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        workspace.cleanup()
        _release_job()
        raise

    return FileResponse(
        path=mp3_path,
        media_type="audio/mpeg",
        filename=mp3_path.name,
        background=BackgroundTask(_cleanup_workspace, workspace),
    )


def _cleanup_workspace(workspace) -> None:
    workspace.cleanup()
    _release_job()


app.mount("/", StaticFiles(directory=WEB_DIR), name="web")
