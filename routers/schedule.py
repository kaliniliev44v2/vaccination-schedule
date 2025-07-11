from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Dict

from database import get_db
from models import Patient, Vaccine, Immunization, Doctor
from routers.auth import get_current_doctor
from utils.schedule import calculate_age_in_months, required_mandatory_vaccines

router = APIRouter(prefix="/schedule", tags=["Schedule"])

@router.get("/{patient_id}", response_model=Dict[str, List[str]])
async def get_patient_schedule(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient or patient.doctor_id != current_doctor.id:
        raise HTTPException(status_code=403, detail="Нямате достъп до този пациент")

    age_months = calculate_age_in_months(patient.birth_date)
    result = await db.execute(select(Vaccine))
    all_vaccines = result.scalars().all()
    required = required_mandatory_vaccines(age_months, all_vaccines)

    result = await db.execute(select(Immunization).where(Immunization.patient_id == patient_id))
    given = result.scalars().all()
    given_ids = {i.vaccine_id for i in given}

    given_names = [v.name for v in all_vaccines if v.id in given_ids]
    missing_names = [v.name for v in required if v.id not in given_ids]

    return {"given": given_names, "missing": missing_names}
