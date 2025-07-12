from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import date
from typing import List

from database import get_db
from models import Patient, Doctor, Vaccine, Immunization
from routers.auth import get_current_doctor_web
from utils.schedule import calculate_age_in_months, required_mandatory_vaccines

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# 🏠 Dashboard - показва всички пациенти на лекаря
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_web)
):
    result = await db.execute(select(Patient).where(Patient.doctor_id == current_doctor.id))
    patients = result.scalars().all()
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "patients": patients,
            "doctor": current_doctor
        }
    )


# ➕ Форма за добавяне на нов пациент
@router.get("/patients/new", response_class=HTMLResponse)
async def new_patient_form(
    request: Request,
    current_doctor: Doctor = Depends(get_current_doctor_web)
):
    return templates.TemplateResponse(
        "form.html", 
        {
            "request": request, 
            "patient": None, 
            "action_url": "/patients/create",
            "doctor": current_doctor
        }
    )


# 📥 Създаване на нов пациент
@router.post("/patients/create")
async def create_patient_web(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    egn: str = Form(...),
    birth_date: date = Form(...),
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_web)
):
    try:
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
                    "doctor": current_doctor
                }
            )
        
        new_patient = Patient(
            first_name=first_name,
            last_name=last_name,
            egn=egn,
            birth_date=birth_date,
            doctor_id=current_doctor.id
        )
        db.add(new_patient)
        await db.commit()
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "patient": None,
                "action_url": "/patients/create",
                "error": f"Грешка при създаване на пациент: {str(e)}",
                "doctor": current_doctor
            }
        )


# 📝 Форма за редактиране на пациент
@router.get("/patients/{patient_id}/edit", response_class=HTMLResponse)
async def edit_patient_form(
    patient_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_web)
):
    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id, 
            Patient.doctor_id == current_doctor.id
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
            "doctor": current_doctor
        }
    )


# 🔄 Актуализиране на пациент
@router.post("/patients/{patient_id}/update")
async def update_patient_web(
    patient_id: int,
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    egn: str = Form(...),
    birth_date: date = Form(...),
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_web)
):
    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id, 
            Patient.doctor_id == current_doctor.id
        )
    )
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Пациентът не е намерен или нямате достъп до него")
    
    try:
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
                    "doctor": current_doctor
                }
            )
        
        patient.first_name = first_name
        patient.last_name = last_name
        patient.egn = egn
        patient.birth_date = birth_date
        
        await db.commit()
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "patient": patient,
                "action_url": f"/patients/{patient_id}/update",
                "error": f"Грешка при актуализиране: {str(e)}",
                "doctor": current_doctor
            }
        )


# ❌ Изтриване на пациент
@router.post("/patients/{patient_id}/delete")
async def delete_patient_web(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_web)
):
    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id, 
            Patient.doctor_id == current_doctor.id
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


# 💉 Страница с ваксини на пациент
@router.get("/patients/{patient_id}/vaccines", response_class=HTMLResponse)
async def patient_vaccines(
    patient_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_web)
):
    # Вземаме пациента
    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id, 
            Patient.doctor_id == current_doctor.id
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
    
    # Поставени ваксини
    result = await db.execute(
        select(Immunization).where(Immunization.patient_id == patient_id)
    )
    immunizations = result.scalars().all()
    given_vaccine_ids = {imm.vaccine_id for imm in immunizations}
    
    # Списъци за темплейта
    given_vaccines = [v for v in all_vaccines if v.id in given_vaccine_ids]
    missing_vaccines = [v for v in required_vaccines if v.id not in given_vaccine_ids]
    
    return templates.TemplateResponse(
        "patient_vaccines.html",
        {
            "request": request,
            "patient": patient,
            "given": given_vaccines,
            "missing": missing_vaccines,
            "doctor": current_doctor,
            "age_months": age_months
        }
    )


# 💉 Форма за добавяне на ваксина
@router.get("/patients/{patient_id}/vaccines/add", response_class=HTMLResponse)
async def add_vaccine_form(
    patient_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_web)
):
    # Проверка на достъп до пациента
    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id, 
            Patient.doctor_id == current_doctor.id
        )
    )
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Пациентът не е намерен или нямате достъп до него")
    
    # Всички налични ваксини
    result = await db.execute(select(Vaccine))
    all_vaccines = result.scalars().all()
    
    # Вече поставени ваксини
    result = await db.execute(
        select(Immunization).where(Immunization.patient_id == patient_id)
    )
    given_vaccine_ids = {imm.vaccine_id for imm in result.scalars().all()}
    
    # Ваксини, които могат да се добавят
    available_vaccines = [v for v in all_vaccines if v.id not in given_vaccine_ids]
    
    return templates.TemplateResponse(
        "add_vaccine.html",
        {
            "request": request,
            "patient": patient,
            "vaccines": available_vaccines,
            "doctor": current_doctor
        }
    )


# 💉 Добавяне на ваксина към пациент
@router.post("/patients/{patient_id}/vaccines/add")
async def add_vaccine_to_patient(
    patient_id: int,
    request: Request,
    vaccine_id: int = Form(...),
    date_given: date = Form(...),
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_web)
):
    # Проверка на достъп до пациента
    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id, 
            Patient.doctor_id == current_doctor.id
        )
    )
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Пациентът не е намерен или нямате достъп до него")
    
    try:
        # Проверка дали ваксината вече е поставена
        result = await db.execute(
            select(Immunization).where(
                Immunization.patient_id == patient_id,
                Immunization.vaccine_id == vaccine_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("Тази ваксина вече е поставена на пациента")
        
        # Добавяне на новата имунизация
        new_immunization = Immunization(
            patient_id=patient_id,
            vaccine_id=vaccine_id,
            date_given=date_given,
            doctor_id=current_doctor.id
        )
        db.add(new_immunization)
        await db.commit()
        
        return RedirectResponse(
            url=f"/patients/{patient_id}/vaccines", 
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        # При грешка, връщаме формата с грешка
        result = await db.execute(select(Vaccine))
        all_vaccines = result.scalars().all()
        
        result = await db.execute(
            select(Immunization).where(Immunization.patient_id == patient_id)
        )
        given_vaccine_ids = {imm.vaccine_id for imm in result.scalars().all()}
        available_vaccines = [v for v in all_vaccines if v.id not in given_vaccine_ids]
        
        return templates.TemplateResponse(
            "add_vaccine.html",
            {
                "request": request,
                "patient": patient,
                "vaccines": available_vaccines,
                "doctor": current_doctor,
                "error": str(e)
            }
        )