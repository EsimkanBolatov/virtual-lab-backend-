# backend/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    role = Column(String)  # student, teacher, admin
    grade = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    results = relationship("ExperimentResult", back_populates="user")

class Experiment(Base):
    __tablename__ = "experiments"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    subject = Column(String)  # chemistry, biology, science
    grade = Column(Integer)
    description = Column(String)
    type = Column(String)  # lab, practical
    difficulty = Column(String)  # easy, medium, hard
    duration_minutes = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    results = relationship("ExperimentResult", back_populates="experiment")

class ExperimentResult(Base):
    __tablename__ = "experiment_results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    experiment_id = Column(Integer, ForeignKey("experiments.id"))
    score = Column(Integer)
    max_score = Column(Integer, default=100)
    time_spent_seconds = Column(Integer)
    answers = Column(JSON)
    completed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    user = relationship("User", back_populates="results")
    experiment = relationship("Experiment", back_populates="results")