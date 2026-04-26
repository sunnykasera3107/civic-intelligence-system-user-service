from sqlalchemy import Column, Integer, String, Boolean, Float, Text

from app.services.database.conn import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)
    departmentId = Column(Integer, nullable=True)
    arearange = Column(Integer, default=5, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    additional_info = Column(Text, nullable=True)
    role = Column(Integer, default=3, nullable=False)
    city = Column(String, nullable=True)