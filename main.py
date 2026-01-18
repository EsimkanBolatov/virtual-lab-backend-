# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, EmailStr

from database import engine, get_db, Base
from models import User, Experiment, ExperimentResult

# Базаны құру
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(title="Virtual Lab API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
SECRET_KEY = "a9f3cD8qL2X7VwR0HkN5S1ZyM4B6P8JQ"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "student"
    grade: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    grade: Optional[int]
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class ExperimentCreate(BaseModel):
    title: str
    subject: str
    grade: int
    description: str
    type: str
    difficulty: str
    duration_minutes: int

class ExperimentResponse(BaseModel):
    id: int
    title: str
    subject: str
    grade: int
    description: str
    type: str
    difficulty: str
    duration_minutes: int
    
    class Config:
        from_attributes = True

class ExperimentResultCreate(BaseModel):
    experiment_id: int
    score: int
    time_spent_seconds: int
    answers: dict

class ExperimentResultResponse(BaseModel):
    id: int
    user_id: int
    experiment_id: int
    score: int
    max_score: int
    time_spent_seconds: int
    completed_at: datetime
    
    class Config:
        from_attributes = True

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role,
        grade=user.grade
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Тексеру сәтсіз аяқталды",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

# Routes
@app.get("/")
def root():
    return {"message": "Virtual Lab API", "status": "active"}

@app.post("/auth/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = get_user_by_email(db, email=user.email)
        if db_user:
            raise HTTPException(status_code=400, detail="Email тіркелген")
        return create_user(db=db, user=user)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Тіркелу қатесі. Базаны қайта құрыңыз: rm virtual_lab.db"
        )

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email немесе құпия сөз қате",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/experiments", response_model=List[ExperimentResponse])
def get_experiments(
    grade: Optional[int] = None,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Experiment)
    if grade:
        query = query.filter(Experiment.grade == grade)
    if subject:
        query = query.filter(Experiment.subject == subject)
    return query.all()

@app.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Тәжірибе табылмады")
    return experiment

@app.post("/experiments", response_model=ExperimentResponse)
def create_experiment(
    experiment: ExperimentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Рұқсат жоқ")
    
    db_experiment = Experiment(**experiment.dict())
    db.add(db_experiment)
    db.commit()
    db.refresh(db_experiment)
    return db_experiment

@app.post("/results", response_model=ExperimentResultResponse)
def save_result(
    result: ExperimentResultCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_result = ExperimentResult(
        user_id=current_user.id,
        experiment_id=result.experiment_id,
        score=result.score,
        time_spent_seconds=result.time_spent_seconds,
        answers=result.answers
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

@app.get("/results/my", response_model=List[ExperimentResultResponse])
def get_my_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(ExperimentResult).filter(
        ExperimentResult.user_id == current_user.id
    ).all()

# Seed data (тәжірибелерді қосу)
@app.post("/seed")
def seed_experiments(db: Session = Depends(get_db)):
    experiments_data = [
        {
            "title": "Тұз қышқылының бейтараптану реакциясы",
            "subject": "chemistry",
            "grade": 7,
            "description": "HCl және NaOH бейтараптану реакциясы",
            "type": "lab",
            "difficulty": "easy",
            "duration_minutes": 20
        },
        {
            "title": "Ерітінділер концентрациясын есептеу",
            "subject": "chemistry",
            "grade": 8,
            "description": "Пайыздық және молярлық концентрацияларды дайындау",
            "type": "practical",
            "difficulty": "medium",
            "duration_minutes": 30
        },
        {
            "title": "Мыс пен мырыш иондарын тану",
            "subject": "chemistry",
            "grade": 10,
            "description": "Cu²⁺, Zn²⁺ иондарына сапалық реакциялар",
            "type": "lab",
            "difficulty": "medium",
            "duration_minutes": 25
        },
        {
            "title": "Митозды микроскопта зерттеу",
            "subject": "biology",
            "grade": 9,
            "description": "Пияз тамыр ұшындағы митоз фазалары",
            "type": "lab",
            "difficulty": "hard",
            "duration_minutes": 40
        }
    ]
    
    for exp_data in experiments_data:
        existing = db.query(Experiment).filter(Experiment.title == exp_data["title"]).first()
        if not existing:
            experiment = Experiment(**exp_data)
            db.add(experiment)
    
    db.commit()
    return {"message": "Тәжірибелер қосылды"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)