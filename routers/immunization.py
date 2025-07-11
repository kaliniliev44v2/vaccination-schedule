from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from models import Immunization, Patient, Vaccine, Doctor
from database import get_db
from schemas import ImmunizationCreate, ImmunizationOut
from routers.auth import get_current_doctor

router = APIRouter(prefix="/immunizations", tags=["Immunizations"])

# 📥 Поставяне на нова имунизация
@router.post("/", response_model=ImmunizationOut, status_code=status.HTTP_201_CREATED)
async def create_immunization(
    immunization: ImmunizationCreate,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    # Проверка: дали пациентът е на този лекар
    result = await db.execute(select(Patient).where(Patient.id == immunization.patient_id))
    patient = result.scalar_one_or_none()
    if not patient or patient.doctor_id != current_doctor.id:
        raise HTTPException(status_code=403, detail="Нямате достъп до този пациент")

    # Проверка: дали ваксината съществува
    result = await db.execute(select(Vaccine).where(Vaccine.id == immunization.vaccine_id))
    vaccine = result.scalar_one_or_none()
    if not vaccine:
        raise HTTPException(status_code=404, detail="Ваксината не съществува")

    new_immunization = Immunization(
        patient_id=immunization.patient_id,
        vaccine_id=immunization.vaccine_id,
        date_given=immunization.date_given,
        doctor_id=current_doctor.id
    )
    db.add(new_immunization)
    await db.commit()
    await db.refresh(new_immunization)
    return new_immunization

# 📋 Връща имунизациите на даден пациент (само ако е твой пациент)
@router.get("/patient/{patient_id}", response_model=List[ImmunizationOut])
async def get_immunizations_for_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient or patient.doctor_id != current_doctor.id:
        raise HTTPException(status_code=403, detail="Нямате достъп до този пациент")

    result = await db.execute(select(Immunization).where(Immunization.patient_id == patient_id))
    return result.scalars().all()
