from __future__ import annotations

# Shared between the /predict endpoint (api/main.py) and the scan upload
# pipeline (api/scans/validation.py) so the two never drift out of sync.
ALLOWED_AUDIO_EXTENSIONS: frozenset[str] = frozenset({".wav", ".flac", ".mp3", ".m4a", ".ogg", ".aiff"})

# Best-effort extension -> acceptable declared Content-Type mapping, used to
# flag an obvious mismatch (e.g. a ".wav" upload declared as "text/html").
# Not exhaustive and not a substitute for real content sniffing (out of scope
# for this slice — see ScanUploadValidation in the design doc's virus-scan /
# future-hardening notes).
EXTENSION_MIME_HINTS: dict[str, frozenset[str]] = {
    ".wav": frozenset({"audio/wav", "audio/wave", "audio/x-wav", "audio/vnd.wave"}),
    ".flac": frozenset({"audio/flac", "audio/x-flac"}),
    ".mp3": frozenset({"audio/mpeg", "audio/mp3"}),
    ".m4a": frozenset({"audio/mp4", "audio/x-m4a", "audio/m4a", "audio/aac"}),
    ".ogg": frozenset({"audio/ogg", "application/ogg"}),
    ".aiff": frozenset({"audio/aiff", "audio/x-aiff"}),
}

# Clients frequently send a generic/absent Content-Type for raw file uploads
# (curl, fetch with a manually-built FormData, some browsers). Treat these as
# "no signal" rather than a mismatch to avoid rejecting legitimate uploads.
AMBIGUOUS_CONTENT_TYPES: frozenset[str] = frozenset({"application/octet-stream", ""})
