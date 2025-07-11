from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from database import get_db
from models import Vaccine, Doctor
from schemas import VaccineCreate, VaccineOut
from routers.auth import get_current_doctor

router = APIRouter(prefix="/vaccines", tags=["Vaccines"])

# 📋 Връща всички ваксини
@router.get("/", response_model=List[VaccineOut])
async def get_all_vaccines(
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    result = await db.execute(select(Vaccine))
    return result.scalars().all()

# ➕ Добавяне на ваксина 
@router.post("/", response_model=VaccineOut, status_code=status.HTTP_201_CREATED)
async def create_vaccine(
    vaccine: VaccineCreate,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    new_vaccine = Vaccine(**vaccine.dict())
    db.add(new_vaccine)
    await db.commit()
    await db.refresh(new_vaccine)
    return new_vaccine

# ❌ Изтриване на ваксина по ID 
@router.delete("/{vaccine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vaccine(
    vaccine_id: int,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    result = await db.execute(select(Vaccine).where(Vaccine.id == vaccine_id))
    vaccine = result.scalar_one_or_none()
    if not vaccine:
        raise HTTPException(status_code=404, detail="Ваксината не е намерена")
    await db.delete(vaccine)
    await db.commit()
