from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import get_settings
from app.controller import dashboard_controller, input_controller, inventory_controller, item_controller, motion_controller, picking_controller, position_controller, transfer_controller, user_controller
from app.controller import auth_controller
from app.db.session import get_db, Base

import sys
import asyncio

if sys.platform == "win32":
    # 1. Cambiar la política del loop
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 2. Forzar al loop actual en este hilo a cambiar si ya fue creado
    try:
        loop = asyncio.get_event_loop()
        if type(loop).__name__ == "ProactorEventLoop":
            new_loop = asyncio.WindowsSelectorEventLoopPolicy().new_event_loop()
            asyncio.set_event_loop(new_loop)
    except RuntimeError:
        pass

settings = get_settings()


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url=settings.app_docs_url,
    redoc_url=settings.app_redoc_url,
)

origins =[
    "http://localhost:4200",  
    "http://localhost:3000",  
    "http://127.0.0.1:4200",
    "http://192.168.3.250:61793"
]

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
app.include_router(input_controller.router)
app.include_router(picking_controller.router)
app.include_router(item_controller.router)
app.include_router(motion_controller.router)
app.include_router(inventory_controller.router)
app.include_router(dashboard_controller.router)
app.include_router(transfer_controller.router)
# app.include_router(inventory_controller.router)
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
 
# main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
 