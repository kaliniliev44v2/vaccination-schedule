from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Patient
from database import get_db

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.get("/")
async def get_patients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient))
    return result.scalars().all()

@router.post("/")
async def create_patient(patient: Patient, db: AsyncSession = Depends(get_db)):
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient
