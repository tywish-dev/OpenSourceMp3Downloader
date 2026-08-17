# syntax=docker/dockerfile:1
FROM python:3.12-bookworm AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip wheel --no-deps -w /wheels -r requirements.txt

FROM python:3.12-slim-bookworm AS runner
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -r -u 1001 appuser
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY app ./app
RUN chown -R appuser:appuser /app
USER appuser
ENV PORT=10000 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 10000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
