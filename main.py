from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import os

# Импортиране на всички роутери
from routers import patient, immunization, auth, vaccine, doctor, schedule
import crud

app = FastAPI(
    title="Vaccination Schedule API",
    version="1.0.0",
    description="API за управление на ваксинационни графици"
)

# ВАЖНО: Първо включваме auth роутера
app.include_router(auth.router)

# След това включваме Web CRUD роутери (които зависят от auth)
app.include_router(crud.router)

# Накрая включваме API роутерите
app.include_router(patient.router) 
app.include_router(doctor.router)
app.include_router(vaccine.router)
app.include_router(immunization.router)
app.include_router(schedule.router)

# Статични файлове (ако имате CSS, JS, изображения)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
def redirect_to_login():
    """Пренасочване към login страницата"""
    return RedirectResponse(url="/auth/login")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)