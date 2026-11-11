"""Tests for avatar embedding helpers."""

from __future__ import annotations

import pytest

from src.avatar import AvatarError, sniff_mime, to_data_uri


def test_sniff_common_image_types():
    assert sniff_mime(b"\xff\xd8\xff\xe0rest") == "image/jpeg"
    assert sniff_mime(b"\x89PNG\r\n\x1a\nrest") == "image/png"
    assert sniff_mime(b"GIF89arest") == "image/gif"
    assert sniff_mime(b"RIFF0000WEBPrest") == "image/webp"
    assert sniff_mime(b"not an image") is None


def test_to_data_uri_embeds_mime_and_payload():
    uri = to_data_uri(b"\x89PNG\r\n\x1a\nabcdef")

    assert uri.startswith("data:image/png;base64,")
    assert "abcdef" not in uri


def test_to_data_uri_rejects_empty_and_unknown_payloads():
    with pytest.raises(AvatarError):
        to_data_uri(b"")
    with pytest.raises(AvatarError):
        to_data_uri(b"plain text")
