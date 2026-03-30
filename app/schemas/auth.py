"""Auth Pydantic schemas."""
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterWholesaleRequest(BaseModel):
    # Company info
    company_name: str = Field(..., min_length=2, max_length=255)
    tax_id: str | None = Field(None, max_length=100)
    business_type: str = Field(..., min_length=2, max_length=100)
    website: str | None = Field(None, max_length=500)
    expected_monthly_volume: str | None = None

    # Contact info
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(None, max_length=50)
    password: str = Field(..., min_length=8)


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
