from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.core.responses import error_envelope

logger = logging.getLogger("voiceguard")


class BaseVoiceGuardError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, details: list[dict[str, str]] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


# ── 400 ──────────────────────────────────────────────────────────────────────
class ValidationError(BaseVoiceGuardError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "VALIDATION_ERROR"


class PasswordValidationError(ValidationError):
    code = "INVALID_PASSWORD"


class InvalidInputError(ValidationError):
    code = "VALIDATION_ERROR"


class UnsupportedFileTypeError(ValidationError):
    code = "UNSUPPORTED_FILE_TYPE"


class ExtensionMimeMismatchError(ValidationError):
    code = "EXTENSION_MIME_MISMATCH"


class EmptyFileError(ValidationError):
    code = "EMPTY_FILE"


class FileTooSmallError(ValidationError):
    code = "FILE_TOO_SMALL"


class FileTooLargeError(ValidationError):
    code = "FILE_TOO_LARGE"


# ── 401 ──────────────────────────────────────────────────────────────────────
class AuthenticationError(BaseVoiceGuardError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"


class InvalidCredentialsError(AuthenticationError):
    code = "INVALID_CREDENTIALS"


class InvalidTokenError(AuthenticationError):
    code = "INVALID_TOKEN"


class ExpiredTokenError(AuthenticationError):
    code = "INVALID_TOKEN"


class SessionExpiredError(AuthenticationError):
    code = "SESSION_EXPIRED"


# ── 403 ──────────────────────────────────────────────────────────────────────
class AuthorizationError(BaseVoiceGuardError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


class InsufficientPermissionsError(AuthorizationError):
    code = "FORBIDDEN"


class EmailNotVerifiedError(AuthorizationError):
    code = "EMAIL_NOT_VERIFIED"


# ── 404 ──────────────────────────────────────────────────────────────────────
class NotFoundError(BaseVoiceGuardError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class UserNotFoundError(NotFoundError):
    code = "USER_NOT_FOUND"


class ScanNotFoundError(NotFoundError):
    code = "SCAN_NOT_FOUND"


# ── 409 ──────────────────────────────────────────────────────────────────────
class ConflictError(BaseVoiceGuardError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class EmailAlreadyExistsError(ConflictError):
    code = "EMAIL_ALREADY_EXISTS"


class DuplicateUploadError(ConflictError):
    code = "DUPLICATE_UPLOAD"


# ── 422 ──────────────────────────────────────────────────────────────────────
class BusinessLogicError(BaseVoiceGuardError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "BUSINESS_LOGIC_ERROR"


class DeletionPendingError(BusinessLogicError):
    code = "DELETION_PENDING"


class DeletionNotScheduledError(BusinessLogicError):
    code = "DELETION_NOT_SCHEDULED"


class InvalidScanStateError(BusinessLogicError):
    code = "INVALID_SCAN_STATE"


# ── 429 ──────────────────────────────────────────────────────────────────────
class RateLimitError(BaseVoiceGuardError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, message: str, *, retry_after_s: int) -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s


# ── 500 / 503 ────────────────────────────────────────────────────────────────
class InternalError(BaseVoiceGuardError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "INTERNAL_ERROR"


class DatabaseError(InternalError):
    code = "INTERNAL_ERROR"


class ServiceUnavailableError(BaseVoiceGuardError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "SERVICE_UNAVAILABLE"


class UploadFailedError(ServiceUnavailableError):
    """A transport/storage-layer failure while receiving the file — distinct
    from ValidationError subclasses, which mean the file itself was rejected."""

    code = "UPLOAD_FAILED"


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or str(uuid.uuid4())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BaseVoiceGuardError)
    async def handle_voiceguard_error(request: Request, exc: BaseVoiceGuardError):
        from fastapi.responses import JSONResponse

        request_id = _request_id(request)
        logger.warning(
            "business_error", extra={"code": exc.code, "path": request.url.path, "request_id": request_id}
        )
        headers = {}
        if isinstance(exc, RateLimitError):
            headers["Retry-After"] = str(exc.retry_after_s)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope(code=exc.code, message=exc.message, request_id=request_id, details=exc.details),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError):
        from fastapi.responses import JSONResponse

        request_id = _request_id(request)
        details = [
            {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_envelope(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                request_id=request_id,
                details=details,
            ),
        )

    @app.exception_handler(PydanticValidationError)
    async def handle_pydantic_validation_error(request: Request, exc: PydanticValidationError):
        from fastapi.responses import JSONResponse

        request_id = _request_id(request)
        details = [{"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]} for err in exc.errors()]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_envelope(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                request_id=request_id,
                details=details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        from fastapi.responses import JSONResponse

        request_id = _request_id(request)
        code = {404: "NOT_FOUND", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 405: "NOT_FOUND"}.get(
            exc.status_code, "ERROR"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope(
                code=code, message=str(exc.detail), request_id=request_id
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception):
        from fastapi.responses import JSONResponse

        request_id = _request_id(request)
        logger.error(
            "unhandled_exception",
            exc_info=exc,
            extra={"path": request.url.path, "request_id": request_id},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_envelope(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred. Please try again.",
                request_id=request_id,
            ),
        )
