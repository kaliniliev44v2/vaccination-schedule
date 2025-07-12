from fastapi import FastAPI
from routers import patient, immunization, auth, vaccine , doctor, schedule
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request
import os
from routers.auth import router as web_auth_router 

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


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
app.include_router(web_auth_router)


@app.get("/", include_in_schema=False)
def redirect_to_login():
    return RedirectResponse(url="/auth/login")
