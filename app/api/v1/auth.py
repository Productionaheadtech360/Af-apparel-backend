# backend/app/api/v1/auth.py
"""Auth API router."""
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings

from app.core.database import get_db
from app.core.security import get_token_jti
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterWholesaleRequest,
    ResetPasswordRequest,
    TokenRefreshResponse,
)
from app.services.auth_service import AuthService
from app.schemas.wholesale import WholesaleApplicationOut

router = APIRouter()

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days


@router.post("/register-wholesale", response_model=WholesaleApplicationOut, status_code=201)
async def register_wholesale(
    data: RegisterWholesaleRequest,
    db: AsyncSession = Depends(get_db),
) -> WholesaleApplicationOut:
    """Submit a wholesale registration application."""
    service = AuthService(db)
    application = await service.register_wholesale(data)
    return WholesaleApplicationOut.model_validate(application)


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Authenticate and return an access token. Sets httpOnly refresh cookie."""
    service = AuthService(db)
    login_response, refresh_token = await service.login(data.email, data.password)

    # Cross-origin deployments (Vercel → Railway) require SameSite=none + Secure.
    # Fall back to configured values for local dev.
    _prod = settings.APP_ENV == "production"
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=True if _prod else settings.COOKIE_SECURE,
        samesite="none" if _prod else settings.COOKIE_SAMESITE,  # type: ignore[arg-type]
        path="/api/v1/refresh",
        domain=settings.COOKIE_DOMAIN,
    )
    return login_response


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Blacklist access token and clear refresh cookie."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        jti = get_token_jti(token)
        user_id = getattr(request.state, "user_id", None)
        if user_id and jti:
            service = AuthService(db)
            await service.logout(user_id, jti)

    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path="/api/v1/refresh",
        secure=settings.COOKIE_SECURE,
    )

@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenRefreshResponse:
    """Issue a new access token using the httpOnly refresh cookie."""
    from app.core.exceptions import UnauthorizedError

    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise UnauthorizedError("Refresh token not found")

    service = AuthService(db)
    token_response, new_refresh_token = await service.refresh_tokens(refresh_token)

    _prod = settings.APP_ENV == "production"
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=new_refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=True if _prod else settings.COOKIE_SECURE,
        samesite="none" if _prod else settings.COOKIE_SAMESITE,  # type: ignore[arg-type]
        path="/api/v1/refresh",
        domain=settings.COOKIE_DOMAIN,
    )
    return token_response


@router.post("/forgot-password", status_code=204)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Send password reset email (always returns 204 to prevent enumeration)."""
    service = AuthService(db)
    await service.send_password_reset(data.email)


@router.post("/reset-password", status_code=204)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = AuthService(db)
    await service.reset_password(data.token, data.new_password)
