from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import service as auth_service
from api.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from api.core.database import get_db
from api.core.deps import get_current_user_optional, require_authenticated
from api.core.exceptions import ServiceUnavailableError, SessionExpiredError
from api.core.middleware import client_ip
from api.core.rate_limit import (
    require_forgot_password_rate_limit,
    require_login_rate_limit,
    require_register_rate_limit,
    require_resend_verification_rate_limit,
    require_reset_password_rate_limit,
    require_verify_email_rate_limit,
)
from api.core.responses import success_envelope
from api.core.security import hash_ip
from api.user.models import User
from api.user.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_register_rate_limit)])
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register_user(
        db,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        ip_hash=hash_ip(client_ip(request)),
    )
    await db.commit()
    return success_envelope({"user": UserResponse.from_user(user).model_dump(mode="json")})


@router.post("/login", dependencies=[Depends(require_login_rate_limit)])
async def login(payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    user, access_token, refresh_token_raw = await auth_service.login_user(
        db,
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_hash=hash_ip(client_ip(request)),
    )
    await db.commit()
    auth_service.set_session_cookies(response, access_token=access_token, refresh_token_raw=refresh_token_raw)
    return success_envelope({"user": UserResponse.from_user(user).model_dump(mode="json")})


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    refresh_raw = request.cookies.get(auth_service.REFRESH_COOKIE_NAME)
    await auth_service.logout(db, refresh_token_raw=refresh_raw, user_id=user.id if user else None)
    await db.commit()
    auth_service.clear_session_cookies(response)
    return success_envelope({})


@router.post("/refresh")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_raw = request.cookies.get(auth_service.REFRESH_COOKIE_NAME)
    if not refresh_raw:
        raise SessionExpiredError("Session expired, please log in again")

    user, access_token, refresh_token_new = await auth_service.rotate_refresh_token(
        db,
        refresh_token_raw=refresh_raw,
        user_agent=request.headers.get("user-agent"),
        ip_hash=hash_ip(client_ip(request)),
    )
    await db.commit()
    auth_service.set_session_cookies(response, access_token=access_token, refresh_token_raw=refresh_token_new)
    return success_envelope({"user": UserResponse.from_user(user).model_dump(mode="json")})


@router.post("/verify-email", dependencies=[Depends(require_verify_email_rate_limit)])
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.verify_email(db, raw_token=payload.token)
    await db.commit()
    return success_envelope({"user": UserResponse.from_user(user).model_dump(mode="json")})


@router.post("/resend-verification", dependencies=[Depends(require_resend_verification_rate_limit)])
async def resend_verification(payload: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.resend_verification(db, email=payload.email)
    await db.commit()
    return success_envelope({})


@router.post("/forgot-password", dependencies=[Depends(require_forgot_password_rate_limit)])
async def forgot_password(payload: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    await auth_service.forgot_password(db, email=payload.email, ip_hash=hash_ip(client_ip(request)))
    await db.commit()
    return success_envelope({})


@router.post("/reset-password", dependencies=[Depends(require_reset_password_rate_limit)])
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.reset_password(db, raw_token=payload.token, new_password=payload.password)
    await db.commit()
    return success_envelope({})


@router.get("/oauth/{provider}")
async def oauth_initiate(provider: str):
    raise ServiceUnavailableError(
        f"OAuth login via {provider} is not yet configured on this deployment. "
        "This requires real provider client credentials (see BATCH_04 §10.6) — deferred to a future slice."
    )


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str):
    raise ServiceUnavailableError(f"OAuth login via {provider} is not yet configured on this deployment.")


@router.get("/me")
async def me(user: User = Depends(require_authenticated)):
    return success_envelope({"user": UserResponse.from_user(user).model_dump(mode="json")})
