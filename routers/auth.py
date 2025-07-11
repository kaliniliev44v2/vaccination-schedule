from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from models import Doctor
from database import get_db
from schemas import DoctorCreate, DoctorOut

import os

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Настройки
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# 🔐 Хеширане на пароли
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)


# 🎟️ Генериране на JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# 👤 Dependency: вземи текущия логнат лекар
async def get_current_doctor(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> Doctor:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невалидни идентификационни данни",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        doctor_id: int = payload.get("sub")
        if doctor_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(Doctor).where(Doctor.id == int(doctor_id)))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise credentials_exception
    return doctor


# 📥 Регистрация на лекар
@router.post("/register", response_model=DoctorOut)
async def register(doctor_data: DoctorCreate, db: AsyncSession = Depends(get_db)):
    hashed_pw = get_password_hash(doctor_data.password)
    new_doctor = Doctor(username=doctor_data.username, hashed_password=hashed_pw)
    db.add(new_doctor)
    try:
        await db.commit()
    except:
        raise HTTPException(status_code=400, detail="Потребителското име вече съществува")
    await db.refresh(new_doctor)
    return new_doctor


# 🔑 Логин
@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Doctor).where(Doctor.username == form_data.username))
    doctor = result.scalar_one_or_none()

    if not doctor or not verify_password(form_data.password, doctor.hashed_password):
        raise HTTPException(status_code=401, detail="Невалидно потребителско име или парола")

    access_token = create_access_token(data={"sub": str(doctor.id)})
    return {"access_token": access_token, "token_type": "bearer"}
