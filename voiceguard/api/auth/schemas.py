from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

# security-review.md F-27: no max_length meant an arbitrarily large password
# string was accepted (bcrypt silently truncates past 72 bytes, so this
# wasn't a live hash-cost DoS, but it was unbounded request-body memory
# allocation and inconsistent error messaging). 128 is comfortably above any
# real password while still being a hard cap.


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)
    display_name: str

    @field_validator("display_name")
    @classmethod
    def _display_name_len(cls, v: str) -> str:
        stripped = v.strip()
        if not (1 <= len(stripped) <= 64):
            raise ValueError("display_name must be 1-64 characters")
        return stripped


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class LogoutRequest(BaseModel):
    pass


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)
