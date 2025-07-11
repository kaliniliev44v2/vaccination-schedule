from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# Лекари
class Doctor(Base):
    __tablename__ = 'doctors'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    patients = relationship("Patient", back_populates="doctor")


# Пациенти
class Patient(Base):
    __tablename__ = 'patients'

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    egn = Column(String, unique=True, nullable=False)
    birth_date = Column(Date, nullable=False)

    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    doctor = relationship("Doctor", back_populates="patients")

    immunizations = relationship("Immunization", back_populates="patient")


# Ваксини
class Vaccine(Base):
    __tablename__ = 'vaccines'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    is_mandatory = Column(Boolean, default=True)
    recommended_month = Column(Integer)  # месец от раждането, например 2, 4, 13

    immunizations = relationship("Immunization", back_populates="vaccine")


# Поставени имунизации
class Immunization(Base):
    __tablename__ = 'immunizations'

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    vaccine_id = Column(Integer, ForeignKey("vaccines.id"))
    date_given = Column(Date, nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="immunizations")
    vaccine = relationship("Vaccine", back_populates="immunizations")

