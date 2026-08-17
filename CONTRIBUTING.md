# Contributing

Thanks for helping with OSMP3. Small, reviewable changes are easier to land than sweeping rewrites.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

You need `ffmpeg` on your PATH only for real extractions. Unit tests mock yt-dlp.

## What belongs here

- Fixes and tests for URL safety, duration limits, or conversion failures
- UI accessibility and layout fixes
- Docs that make self-hosting clearer

Please do **not** add:

- A public search index of copyrighted music
- Features whose main purpose is to bypass DRM or site logins
- Ads, trackers, or accounts unless we have a clear design for them

## Pull requests

1. Branch from `main`
2. Keep the change focused
3. Add or update tests when you touch behavior
4. Run `pytest`

By contributing you agree your work is licensed under the MIT License already in this repository.
