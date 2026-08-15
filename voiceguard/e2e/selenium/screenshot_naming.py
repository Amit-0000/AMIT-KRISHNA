"""Shared screenshot-filename helper for the Selenium suite.

conftest.py's failure-screenshot hook (which writes the file) and
build_html_report.py's screenshot-link lookup (which checks the file exists)
must derive byte-identical filenames from the same nodeid, so this is the one
place that logic lives.
"""
from __future__ import annotations

import hashlib
import re

# ext4 (the GitHub Actions runner's filesystem, and most local Linux/macOS
# setups) caps a filename component at 255 bytes. Confirmed live: a
# 2026-08-11 CI run crashed build_html_report.py with
# OSError: [Errno 36] File name too long while checking a screenshot path for
# a heavily-parametrized fuzz test (test_error_handling.py's malformed-id
# cases include a 300+ char string). Capped in UTF-8 *bytes*, not characters
# -- some parametrize ids in this suite contain multi-byte characters (e.g.
# a Japanese + emoji case in the same file), so a character-count cap alone
# wouldn't bound the encoded byte length.
MAX_STEM_BYTES = 150


def screenshot_stem(nodeid: str) -> str:
    # An allowlist regex, not the previous three literal .replace() calls:
    # this suite's own security tests (test_error_handling.py) parametrize
    # with real XSS/injection payloads like "<img src=x onerror=alert(1)>"
    # as part of their nodeid -- confirmed live, a 2026-08-15 CI run's
    # "Upload Selenium report" step hard-failed with "The path for one of
    # the files in artifact is not valid ... Contains the following
    # character: Less than <" for exactly such a case. Replacing only "/",
    # "::", and spaces left every other artifact-upload-invalid character
    # (<, >, ", :, |, *, ?, control chars, ...) to pass straight through
    # whenever a parametrize id happened to contain one.
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", nodeid)
    encoded = safe_name.encode("utf-8")
    if len(encoded) <= MAX_STEM_BYTES:
        return safe_name
    # Truncate, then hash the *full* untruncated name so two long nodeids
    # that only differ after the truncation point still get distinct files.
    digest = hashlib.sha1(encoded).hexdigest()[:8]
    truncated = encoded[:MAX_STEM_BYTES].decode("utf-8", errors="ignore")
    return f"{truncated}_{digest}"
