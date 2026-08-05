"""Category 8 — Hardcoded credentials scan.
Scans only git-tracked files (i.e. what .gitignore actually lets through)
for secret-shaped strings: API keys, private keys, JWT secrets, DB
connection strings with embedded passwords, AWS-style keys, generic
high-entropy "SECRET=" / "PASSWORD=" assignments. node_modules/ is
tracked in this repo (unusual, but confirmed via git status) so it's
included but capped in output volume.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "generic_api_key_assignment": re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
    "private_key_block": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    "jwt_secret_assignment": re.compile(r"(?i)JWT_SECRET\s*[:=]\s*['\"]?[A-Za-z0-9_\-+/=]{8,}['\"]?"),
    "db_url_with_password": re.compile(r"(?i)(postgres(?:ql)?|mysql|mongodb)(\+\w+)?://[^:\s'\"]+:[^@\s'\"]+@"),
    "generic_password_assignment": re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"\s]{6,}['\"]"),
    "generic_secret_assignment": re.compile(r"(?i)\bsecret\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"),
    "slack_token": re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
    "stripe_key": re.compile(r"sk_(live|test)_[0-9A-Za-z]{16,}"),
}

# Known-safe placeholder/example values that would otherwise false-positive.
ALLOWLIST_SUBSTRINGS = [
    "changeme", "example", "your-", "xxxxxxxx", "REPLACE_ME", "placeholder",
    "voiceguard:voiceguard@localhost", "voiceguard:voiceguard@postgres",  # docker-compose local-dev DB, not a real secret
    "dummy", "test-secret", "not-the-real-one", "wrong-secret",
    "attacker-guessed-secret", "changeme1",  # our own common-password list entry
]

EXCLUDE_DIR_PARTS = {".git", "dist", "build", "__pycache__", ".pytest_cache"}


def is_allowlisted(line: str) -> bool:
    low = line.lower()
    return any(s.lower() in low for s in ALLOWLIST_SUBSTRINGS)


def git_tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return [f for f in out.stdout.splitlines() if f.strip()]


def main() -> None:
    files = git_tracked_files()
    findings = []
    scanned = 0

    for rel_path in files:
        parts = Path(rel_path).parts
        if any(p in EXCLUDE_DIR_PARTS for p in parts):
            continue
        full = REPO_ROOT / rel_path
        if not full.is_file():
            continue
        try:
            size = full.stat().st_size
            if size > 2_000_000:  # skip huge binaries/bundles
                continue
            text = full.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        scanned += 1

        for line_no, line in enumerate(text.splitlines(), start=1):
            if is_allowlisted(line):
                continue
            for pat_name, pat in PATTERNS.items():
                m = pat.search(line)
                if m:
                    findings.append({
                        "file": rel_path,
                        "line": line_no,
                        "pattern": pat_name,
                        "excerpt": line.strip()[:160],
                    })

    print(f"Scanned {scanned} git-tracked files across {len(files)} listed. Findings: {len(findings)}")
    for f in findings[:100]:
        print(f"  {f['pattern']}: {f['file']}:{f['line']} -> {f['excerpt']}")

    out_path = REPO_ROOT / "automated_test" / "results" / "08_hardcoded_creds.json"
    out_path.write_text(json.dumps(findings, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
