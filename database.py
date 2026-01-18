# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite үшін database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./virtual_lab.db"

# Engine құру (check_same_thread=False - SQLite үшін керек)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Session құру
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class моделдер үшін
Base = declarative_base()

# Database session алу функциясы
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()