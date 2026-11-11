"""Avatar sniffing and self-contained data-URI embedding."""

from __future__ import annotations

import base64
from pathlib import Path

MAX_AVATAR_BYTES = 3_000_000


class AvatarError(ValueError):
    """Raised when an avatar cannot be read or embedded."""


def sniff_mime(payload: bytes) -> str | None:
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if payload.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if payload.startswith(b"GIF87a") or payload.startswith(b"GIF89a"):
        return "image/gif"
    if payload.startswith(b"RIFF") and payload[8:12] == b"WEBP":
        return "image/webp"
    return None


def to_data_uri(payload: bytes | None) -> str:
    if not payload:
        raise AvatarError("avatar payload is empty")
    mime = sniff_mime(payload)
    if mime is None:
        raise AvatarError("avatar payload is not a supported image")
    return f"data:{mime};base64,{base64.b64encode(payload).decode('ascii')}"


def read_avatar_file(path: str | Path) -> str:
    target = Path(path)
    try:
        payload = target.read_bytes()
    except OSError as exc:
        raise AvatarError(f"could not read avatar file {target}: {exc}") from exc
    if len(payload) > MAX_AVATAR_BYTES:
        raise AvatarError(f"avatar file {target} is larger than {MAX_AVATAR_BYTES} bytes")
    return to_data_uri(payload)
