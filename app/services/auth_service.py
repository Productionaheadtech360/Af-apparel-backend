"""Authentication service."""
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AccountSuspendedError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.core.redis import redis_delete, redis_get, redis_set
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.company import Company, CompanyUser
from app.models.user import User
from app.schemas.auth import LoginResponse, RegisterWholesaleRequest, TokenRefreshResponse
from app.models.wholesale import WholesaleApplication

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_TOKEN_EXPIRE_DAYS = 7


def _build_access_token_claims(user: User, membership: CompanyUser | None) -> dict:
    """Build extra JWT claims from user + company membership."""
    claims: dict = {"is_admin": user.is_admin}
    if membership:
        claims["company_id"] = str(membership.company_id)
        claims["company_role"] = membership.role
        if membership.company and membership.company.pricing_tier_id:
            claims["pricing_tier_id"] = str(membership.company.pricing_tier_id)
    return claims


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def login(self, email: str, password: str) -> LoginResponse:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedError("Your account is inactive")

        # Check company status for non-admin users
        membership: CompanyUser | None = None
        if not user.is_admin:
            mem_result = await self.db.execute(
                select(CompanyUser)
                .where(CompanyUser.user_id == user.id, CompanyUser.is_active == True)
                .limit(1)
            )
            membership = mem_result.scalar_one_or_none()
            if membership:
                await self.db.refresh(membership, ["company"])
                company: Company = membership.company
                if company.status == "suspended":
                    raise AccountSuspendedError()

        # Update last_login
        user.last_login = datetime.now(UTC)
        await self.db.flush()

        extra_claims = _build_access_token_claims(user, membership)
        access_token = create_access_token(str(user.id), extra_claims=extra_claims)
        refresh_token = create_refresh_token(str(user.id))

        # Store refresh token in Redis (7-day TTL)
        await redis_set(
            f"refresh:{user.id}",
            refresh_token,
            expire=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )

        return LoginResponse(access_token=access_token, token_type="bearer"), refresh_token

    async def logout(self, user_id: str, access_jti: str) -> None:
        """Blacklist the access token JTI and delete the refresh token."""
        await redis_set(f"blacklist:{access_jti}", "1", expire=15 * 60)
        await redis_delete(f"refresh:{user_id}")

    async def refresh_tokens(self, refresh_token: str) -> TokenRefreshResponse:
        """Validate refresh token, issue new access token."""
        from jose import JWTError

        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise UnauthorizedError("Invalid or expired refresh token")

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Wrong token type")

        user_id = payload.get("sub")
        stored = await redis_get(f"refresh:{user_id}")
        if stored != refresh_token:
            raise UnauthorizedError("Refresh token has been rotated or revoked")

        result = await self.db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        mem_result = await self.db.execute(
            select(CompanyUser)
            .where(CompanyUser.user_id == user.id, CompanyUser.is_active == True)
            .limit(1)
        )
        membership = mem_result.scalar_one_or_none()
        if membership:
            await self.db.refresh(membership, ["company"])

        extra_claims = _build_access_token_claims(user, membership)
        new_access_token = create_access_token(user_id, extra_claims=extra_claims)
        new_refresh_token = create_refresh_token(user_id)

        # Rotate refresh token (one-time use)
        await redis_set(
            f"refresh:{user_id}",
            new_refresh_token,
            expire=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )

        return TokenRefreshResponse(access_token=new_access_token), new_refresh_token

    async def register_wholesale(self, data: RegisterWholesaleRequest) -> WholesaleApplication:
        """Create a user account and wholesale application with 'pending' status."""
        # Check for duplicate email
        existing = await self.db.execute(select(User).where(User.email == data.email.lower()))
        if existing.scalar_one_or_none():
            raise ConflictError("An account with this email already exists")

        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            is_admin=False,
            is_active=True,
            email_verified=False,
        )
        self.db.add(user)
        await self.db.flush()

        application = WholesaleApplication(
            company_name=data.company_name,
            tax_id=data.tax_id,
            business_type=data.business_type,
            website=data.website,
            expected_monthly_volume=data.expected_monthly_volume,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email.lower(),
            phone=data.phone,
            status="pending",
        )
        self.db.add(application)
        await self.db.flush()

        return application

    async def send_password_reset(self, email: str) -> None:
        """Send a password reset email if the user exists. Always returns 200 to prevent enumeration."""
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            return  # Silently ignore — don't reveal email existence

        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_expires = datetime.now(UTC) + timedelta(hours=1)
        await self.db.flush()

        from app.tasks.email_tasks import send_password_reset_email
        send_password_reset_email.delay(str(user.id), token)

    async def reset_password(self, token: str, new_password: str) -> None:
        result = await self.db.execute(
            select(User).where(User.password_reset_token == token)
        )
        user = result.scalar_one_or_none()
        if not user or not user.password_reset_expires:
            raise ValidationError("Invalid or expired reset token")
        if user.password_reset_expires < datetime.now(UTC):
            raise ValidationError("Reset token has expired")

        user.hashed_password = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
