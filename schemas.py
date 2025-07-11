from pydantic import BaseModel
from datetime import date
from typing import Optional


# --- Doctor ---
class DoctorCreate(BaseModel):
    username: str
    password: str  # plaintext за създаване, ще се хешира

class DoctorOut(BaseModel):
    id: int
    username: str
    class Config:
        orm_mode = True


# --- Patient ---
class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    egn: str
    birth_date: date
    doctor_id: Optional[int] = None

class PatientOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    egn: str
    birth_date: date
    doctor_id: Optional[int]
    class Config:
        orm_mode = True


# --- Vaccine ---
class VaccineCreate(BaseModel):
    name: str
    is_mandatory: Optional[bool] = True
    recommended_month: Optional[int]

class VaccineOut(BaseModel):
    id: int
    name: str
    is_mandatory: bool
    recommended_month: Optional[int]
    class Config:
        orm_mode = True


# --- Immunization ---
class ImmunizationCreate(BaseModel):
    patient_id: int
    vaccine_id: int
    date_given: date

class ImmunizationOut(BaseModel):
    id: int
    patient_id: int
    vaccine_id: int
    date_given: date
    doctor_id: int
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str
