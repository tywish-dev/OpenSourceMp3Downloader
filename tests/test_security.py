import socket

import pytest

from app.security import UnsafeURLError, validate_media_url


def _fake_public_dns(*_args, **_kwargs):
    return [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
    ]


def _fake_private_dns(*_args, **_kwargs):
    return [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 0)),
    ]


def test_rejects_empty():
    with pytest.raises(UnsafeURLError):
        validate_media_url("   ")


def test_rejects_non_http_schemes():
    with pytest.raises(UnsafeURLError):
        validate_media_url("file:///etc/passwd")
    with pytest.raises(UnsafeURLError):
        validate_media_url("javascript:alert(1)")


def test_rejects_localhost_and_loopback():
    with pytest.raises(UnsafeURLError):
        validate_media_url("http://localhost/audio.mp3")
    with pytest.raises(UnsafeURLError):
        validate_media_url("http://127.0.0.1/audio.mp3")
    with pytest.raises(UnsafeURLError):
        validate_media_url("http://[::1]/audio.mp3")


def test_rejects_private_and_metadata_ips():
    with pytest.raises(UnsafeURLError):
        validate_media_url("http://10.0.0.5/x")
    with pytest.raises(UnsafeURLError):
        validate_media_url("http://192.168.1.10/x")
    with pytest.raises(UnsafeURLError):
        validate_media_url("http://169.254.169.254/latest/meta-data")
    with pytest.raises(UnsafeURLError):
        validate_media_url("http://2130706433/")


def test_rejects_credentials_and_local_suffixes():
    with pytest.raises(UnsafeURLError):
        validate_media_url("https://user:pass@example.com/a")
    with pytest.raises(UnsafeURLError):
        validate_media_url("http://router.lan/audio")


def test_accepts_public_https(monkeypatch):
    monkeypatch.setattr("app.security.socket.getaddrinfo", _fake_public_dns)
    assert (
        validate_media_url("https://example.com/talk.mp4")
        == "https://example.com/talk.mp4"
    )


def test_rejects_hostname_that_resolves_privately(monkeypatch):
    monkeypatch.setattr("app.security.socket.getaddrinfo", _fake_private_dns)
    with pytest.raises(UnsafeURLError):
        validate_media_url("https://evil.example/x")
