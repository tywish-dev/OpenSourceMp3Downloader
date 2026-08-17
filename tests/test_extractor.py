from pathlib import Path

import pytest

from app.extractor import ExtractionError, extract_mp3, sanitize_filename


def test_sanitize_filename_strips_junk():
    assert sanitize_filename("My Talk: Hello*World?") == "My_Talk__Hello_World.mp3"
    assert sanitize_filename("   ") == "audio.mp3"


def test_extract_rejects_bad_bitrate(tmp_path: Path):
    with pytest.raises(ExtractionError):
        extract_mp3("https://example.com/a", 96, tmp_path)
