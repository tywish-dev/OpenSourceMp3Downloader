from pathlib import Path

from fastapi.testclient import TestClient

from app.extractor import MediaInfo
from app.main import app

client = TestClient(app)


def test_home_page_renders():
    response = client.get("/")
    assert response.status_code == 200
    assert "OSMP3" in response.text
    assert "Extractor" in response.text


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "ffmpeg" in payload


def test_info_rejects_private_url():
    response = client.post("/api/info", json={"url": "http://127.0.0.1/secret"})
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"].lower() or "allowed" in response.json()["detail"].lower()


def test_download_rejects_bad_bitrate(monkeypatch):
    monkeypatch.setattr(
        "app.main.validate_media_url",
        lambda url: url,
    )
    response = client.post(
        "/api/download",
        json={"url": "https://example.com/a", "bitrate": 64},
    )
    assert response.status_code == 400


def test_info_returns_probe_payload(monkeypatch):
    monkeypatch.setattr(
        "app.main.validate_media_url",
        lambda url: url,
    )
    monkeypatch.setattr(
        "app.main.probe_media",
        lambda url: MediaInfo(
            title="Studio Session",
            duration=125,
            extractor="generic",
            webpage_url=url,
            thumbnail=None,
        ),
    )
    response = client.post("/api/info", json={"url": "https://example.com/talk"})
    assert response.status_code == 200
    assert response.json()["title"] == "Studio Session"
    assert response.json()["duration"] == 125


def test_download_streams_mp3(monkeypatch, tmp_path: Path):
    mp3 = tmp_path / "Studio_Session.mp3"
    mp3.write_bytes(b"ID3fake-mp3-bytes")

    class FakeWorkspace:
        def __init__(self, path: Path):
            self.name = str(path)

        def cleanup(self) -> None:
            return None

    monkeypatch.setattr("app.main.validate_media_url", lambda url: url)
    monkeypatch.setattr("app.main.temporary_workspace", lambda: FakeWorkspace(tmp_path))
    monkeypatch.setattr("app.main.extract_mp3", lambda url, bitrate, workdir: mp3)

    response = client.post(
        "/api/download",
        json={"url": "https://example.com/talk", "bitrate": 192},
    )
    assert response.status_code == 200
    assert response.content == b"ID3fake-mp3-bytes"
    assert "audio/mpeg" in response.headers["content-type"]
