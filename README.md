# OSMP3 — Open Source MP3 Downloader

A self-hosted website that turns a **public media URL you have the right to copy** into an MP3. Paste a link, inspect the title and length, download the audio. The file is streamed back to the browser and then deleted.

This is not a search engine, not a song locker, and not a hosted ripping service for other people’s catalogs. You run it. You are responsible for what you fetch.

## How it is published

The UI is a static site. The extractor is a Docker API. They can run together locally, or split:

```text
Vercel (public/ + /api proxy)  --HTTPS-->  Northflank Docker API (yt-dlp + ffmpeg)
```

**Frontend: Vercel.** Static files, no sleep, global CDN.

**Backend: [Koyeb](https://www.koyeb.com/) free instance.** This is the default recommendation. Render’s free web service sleeps after 15 minutes and can take a long time to boot (a minute is common; several minutes happens). Koyeb’s free instance stays warm for an hour of idle time, then wakes in about **1–5 seconds**.

If you need a process that **never** sleeps, use [Northflank](https://northflank.com/) Sandbox (always-on, 2 free services, card required to activate). Google Cloud Run is also strong (fast cold starts, long request timeouts) but needs a GCP billing account.

Do not put yt-dlp + ffmpeg on Vercel. The converter is a container job, not a static page.

## How it works

```text
Browser  →  FastAPI  →  yt-dlp (find audio)  →  ffmpeg (write MP3)  →  download
                         \__ metadata only on Inspect
```

1. The UI lives in `public/` (Vercel, or bundled with the API for self-host).
2. `POST /api/info` asks yt-dlp for title, duration, and thumbnail. Nothing is saved.
3. `POST /api/download` extracts best audio, transcodes to 128 / 192 / 320 kbps MP3, and streams the file.
4. A background task deletes the temp directory. We do not keep a media library.

Guards in front of yt-dlp:

- Only `http` / `https`
- No userinfo in the URL
- Localhost, private, link-local, metadata, and `.internal` / `.lan` hosts are blocked (SSRF)
- 45-minute duration cap
- In-memory rate limit and a small concurrent-job cap

## Quick start (Docker, UI + API together)

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

## Deploy the frontend on Vercel

Import this GitHub repo (`main`). Static files are in `public/`; Vercel Functions in `api/` proxy to Northflank.

In Vercel **Settings → General → Build & Development**, leave **Output Directory empty** (do not set `web`). A custom output folder publishes only HTML and drops `/api`.

1. [vercel.com/new](https://vercel.com/new) → this repository, production branch `main`
2. **Settings → Environment Variables** → `OSMP3_API_BASE` = Northflank public URL, **no trailing slash**  
   Example: `https://http--osmp3--yourproject--user.code.run`  
   Enable **Production** (and Preview if you want)
3. **Deployments → Redeploy** (do not skip the build)

After that, Inspect on the Vercel site hits `/api` on Vercel, which forwards to Northflank. You can also paste the Northflank URL into the page’s API field.

## Deploy the API on Koyeb

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?type=git&builder=dockerfile&repository=github.com/tywish-dev/OpenSourceMp3Downloader&branch=main&name=osmp3&instance_type=free&env%5BOSMP3_MAX_CONCURRENT%5D=1&env%5BOSMP3_RATE_LIMIT%5D=6&env%5BOSMP3_CORS_ORIGINS%5D=*)

Or by hand:

1. Create a Koyeb account and connect GitHub
2. New App → this repo → **Dockerfile** builder → **Free** instance (Frankfurt or Washington)
3. Health check path: `/health`
4. Set env:

| Variable | Suggested | Meaning |
| --- | --- | --- |
| `PORT` | set by Koyeb | HTTP port (`0.0.0.0:$PORT`) |
| `OSMP3_MAX_CONCURRENT` | `1` | Parallel conversions |
| `OSMP3_RATE_LIMIT` | `6` | Requests per IP per minute |
| `OSMP3_CORS_ORIGINS` | `*` then lock it | Allowed browser origins |

After the Vercel URL exists, change `OSMP3_CORS_ORIGINS` from `*` to that origin, for example `https://osmp3.vercel.app`.

Free Koyeb is 0.1 vCPU / 512 MB, so conversions can be slow. Idle sleep is **1 hour**, then a **1–5 s** wake — not a multi-minute Render boot.

### Always-on alternative: Northflank

[Northflank Sandbox](https://northflank.com/) keeps two services running with no sleep. Deploy the same Dockerfile, expose HTTP, health path `/health`, same env vars. A card is required to activate the sandbox; it is not billed while you stay on the free services.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Website (when UI is bundled) |
| `GET` | `/health` | Liveness (`ok`, `ffmpeg`, `active_jobs`) |
| `POST` | `/api/info` | `{ "url": "https://..." }` → title, duration, thumbnail |
| `POST` | `/api/download` | `{ "url": "...", "bitrate": 192 }` → `audio/mpeg` file |

## Legal

OSMP3 is a tool. Use it only with recordings you own, Creative Commons / public-domain media, or other material you have permission to copy. Circumventing DRM or downloading copyrighted works you do not have rights to can be illegal. The MIT license includes no warranty.

## Stack

- Python 3.12, FastAPI, uvicorn
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) + ffmpeg
- Vanilla HTML / CSS / JS in `public/` (Vercel Functions in `api/`)
- Docker API on Koyeb (or any container host)

## License

[MIT](LICENSE) © 2026 Samet Yılmaz
