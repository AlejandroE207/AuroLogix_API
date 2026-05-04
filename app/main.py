from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import get_settings
from app.controller import inventory_controller, position_controller, user_controller
from app.controller import auth_controller
from app.db.session import get_db, Base

settings = get_settings()


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url=settings.app_docs_url,
    redoc_url=settings.app_redoc_url,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


app.include_router(user_controller.router)
app.include_router(auth_controller.router)
app.include_router(position_controller.router)
app.include_router(inventory_controller.router)
# app.include_router(users.router, prefix="/users", tags=["Users"])
# app.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])

@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Raíz de la API",
    tags=["General"]
)
async def root():
    """Endpoint raíz de la API"""
    return {
        "message": "Bienvenido a la API",
        "app_name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs"
    }
 
@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    tags=["General"]
)
async def health_check():
    """Verifica que la API está funcionando"""
    return {
        "status": "ok",
        "message": "API funcionando correctamente"
    }
 

 