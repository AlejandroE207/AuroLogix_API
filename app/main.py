from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import app.routers.users as users

app = FastAPI(title="AuroTrack API", description="AuroTrack es un WMS de Laboratorios Aurofarma", version="1.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "API funcionando correctamente"}


app.include_router(users.router, prefix="/users", tags=["Users"])
# app.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])