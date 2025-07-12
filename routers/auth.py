from fastapi import APIRouter, Depends, Form, HTTPException, Request, status 
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
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
templates = Jinja2Templates(directory="templates")

# Настройки
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
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
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# 👤 Dependency: вземи текущия логнат лекар (за API)
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


# 👤 Dependency: вземи текущия логнат лекар (за Web)
async def get_current_doctor_web(request: Request, db: AsyncSession = Depends(get_db)) -> Doctor:
    """Web версия на get_current_doctor - проверява за token в cookie"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/auth/login"})
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        doctor_id: int = payload.get("sub")
        if doctor_id is None:
            raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/auth/login"})
    except JWTError:
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/auth/login"})

    result = await db.execute(select(Doctor).where(Doctor.id == int(doctor_id)))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/auth/login"})
    return doctor


# 📥 Регистрация на лекар (API)
@router.post("/register", response_model=DoctorOut)
async def register(doctor_data: DoctorCreate, db: AsyncSession = Depends(get_db)):
    # Проверка дали потребителското име вече съществува
    result = await db.execute(select(Doctor).where(Doctor.username == doctor_data.username))
    existing_doctor = result.scalar_one_or_none()
    if existing_doctor:
        raise HTTPException(status_code=400, detail="Потребителското име вече съществува")
    
    hashed_pw = get_password_hash(doctor_data.password)
    new_doctor = Doctor(username=doctor_data.username, hashed_password=hashed_pw)
    db.add(new_doctor)
    await db.commit()
    await db.refresh(new_doctor)
    return new_doctor


# 🔑 Логин (API)
@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Doctor).where(Doctor.username == form_data.username))
    doctor = result.scalar_one_or_none()

    if not doctor or not verify_password(form_data.password, doctor.hashed_password):
        raise HTTPException(status_code=401, detail="Невалидно потребителско име или парола")

    access_token = create_access_token(data={"sub": str(doctor.id)})
    return {"access_token": access_token, "token_type": "bearer"}


# 🌐 WEB ROUTES


# 📄 Login форма
@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# 📄 Register форма  
@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


# 🔑 Web Login
@router.post("/login")
async def login_web(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Doctor).where(Doctor.username == username))
    doctor = result.scalar_one_or_none()

    if not doctor or not verify_password(password, doctor.hashed_password):
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Невалидно потребителско име или парола"}
        )

    # Създаваме JWT token
    access_token = create_access_token(data={"sub": str(doctor.id)})
    
    # Пренасочваме към dashboard с token в cookie
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response


# 📥 Web Register
@router.post("/register")
async def register_web(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    # Проверка дали потребителското име вече съществува
    result = await db.execute(select(Doctor).where(Doctor.username == username))
    existing_doctor = result.scalar_one_or_none()
    if existing_doctor:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Потребителското име вече съществува"}
        )
    
    try:
        hashed_pw = get_password_hash(password)
        new_doctor = Doctor(username=username, hashed_password=hashed_pw)
        db.add(new_doctor)
        await db.commit()
        
        # Автоматично влизане след регистрация
        access_token = create_access_token(data={"sub": str(new_doctor.id)})
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="access_token", 
            value=access_token, 
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax"
        )
        return response
    except Exception as e:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": f"Грешка при регистрация: {str(e)}"}
        )


# 🚪 Logout
@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response


# GET версия на logout за директно извикване
@router.get("/logout")
async def logout_get():
    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response