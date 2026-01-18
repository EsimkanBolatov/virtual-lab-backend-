# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt

from database import engine, get_db, Base
from models import User, Lab, Result, Progress

# Database кестелерін құру
Base.metadata.create_all(bind=engine)

# Security
SECRET_KEY = "your-secret-key-change-in-production-12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 сағат

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# FastAPI app
app = FastAPI(title="Virtual Lab API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== PYDANTIC SCHEMAS ====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "student"
    grade: Optional[int] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    grade: Optional[int]
    
    class Config:
        from_attributes = True

class LabCreate(BaseModel):
    title_kk: str
    title_ru: str
    subject: str
    grade: int
    lab_number: Optional[str] = None
    description_kk: Optional[str] = None
    description_ru: Optional[str] = None
    difficulty: Optional[str] = "medium"
    estimated_time: Optional[int] = 20
    config: Optional[Dict] = {}

class LabResponse(BaseModel):
    id: int
    title_kk: str
    title_ru: str
    subject: str
    grade: int
    lab_number: Optional[str]
    difficulty: Optional[str]
    estimated_time: Optional[int]
    
    class Config:
        from_attributes = True

class ResultCreate(BaseModel):
    lab_id: int
    answers: Dict[str, Any]
    time_spent: int

class ResultResponse(BaseModel):
    id: int
    lab_id: int
    score: Optional[float]
    status: str
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# ==================== HELPER FUNCTIONS ====================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

def calculate_score(answers: Dict[str, Any]) -> float:
    """Нәтижені есептеу функциясы"""
    correct = sum(1 for a in answers.values() if a.get("correct", False))
    total = len(answers)
    return round((correct / total * 100) if total > 0 else 0, 2)

# ==================== ROUTES: AUTH ====================

@app.post("/auth/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Жаңа пайдаланушыны тіркеу"""
    # Email тексеру
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Жаңа пайдаланушы құру
    db_user = User(
        email=user.email,
        password_hash=get_password_hash(user.password),
        full_name=user.full_name,
        role=user.role,
        grade=user.grade
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Жүйеге кіру"""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Ағымдағы пайдаланушы деректерін алу"""
    return current_user

# ==================== ROUTES: LABS ====================

@app.post("/labs", response_model=LabResponse)
def create_lab(lab: LabCreate, db: Session = Depends(get_db)):
    """Жаңа лабораторияны құру"""
    db_lab = Lab(**lab.dict())
    db.add(db_lab)
    db.commit()
    db.refresh(db_lab)
    return db_lab

@app.get("/labs", response_model=List[LabResponse])
def get_labs(
    grade: Optional[int] = None,
    subject: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Лабораторияларды алу (фильтрлермен)"""
    query = db.query(Lab)
    if grade:
        query = query.filter(Lab.grade == grade)
    if subject:
        query = query.filter(Lab.subject == subject)
    return query.all()

@app.get("/labs/{lab_id}")
def get_lab(lab_id: int, db: Session = Depends(get_db)):
    """Жеке лабораторияны алу"""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    return lab

# ==================== ROUTES: RESULTS ====================

@app.post("/results", response_model=ResultResponse)
def create_result(
    result_data: ResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Нәтижені сақтау"""
    score = calculate_score(result_data.answers)
    
    result = Result(
        user_id=current_user.id,
        lab_id=result_data.lab_id,
        answers=result_data.answers,
        time_spent=result_data.time_spent,
        score=score,
        status="completed",
        completed_at=datetime.utcnow()
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result

@app.get("/results/my", response_model=List[ResultResponse])
def get_my_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Менің нәтижелерім"""
    return db.query(Result).filter(Result.user_id == current_user.id).all()

# ==================== ROOT ====================

@app.get("/")
def root():
    return {
        "message": "Virtual Lab API",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)