from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import date
from typing import List, Optional

from database import get_db
from models import Patient, Doctor, Vaccine, Immunization
from routers.auth import get_current_doctor_web_strict  # Използваме strict версията
from utils.schedule import calculate_age_in_months, required_mandatory_vaccines

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# Middleware функция за проверка на автентификация и redirect
async def check_auth_redirect(request: Request, db: AsyncSession = Depends(get_db)):
    """Проверява автентификацията и прави redirect към login ако е необходимо"""
    try:
        from routers.auth import get_current_doctor_web_strict
        doctor = await get_current_doctor_web_strict(request, db)
        return doctor
    except HTTPException:
        # Ако няма автентификация, redirect към login
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)


# 🏠 Dashboard - показва всички пациенти на лекаря
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    try:
        # Проверка на автентификацията
        doctor = await check_auth_redirect(request, db)
        if isinstance(doctor, RedirectResponse):
            return doctor
            
        result = await db.execute(select(Patient).where(Patient.doctor_id == doctor.id))
        patients = result.scalars().all()
        
        return templates.TemplateResponse(
            "dashboard.html", 
            {
                "request": request, 
                "patients": patients,
                "doctor": doctor
            }
        )
    except Exception as e:
        print(f"Dashboard error: {e}")
        return templates.TemplateResponse(
            "dashboard.html", 
            {
                "request": request, 
                "patients": [],
                "doctor": None,
                "error": "Грешка при зареждане на пациентите"
            }
        )


# 💉 Управление на ваксини
@router.get("/vaccines", response_class=HTMLResponse)
async def manage_vaccines(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        doctor = await check_auth_redirect(request, db)
        if isinstance(doctor, RedirectResponse):
            return doctor
            
        result = await db.execute(select(Vaccine).order_by(Vaccine.recommended_month))
        vaccines = result.scalars().all()
        
        return templates.TemplateResponse(
            "manage_vaccines.html",
            {
                "request": request,
                "vaccines": vaccines,
                "doctor": doctor
            }
        )
    except Exception as e:
        print(f"Vaccines management error: {e}")
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)


# 📝 Редактиране на ваксина
@router.get("/vaccines/{vaccine_id}/edit", response_class=HTMLResponse)
async def edit_vaccine_form(
    vaccine_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        doctor = await check_auth_redirect(request, db)
        if isinstance(doctor, RedirectResponse):
            return doctor
            
        result = await db.execute(select(Vaccine).where(Vaccine.id == vaccine_id))
        vaccine = result.scalar_one_or_none()
        
        if not vaccine:
            raise HTTPException(status_code=404, detail="Ваксината не е намерена")
        
        return templates.TemplateResponse(
            "edit_vaccine.html",
            {
                "request": request,
                "vaccine": vaccine,
                "doctor": doctor
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Edit vaccine form error: {e}")
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)


# 🔄 Актуализиране на ваксина
@router.post("/vaccines/{vaccine_id}/update")
async def update_vaccine_web(
    vaccine_id: int,
    request: Request,
    name: str = Form(...),
    is_mandatory: bool = Form(False),
    recommended_month: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        doctor = await check_auth_redirect(request, db)
        if isinstance(doctor, RedirectResponse):
            return doctor
            
        result = await db.execute(select(Vaccine).where(Vaccine.id == vaccine_id))
        vaccine = result.scalar_one_or_none()
        
        if not vaccine:
            raise HTTPException(status_code=404, detail="Ваксината не е намерена")
        
        vaccine.name = name
        vaccine.is_mandatory = is_mandatory
        vaccine.recommended_month = recommended_month if recommended_month else None
        
        await db.commit()
        return RedirectResponse(url="/vaccines", status_code=status.HTTP_303_SEE_OTHER)
        
    except Exception as e:
        print(f"Update vaccine error: {e}")
        await db.rollback()
        return RedirectResponse(url="/vaccines", status_code=status.HTTP_303_SEE_OTHER)


# ➕ Форма за добавяне на нов пациент
@router.get("/patients/new", response_class=HTMLResponse)
async def new_patient_form(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        doctor = await check_auth_redirect(request, db)
        if isinstance(doctor, RedirectResponse):
            return doctor
            
        return templates.TemplateResponse(
            "form.html", 
            {
                "request": request, 
                "patient": None, 
                "action_url": "/patients/create",
                "doctor": doctor
            }
        )
    except Exception as e:
        print(f"New patient form error: {e}")
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)


# 📥 Създаване на нов пациент
@router.post("/patients/create")
async def create_patient_web(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    egn: str = Form(...),
    birth_date: date = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        doctor = await check_auth_redirect(request, db)
        if isinstance(doctor, RedirectResponse):
            return doctor
            
        # Проверка дали ЕГН вече съществува
        result = await db.execute(select(Patient).where(Patient.egn == egn))
        existing_patient = result.scalar_one_or_none()
        if existing_patient:
            return templates.TemplateResponse(
                "form.html",
                {
                    "request": request,
                    "patient": None,
                    "action_url": "/patients/create",
                    "error": "Пациент с това ЕГН вече съществува",
                    "doctor": doctor
                }
            )
        
        new_patient = Patient(
            first_name=first_name,
            last_name=last_name,
            egn=egn,
            birth_date=birth_date,
            doctor_id=doctor.id
        )
        db.add(new_patient)
        await db.commit()
        await db.refresh(new_patient)
        
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        
    except Exception as e:
        print(f"Create patient error: {e}")
        await db.rollback()
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


# 📝 Форма за редактиране на пациент
@router.get("/patients/{patient_id}/edit", response_class=HTMLResponse)
async def edit_patient_form(
    patient_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        doctor = await check_auth_redirect(request, db)
        if isinstance(doctor, RedirectResponse):
            return doctor
            
        result = await db.execute(
            select(Patient).where(
                Patient.id == patient_id, 
                Patient.doctor_id == doctor.id
            )
        )
        patient = result.scalar_one_or_none()
        
        if not patient:
            raise HTTPException(status_code=404, detail="Пациентът не е намерен или нямате достъп до него")
        
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "patient": patient,
                "action_url": f"/patients/{patient_id}/update",
                "doctor": doctor
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Edit patient form error: {e}")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


# 🔄 Актуализиране на пациент
@router.post("/patients/{patient_id}/update")
async def update_patient_web(
    patient_id: int,
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    egn: str = Form(...),
    birth_date: date = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        doctor = await check_auth_redirect(request, db)
        if isinstance(doctor, RedirectResponse):
            return doctor
            
        result = await db.execute(
            select(Patient).where(
                Patient.id == patient_id, 
                Patient.doctor_id == doctor.id
            )
        )
        patient = result.scalar_one_or_none()
        
        if not patient:
            raise HTTPException(status_code=404, detail="Пациентът не е намерен или нямате достъп до него")
        
        # Проверка дали ЕГН вече съществува при друг пациент
        result = await db.execute(
            select(Patient).where(Patient.egn == egn, Patient.id != patient_id)
        )
        existing_patient = result.scalar_one_or_none()
        if existing_patient:
            return templates.TemplateResponse(
                "form.html",
                {
                    "request": request,
                    "patient": patient,
                    "action_url": f"/patients/{patient_id}/update",
                    "error": "Пациент с това ЕГН вече съществува",
                    "doctor": doctor
                }
            )
        
        patient.first_name = first_name
        patient.last_name = last_name
        patient.egn = egn
        patient.birth_date = birth_date
        
        await db.commit()
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update patient error: {e}")
        await db.rollback()
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


# ❌ Изтриване на пациент
@router.post("/patients/{patient_id}/delete")
async def delete_patient_web(
    patient_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        doctor = await check_auth_redirect(request, db)
        if isinstance(doctor, RedirectResponse):
            return doctor
            
        result = await db.execute(
            select(Patient).where(
                Patient.id == patient_id, 
                Patient.doctor_id == doctor.id
            )
        )
        patient = result.scalar_one_or_none()
        
        if not patient:
            raise HTTPException(status_code=404, detail="Пациентът не е намерен или нямате достъп до него")
        
        # Изтриваме всички свързани имунизации
        result = await db.execute(
            select(Immunization).where(Immunization.patient_id == patient_id)
        )
        immunizations = result.scalars().all()
        for immunization in immunizations:
            await db.delete(immunization)
        
        await db.delete(patient)
        await db.commit()
        
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete patient error: {e}")
        await db.rollback()
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


# 💉 Страница с ваксини на пациент
@router.get("/patients/{patient_id}/vaccines", response_class=HTMLResponse)
async def patient_vaccines(
    patient_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        doctor = await check_auth_redirect(request, db)
        if isinstance(doctor, RedirectResponse):
            return doctor
            
        # Вземаме пациента
        result = await db.execute(
            select(Patient).where(
                Patient.id == patient_id, 
                Patient.doctor_id == doctor.id
            )
        )
        patient = result.scalar_one_or_none()
        
        if not patient:
            raise HTTPException(status_code=404, detail="Пациентът не е намерен или нямате достъп до него")
        
        # Изчисляваме възрастта в месеци
        age_months = calculate_age_in_months(patient.birth_date)
        
        # Всички ваксини
        result = await db.execute(select(Vaccine))
        all_vaccines = result.scalars().all()
        
        # Задължителни ваксини според възрастта
        required_vaccines = required_mandatory_vaccines(age_months, all_vaccines)
        
        # Поставени ваксини с данни за имунизациите
        result = await db.execute(
            select(Immunization).where(Immunization.patient_id == patient_id)
        )
        immunizations = result.scalars().all()
        given_vaccine_ids = {imm.vaccine_id for imm in immunizations}
        
        # Създаваме речници за по-лесно търсене
        immunization_dict = {imm.vaccine_id: imm for imm in immunizations}
        
        # Списъци за темплейта
        given_vaccines = []
        for vaccine in all_vaccines:
            if vaccine.id in given_vaccine_ids:
                immunization = immunization_dict[vaccine.id]
                given_vaccines.append({
                    'vaccine': vaccine,
                    'immunization': immunization
                })
        
        missing_vaccines = [v for v in required_vaccines if v.id not in given_vaccine_ids]
        
        return templates.TemplateResponse(
            "patient_vaccines.html",
            {
                "request": request,
                "patient": patient,
                "given": given_vaccines,
                "missing": missing_vaccines,
                "doctor": doctor,
                "age_months": age_months
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Patient vaccines error: {e}")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
