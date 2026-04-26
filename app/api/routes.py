import os
import time
from datetime import datetime, timedelta, timezone
import logging
import json

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from redis import Redis

from app.services.database import schema
from app.services.database.conn import SessionLocal, Base
from app.services.database.conn import engine
from app.services.database.models import User
from app.services.email.sender import send_email

from app.utils.helper import Helper

Base.metadata.create_all(bind=engine)
router = APIRouter()
_logger = logging.Logger(__name__)
rd = Redis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    decode_responses=True
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
async def register(
    user: schema.UserCreate, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
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

    _logger.info(new_user)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    await email_service(
        new_user, 
        background_tasks, 
        subject="Email Verification", 
        type="verify"
    )

    return {
        "message": "Account registered successfully"
    }



@router.post("/register-officer")
async def register(
    user: schema.OfficerCreate,
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):  
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="Email already registered"
        )
    

    coords = ",".join([str(user.latitude), str(user.longitude)])
    location = Helper.get_address_from_coordinates(coords)

    # Hash password
    user.password = Helper.hash_password(user.password)
    user = user.model_dump()
    user['role'] = 2
    user['city'] = location.get("city")
   

    # Create user
    new_user = User(**user)

    _logger.info(new_user)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    await email_service(
        new_user, 
        background_tasks, 
        subject="Email Verification", 
        type="verify"
    )

    return {
        "message": "Account registered successfully"
    }


@router.post("/login")
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
        "token_type": "bearer",
        "user": {
            "id": existing_user.id,
            "email": existing_user.email,
            "name": existing_user.name,
            "phone": existing_user.phone,
            "email_verified": existing_user.email_verified,
            "phone_verified": existing_user.phone_verified
        }
    }


@router.post("/forget")
async def forget(
    user: schema.ForgotPasswordRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.email == user.email).first()

    # Check if email not exists
    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid email address")
    
    # Create Token
    reset_token = Helper.jwt_tokenize({
        "type": "reset",
        "email": existing_user.email
    })

    await email_service(
        existing_user, 
        background_tasks, 
        type="reset", 
        min=15, 
        subject="Reset Password",
        body_arg={
            "name": existing_user.name,
            "reset_link": f"{
                os.path.join(os.getenv("BASE_URL"), "reset_password")
            }/{reset_token}"
        },
        template="forget_password.html"
    )

    return {
        "message": "Reset password link sent on your email account."
    }


@router.post("/reset")
def reset(
    user: schema.ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    data = Helper.jwt_detokenize(user.reset_token)

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

    key = f"user:{data.get("id")}"
    if data.get("id") and rd.exists(key):        
        user = json.loads(rd.getex(key))
        return user

    existing_user = db.query(User).filter(
        User.email == data.get("email")
    ).first()

    # Check if email not exists
    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid email address")
    
    key = f"user:{existing_user.id}"
    user_data = schema.UserResponse.model_validate(existing_user).model_dump_json()
    rd.setex(key, timedelta(minutes=int(os.getenv("TOKEN_EXPIRE"))), user_data)
    return existing_user


@router.post("/nearest_officer")
async def get_user(
    complaint_detail: schema.OfficerRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.id == complaint_detail.complainerId
    ).first()

    await email_service(
        existing_user, 
        background_tasks, 
        type="complaint", 
        min=15, 
        subject="Your complaint registered",
        body_arg={
            "name": existing_user.name,
            "complaint_link": f"{
                os.path.join(os.getenv("BASE_URL"), "complaint")
            }/{complaint_detail.complaintId}",
            "contact_details": "A relavent officer will attand it soon."
        },
        template="complaint.html"
    )

    existing_users = db.query(User).filter(
        User.city == complaint_detail.city,
        User.departmentId == complaint_detail.departmentId,
        User.role == 2
    ).all()
    coord1 = (complaint_detail.latitude, complaint_detail.longitude)
    
    for user in existing_users:
        coord2 = (user.latitude, user.longitude)
        distance = Helper.get_distance_between(coord1, coord2)
        if user.arearange > distance:
            # await email_service(
            #     user, 
            #     background_tasks, 
            #     type="complaint", 
            #     min=15, 
            #     subject="New complaint registered",
            #     body_arg={
            #         "name": user.name,
            #         "complaint_link": f"{
            #             os.path.join(os.getenv("BASE_URL"), "complaint")
            #         }/{complaint_detail.complaintId}",
            #         "contact_details": f"Contact to {existing_user.name}<br>On {existing_user.phone} and {existing_user.email}"
            #     },
            #     template="complaint.html"
            # )
            return user
    raise HTTPException(
        status_code=404, 
        detail="Related officer not found."
    )

@router.post("/get_user", response_model=schema.UserResponse)
def get_user(user: schema.UserByID, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        User.id == user.id
    ).first()

    # Check if email not exists
    if not existing_user:
        raise HTTPException(
            status_code=401, 
            detail="User not found with this id"
        )
    
    return existing_user


@router.get("/verify_email/{access_token}")
async def verify_email(
    access_token: str, 
    db: Session = Depends(get_db)
):
    data = Helper.jwt_detokenize(access_token)
    existing_user = db.query(User).filter(
        User.email == data.get("email")
    ).first()
    print(not existing_user ,
        ("type" in data and data.get("type") != "verify"),
        data.get("exp") < time.time())
    if (
        not existing_user 
        or 
        ("type" in data and data.get("type") != "verify")
        or
        data.get("exp") < time.time()
    ):
        raise HTTPException(
            status_code=401, 
            detail=f"Invalid token. Login and click on verify email for new token."
        )
    
    existing_user.email_verified = True
    db.commit()

    return {
        "message": "Email is verified"
    }


@router.get("/send_verification_email/{id}")
async def send_verification_email(
    id: int, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.id == id
    ).first()

    if not existing_user and not id:
        raise HTTPException(
            status_code=401, 
            detail=f"User detail not found, login and try again."
        )

    await email_service(
        existing_user, 
        background_tasks, 
        subject="Email Verification", 
        type="verify"
    )

    return {
        "message": "Reset email sent on your email address.",
    }


async def email_service(
    user, 
    background_tasks: BackgroundTasks, 
    min: int = 1440, 
    type: str = "bearer", 
    subject: str = "Welcome!",
    template: str = "registration.html",
    body_arg: dict = None
):
    if not body_arg:
        access_token = Helper.jwt_tokenize({
            "id": user.id,
            "email": user.email,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=min),
            "type": type
        })
        body_arg = {
            "name": user.name, 
            "verification_link": f"{
                os.path.join(os.getenv("BASE_URL"), "verify_email")
            }/{access_token}",
        }

    background_tasks.add_task(
        send_email,
        subject=subject,
        recipients=[user.email],
        body_arg=body_arg,
        template=template
    )
