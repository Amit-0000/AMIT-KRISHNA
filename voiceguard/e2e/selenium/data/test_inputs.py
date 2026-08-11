"""Invalid-input fixtures for form-validation coverage.

Identical to voiceguard/e2e/appium/data/test_inputs.py — same app, same real
rules from frontend/src/lib/validation.ts (emailSchema,
passwordSchema/PASSWORD_REQUIREMENTS, displayNameSchema), copied rather than
re-derived.
"""
from __future__ import annotations

INVALID_EMAILS = [
    "not-an-email",
    "missing-domain@",
    "@missing-local.com",
]

# Each violates exactly one PASSWORD_REQUIREMENTS rule from validation.ts.
WEAK_PASSWORDS = {
    "too_short": "Ab1!",
    "no_uppercase": "lowercase1!",
    "no_lowercase": "UPPERCASE1!",
    "no_digit": "NoDigitsHere!",
    "no_special": "NoSpecial123",
}

INVALID_DISPLAY_NAMES = {
    "disallowed_chars": "Bad@Name!",
    "too_long": "A" * 65,
}

MISMATCHED_PASSWORD = "DoesNotMatch!1"

WRONG_LOGIN_CREDENTIALS = {
    "email": "nobody-selenium@example.com",
    "password": "WrongPassword!1",
}
