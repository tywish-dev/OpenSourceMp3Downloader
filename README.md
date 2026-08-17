# OSMP3 — Open Source MP3 Downloader

A self-hosted website that turns a **public media URL you have the right to copy** into an MP3. Paste a link, inspect the title and length, download the audio. The file is streamed back to the browser and then deleted.

This is not a search engine, not a song locker, and not a hosted ripping service for other people’s catalogs. You run it. You are responsible for what you fetch.

## How it works

```text
Browser  →  FastAPI  →  yt-dlp (find audio)  →  ffmpeg (write MP3)  →  download
                         \__ metadata only on Inspect
```

1. The UI is a static page served by FastAPI (`app/static`).
2. `POST /api/info` asks yt-dlp for title, duration, and thumbnail. Nothing is saved.
3. `POST /api/download` extracts best audio, transcodes to 128 / 192 / 320 kbps MP3, and streams the file.
4. A background task deletes the temp directory. Render’s filesystem is ephemeral anyway; we do not keep a media library.

Guards in front of yt-dlp:

- Only `http` / `https`
- No userinfo in the URL
- Localhost, private, link-local, metadata, and `.internal` / `.lan` hosts are blocked (SSRF)
- 45-minute duration cap
- In-memory rate limit and a small concurrent-job cap

## Quick start (Docker)

You need Docker. ffmpeg is bundled in the image.

```bash
docker build -t osmp3 .
docker run --rm -p 10000:10000 -e PORT=10000 osmp3
```

Open [http://localhost:10000](http://localhost:10000).

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
# ffmpeg must be on your PATH for real conversions
uvicorn app.main:app --reload --host 0.0.0.0 --port 10000
```

```bash
pytest
```

## Deploy on Render

`render.yaml` describes a free Docker web service that binds to `0.0.0.0:$PORT` and health-checks `/health`.

1. Merge this repo (or the PR) to GitHub
2. Open the Blueprint: [Apply on Render](https://dashboard.render.com/blueprint/new?repo=https://github.com/tywish-dev/OpenSourceMp3Downloader)
3. Apply the Blueprint and wait for the deploy

Free instances spin down after idle time and have a tight memory budget. If large conversions die, bump the plan and keep `OSMP3_MAX_CONCURRENT=1`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | set by Render | HTTP port |
| `OSMP3_MAX_CONCURRENT` | `2` locally, `1` on Render | Parallel conversions |
| `OSMP3_RATE_LIMIT` | `8` locally, `6` on Render | Requests per IP per minute |

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Website |
| `GET` | `/health` | Liveness (`ok`, `ffmpeg`, `active_jobs`) |
| `POST` | `/api/info` | `{ "url": "https://..." }` → title, duration, thumbnail |
| `POST` | `/api/download` | `{ "url": "...", "bitrate": 192 }` → `audio/mpeg` file |

## Legal

OSMP3 is a tool. Use it only with recordings you own, Creative Commons / public-domain media, or other material you have permission to copy. Circumventing DRM or downloading copyrighted works you do not have rights to can be illegal. The MIT license includes no warranty.

## Stack

- Python 3.12, FastAPI, uvicorn
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) + ffmpeg
- Vanilla HTML / CSS / JS (no frontend build)
- Docker on Render

## License

[MIT](LICENSE) © 2026 Samet Yılmaz
