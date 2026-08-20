from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration requests."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    current_level: str = "A1"
