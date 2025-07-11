from fastapi import FastAPI
from routers import patient, immunization, auth, vaccine , doctor, schedule

app = FastAPI(
    title="Vaccination Schedule API",
    version="1.0.0"
)

# Включване на routers
app.include_router(patient.router)
app.include_router(doctor.router)
app.include_router(vaccine.router)
app.include_router(immunization.router)
app.include_router(auth.router)
app.include_router(schedule.router)

@app.get("/")
def root():
    return {"message": "Добре дошли в Vaccination Schedule API"}
