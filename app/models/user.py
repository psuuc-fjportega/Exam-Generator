import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class UserRole(str, enum.Enum):
    admin = "admin"
    teacher = "teacher"
    student = "student"

class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.student, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.active, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    subjects = relationship("Subject", back_populates="teacher", cascade="all, delete-orphan")
