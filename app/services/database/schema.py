from pydantic import BaseModel, EmailStr
from pydantic_extra_types.phone_numbers import PhoneNumber


class INPhone(PhoneNumber):
    default_region_code = 'IN'
    supported_regions = ['IN']
    phone_format = 'E164'


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: INPhone


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: PhoneNumber
    email_verified: bool
    phone_verified: bool

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    access_token: str
    new_password: str