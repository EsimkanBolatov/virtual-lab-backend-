# backend/models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, JSON
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # student, teacher, admin
    full_name = Column(String, nullable=False)
    grade = Column(Integer, nullable=True)  # 5-10 сынып
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Lab(Base):
    __tablename__ = "labs"
    
    id = Column(Integer, primary_key=True, index=True)
    title_kk = Column(String, nullable=False)
    title_ru = Column(String, nullable=False)
    subject = Column(String, nullable=False)  # chemistry, biology, nature
    grade = Column(Integer, nullable=False)
    lab_number = Column(String)
    description_kk = Column(String)
    description_ru = Column(String)
    difficulty = Column(String)  # easy, medium, hard
    estimated_time = Column(Integer)  # минутпен
    config = Column(JSON)  # лабораторияның конфигурациясы
    created_at = Column(DateTime, default=datetime.utcnow)

class Result(Base):
    __tablename__ = "results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    lab_id = Column(Integer, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    score = Column(Float)  # 0-100
    time_spent = Column(Integer)  # секундпен
    attempts = Column(Integer, default=1)
    status = Column(String, default="in_progress")  # in_progress, completed, failed
    answers = Column(JSON)  # қадамдар бойынша жауаптар

class Progress(Base):
    __tablename__ = "progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    lab_id = Column(Integer, nullable=False)
    current_step = Column(Integer, default=1)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    is_completed = Column(Boolean, default=False)