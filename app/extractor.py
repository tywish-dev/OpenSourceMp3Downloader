"""yt-dlp + ffmpeg extraction helpers."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

ALLOWED_BITRATES = {128, 192, 320}
MAX_DURATION_SECONDS = 45 * 60
YT_DLP_TIMEOUT_SECONDS = 180
INFO_TIMEOUT_SECONDS = 45

SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


class ExtractionError(RuntimeError):
    """Raised when metadata lookup or conversion fails."""


@dataclass(frozen=True)
class MediaInfo:
    title: str
    duration: float | None
    extractor: str | None
    webpage_url: str | None
    thumbnail: str | None


def sanitize_filename(title: str) -> str:
    cleaned = SAFE_FILENAME.sub("_", title).strip("._")
    cleaned = cleaned[:80] or "audio"
    return f"{cleaned}.mp3"


def _run_yt_dlp(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    command = ["yt-dlp", *args]
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExtractionError("The source took too long to respond.") from exc
    except FileNotFoundError as exc:
        raise ExtractionError("yt-dlp is not installed on this server.") from exc


def probe_media(url: str) -> MediaInfo:
    result = _run_yt_dlp(
        [
            "--no-playlist",
            "--skip-download",
            "--no-warnings",
            "--dump-single-json",
            "--socket-timeout",
            "20",
            url,
        ],
        timeout=INFO_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "Could not read that URL.").strip()
        raise ExtractionError(_public_error(message))

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ExtractionError("Could not parse media information.") from exc

    duration = payload.get("duration")
    try:
        duration_value = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_value = None

    if duration_value is not None and duration_value > MAX_DURATION_SECONDS:
        raise ExtractionError("That clip is longer than the 45-minute limit.")

    title = str(payload.get("title") or payload.get("id") or "audio")
    return MediaInfo(
        title=title,
        duration=duration_value,
        extractor=payload.get("extractor_key") or payload.get("extractor"),
        webpage_url=payload.get("webpage_url") or url,
        thumbnail=payload.get("thumbnail"),
    )


def extract_mp3(url: str, bitrate: int, workdir: Path) -> Path:
    if bitrate not in ALLOWED_BITRATES:
        raise ExtractionError("Choose 128, 192, or 320 kbps.")

    info = probe_media(url)
    output_template = str(workdir / "track.%(ext)s")
    result = _run_yt_dlp(
        [
            "--no-playlist",
            "--no-warnings",
            "--newline",
            "--socket-timeout",
            "20",
            "-f",
            "bestaudio/best",
            "-x",
            "--audio-format",
            "mp3",
            "--audio-quality",
            str(bitrate),
            "-o",
            output_template,
            url,
        ],
        timeout=YT_DLP_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "Conversion failed.").strip()
        raise ExtractionError(_public_error(message))

    produced = workdir / "track.mp3"
    if not produced.exists():
        matches = list(workdir.glob("track.*"))
        if not matches:
            raise ExtractionError("The converter finished without an audio file.")
        produced = matches[0]

    if produced.stat().st_size <= 0:
        raise ExtractionError("The converted file was empty.")

    named = workdir / sanitize_filename(info.title)
    if named != produced:
        produced.replace(named)
    return named


def temporary_workspace() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix="osmp3-")


def _public_error(raw: str) -> str:
    lowered = raw.lower()
    if "unsupported url" in lowered or "no video" in lowered:
        return "That site or URL is not supported."
    if "private" in lowered or "sign in" in lowered or "login" in lowered:
        return "That media is private or requires a login."
    if "403" in lowered or "unavailable" in lowered:
        return "The source refused the request."
    if "ffmpeg" in lowered:
        return "Audio conversion failed. ffmpeg may be missing."
    first_line = next((line.strip() for line in raw.splitlines() if line.strip()), "")
    if first_line and len(first_line) < 180:
        return first_line
    return "Could not extract audio from that URL."


def ffmpeg_available() -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            check=False,
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
