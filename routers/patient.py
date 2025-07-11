from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from utils.schedule import calculate_age_in_months, required_mandatory_vaccines
from models import Patient, Doctor, Vaccine, Immunization
from database import get_db
from schemas import PatientCreate, PatientOut
from routers.auth import get_current_doctor  # 👈 добавяме зависимостта

router = APIRouter(prefix="/patients", tags=["Patients"])

# 📥 Създаване на пациент (автоматично се свързва с логнатия лекар)
@router.post("/", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    new_patient = Patient(**patient.dict(), doctor_id=current_doctor.id)
    db.add(new_patient)
    await db.commit()
    await db.refresh(new_patient)
    return new_patient

# 📋 Взимане на всички пациенти на логнатия лекар
@router.get("/", response_model=List[PatientOut])
async def get_my_patients(
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    result = await db.execute(select(Patient).where(Patient.doctor_id == current_doctor.id))
    return result.scalars().all()

# 🔍 Взимане на конкретен пациент, ако е на текущия лекар
@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id, Patient.doctor_id == current_doctor.id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Пациентът не е намерен или не принадлежи на този лекар")
    return patient

# 📝 Актуализиране на пациент – само ако е на текущия лекар
@router.put("/{patient_id}", response_model=PatientOut)
async def update_patient(
    patient_id: int,
    updated: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id, Patient.doctor_id == current_doctor.id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Нямате достъп до този пациент")

    for key, value in updated.dict().items():
        setattr(patient, key, value)

    await db.commit()
    await db.refresh(patient)
    return patient

# ❌ Изтриване на пациент – само ако е на текущия лекар
@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id, Patient.doctor_id == current_doctor.id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Нямате достъп до този пациент")

    await db.delete(patient)
    await db.commit()

@router.get("/{patient_id}/missing-vaccines", response_model=List[str])
async def get_missing_vaccines(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    # Проверка на достъп
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient or patient.doctor_id != current_doctor.id:
        raise HTTPException(status_code=403, detail="Нямате достъп до този пациент")

    age_months = calculate_age_in_months(patient.birth_date)

    # Всички ваксини
    result = await db.execute(select(Vaccine))
    all_vaccines = result.scalars().all()

    # Задължителни според възраст
    required = required_mandatory_vaccines(age_months, all_vaccines)

    # Вече поставени ваксини
    result = await db.execute(select(Immunization).where(Immunization.patient_id == patient_id))
    given_ids = {imm.vaccine_id for imm in result.scalars().all()}

    # Ваксини, които липсват
    missing = [v.name for v in required if v.id not in given_ids]
    return missing
