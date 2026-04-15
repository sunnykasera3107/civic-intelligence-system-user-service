import os
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.services.database import schema
from app.services.database.conn import SessionLocal, Base
from app.services.database.conn import engine
from app.services.database.models import User
from app.services.email.sender import send_email

from app.utils.helper import Helper

Base.metadata.create_all(bind=engine)
router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
async def register(user: schema.UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="Email already registered"
        )

    # Hash password
    hashed_password = Helper.hash_password(user.password)

    # Create user
    new_user = User(
        name=user.name,
        email=user.email,
        password=hashed_password,
        phone=user.phone
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    await email_verification(new_user)

    return {
        "message": "Account registered successfully"
    }


@router.post("/login", response_model=schema.Token)
def login(user: schema.UserLogin, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()

    # Check if email not exists
    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid email address")
    
    # Verify password
    if not Helper.verify_password(user.password, existing_user.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    # Create Token
    access_token = Helper.jwt_tokenize({
        "id": existing_user.id,
        "email": existing_user.email
    })

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/forget", response_model=schema.Token)
async def forget(
    user: schema.ForgotPasswordRequest, 
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.email == user.email).first()

    # Check if email not exists
    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid email address")
    
    # Create Token
    access_token = Helper.jwt_tokenize({
        "type": "reset",
        "email": existing_user.email
    })

    await send_email(
        subject="Reset Password",
        recipients=[os.getenv("FROM_MAIL")],
        body_arg={
            "name": existing_user.name,
            "reset_link": f"{
                os.getenv("BASE_URL")
            }/verify_email?token={access_token}&type=bearer"
        },
        template="app/services/email/templates/forget_password.html"
    )

    return {
        "message": "Reset password link sent on your email account."
    }


@router.post("/reset")
def reset(user: schema.ResetPasswordRequest, db: Session = Depends(get_db)):
    data = Helper.jwt_detokenize(user.access_token)

    # Check if token is reset type token
    if data.get("type") != "reset":
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check if token is valid or expired
    if data.get("exp") < time.time():
        raise HTTPException(status_code=401, detail="Token expired")

    existing_user = db.query(User).filter(
        User.email == data.get("email")
    ).first()

    # Check if email not exists
    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid email address")
    
    existing_user.password = Helper.hash_password(user.new_password)
    db.commit()

    return {
        "message": "Password updated successfully."
    }


@router.post("/account", response_model=schema.UserResponse)
def account(user: schema.Token, db: Session = Depends(get_db)):
    data = Helper.jwt_detokenize(user.access_token)

    # Check if token is not reset type token
    if "type" in data and data.get("type") != "reset":
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check if token is valid or expired
    if data.get("exp") < time.time():
        raise HTTPException(status_code=401, detail="Token expired")

    existing_user = db.query(User).filter(
        User.email == data.get("email")
    ).first()

    # Check if email not exists
    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid email address")
    
    return existing_user


@router.get("/verify_email")
async def verify_email(access_token: str, db: Session = Depends(get_db)):
    data = Helper.jwt_detokenize(access_token)
    existing_user = db.query(User).filter(
        User.email == data.get("email")
    ).first()

    # Check if token is not reset type token
    if not existing_user or ("type" in data and data.get("type") != "reset"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check if token is valid or expired
    if data.get("exp") < time.time():
        await email_verification(existing_user)
        raise HTTPException(status_code=401, detail="Token expired")
    
    if existing_user.email_verified == True:
        raise HTTPException(
            status_code=401, 
            detail="Email is already verified"
        )
    
    existing_user.email_verified = True
    db.commit()

    return {
        "message": "Your email address is verified."
    }


async def email_verification(user):
    access_token = Helper.jwt_tokenize({
        "id": user.id,
        "email": user.email,
        "exp": (datetime.now() + timedelta(minutes=(60*24)))
    })

    await send_email(
        subject="Welcome to civic intelligent portal",
        recipients=[os.getenv("FROM_MAIL")],
        body_arg={
            "name": user.name,
            "verification_link": f"{
                os.getenv("BASE_URL")
            }/verify_email?access_token={access_token}"
        },
        template="registration.html"
    )