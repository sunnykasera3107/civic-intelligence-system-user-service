from datetime import datetime, timedelta
import logging
import os

import bcrypt
from fastapi import Depends, HTTPException
import jwt
from jwt.exceptions import InvalidTokenError
from geopy.geocoders import Nominatim
from geopy.distance import geodesic


logger = logging.getLogger(__name__)


class Helper:

    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def jwt_tokenize(data: dict) -> dict:
        to_encode = data.copy()
        if "data" not in data:
            expery_minutes = os.getenv("TOKEN_EXPIRE") if "type" not in data else os.getenv("RESET_EXPIRE")
            expiry = datetime.now() + timedelta(minutes=int(expery_minutes))
            to_encode.update({"exp": expiry})
        return jwt.encode(to_encode, os.getenv("SECRET_TOKEN"), algorithm=os.getenv("ALGORITHM"))
    
    @staticmethod
    def jwt_detokenize(token: str) -> dict:
        try:
            return jwt.decode(token, os.getenv("SECRET_TOKEN"), algorithms=[os.getenv("ALGORITHM")])
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    @staticmethod
    def get_address_from_coordinates(coords) -> dict:
        geolocator = Nominatim(user_agent="civic-issue-app")
        location = geolocator.reverse(f"{coords}", language="en", zoom=18)
        if not location:
            return {"error": "Address not found"}

        addr = location.raw.get("address", {})

        return {
            "address": location.address,
            "city": addr.get("city") or addr.get("town"),
            "state": addr.get("state"),
            "country": addr.get("country"),
            "postcode": addr.get("postcode")
        }
    
    @staticmethod
    def get_distance_between(coord1, coord2):
        return geodesic(coord1, coord2).km