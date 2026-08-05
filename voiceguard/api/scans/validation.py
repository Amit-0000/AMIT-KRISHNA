from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from api.core.audio_formats import ALLOWED_AUDIO_EXTENSIONS, AMBIGUOUS_CONTENT_TYPES, EXTENSION_MIME_HINTS
from api.core.exceptions import (
    EmptyFileError,
    ExtensionMimeMismatchError,
    FileTooLargeError,
    FileTooSmallError,
    UnsupportedFileTypeError,
)

_SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9 _.\-()\[\]]{1,255}$")


@dataclass(frozen=True)
class ValidatedUpload:
    original_filename: str
    extension: str
    declared_mime_type: str | None


def sanitize_original_filename(filename: str | None) -> str:
    """Returns a filename safe to store as *display* metadata. Never used to
    build a filesystem path — the actual on-disk key is always
    f"{scan_id}{extension}" (see api.scans.service), which is what makes path
    traversal from a malicious filename impossible regardless of what this
    function returns."""
    name = Path((filename or "").strip()).name  # strips any directory components / ".." segments
    if not name or name in {".", ".."}:
        return "upload"
    if _SAFE_FILENAME_RE.match(name):
        return name
    suffix = Path(name).suffix
    return f"upload{suffix}" if suffix else "upload"


def validate_upload_request(filename: str | None, content_type: str | None) -> ValidatedUpload:
    """Pre-stream checks derivable from the multipart headers alone —
    extension whitelist and a best-effort extension/declared-mime match.
    Raises a ValidationError subclass on rejection."""
    extension = Path(filename or "").suffix.lower()
    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))
        raise UnsupportedFileTypeError(f"Unsupported file type {extension or '(none)'!r}. Allowed: {allowed}.")

    normalized_type = (content_type or "").split(";")[0].strip().lower()
    if normalized_type not in AMBIGUOUS_CONTENT_TYPES:
        hints = EXTENSION_MIME_HINTS.get(extension)
        if hints and normalized_type not in hints:
            raise ExtensionMimeMismatchError(
                f"File extension {extension!r} does not match declared content type {content_type!r}.",
                details=[{"field": "file", "message": "extension_mime_mismatch"}],
            )

    return ValidatedUpload(
        original_filename=sanitize_original_filename(filename),
        extension=extension,
        declared_mime_type=content_type,
    )


def validate_upload_size(size_bytes: int, *, min_bytes: int, max_bytes: int) -> None:
    """Post-stream checks — the final size is only known once every byte has
    been read. The max-size check is *also* enforced mid-stream (see
    api.scans.service.store_upload) so an oversized upload is aborted as soon
    as it crosses the limit instead of being fully buffered first; this is
    the belt-and-suspenders check for callers that already have the total."""
    if size_bytes <= 0:
        raise EmptyFileError("The uploaded file is empty.")
    if size_bytes < min_bytes:
        raise FileTooSmallError(f"File is too small (minimum {min_bytes} bytes).")
    if size_bytes > max_bytes:
        raise FileTooLargeError(f"File is too large (maximum {max_bytes} bytes).")
