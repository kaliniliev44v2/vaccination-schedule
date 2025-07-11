from fastapi import APIRouter, Depends
from schemas import DoctorOut
from models import Doctor
from routers.auth import get_current_doctor

router = APIRouter(prefix="/doctors", tags=["Doctors"])

# 👤 Връща текущия логнат доктор
@router.get("/me", response_model=DoctorOut)
async def get_me(current_doctor: Doctor = Depends(get_current_doctor)):
    return current_doctor
