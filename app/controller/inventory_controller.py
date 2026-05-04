from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.service import inventory_service
from app.model.inventory_model import Motion
from app.model.inventory_model import Inventory
from app.core.security import (
    get_current_token_payload,
    get_current_user_id,
    get_current_user_role,
    require_role,
)

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    # dependencies=[Depends(get_current_token_payload)]
)

@router.post("/create_input_inventory")
async def create_input_inventory(
    tipo_movimiento: int = Body(..., embed=True),
    id_item: int = Body(..., embed = True),
    lote : str = Body(..., embed = True),
    cantidad: int = Body(..., embed = True),
    posicion_destino_id: int = Body(..., embed = True),
    fecha: datetime = Body(..., embed = True),
    id_usuario:int = Depends(get_current_user_id),
    estado : str = Body(..., embed = True),
    detalles: str = Body(..., embed = True),
    db: AsyncSession = Depends(get_db),
    
    
):
    motion_data = Motion()