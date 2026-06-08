from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.service import input_service, input_service
from app.model.putaway_model import Putaway
from app.core.security import (
    get_current_token_payload,
    get_current_user_id,
    get_current_user_role,
    require_role,
)

router = APIRouter(
    prefix="/input",
    tags=["input"],
    dependencies=[Depends(get_current_token_payload)]
)

@router.post("/create_input")
async def create_input(
    db: AsyncSession = Depends(get_db),
    id_item: int = Body(..., embed=True),
    lote : str = Body(..., embed = True),
    cantidad: int = Body(..., embed = True),
    fecha_vencimiento: Optional[str] = Body(None, embed = True),
    id_usuario = Depends(get_current_user_id),
    current_user_role: int = Depends(get_current_user_role),
):
    if fecha_vencimiento is not None:
            fecha_vencimiento = fecha_vencimiento.strip()
            if fecha_vencimiento == "" or fecha_vencimiento.lower() in ["null", "undefined"]:
                fecha_vencimiento = None
        
    putaway_data = Putaway(id_item=id_item, lote=lote, cantidad=cantidad, id_usuario=id_usuario, fecha_vencimiento = fecha_vencimiento)
    putaway_data = await input_service.create_input(db,putaway_data)
    if putaway_data.result == 1:
        return {
            "message": putaway_data.message,
            "id": putaway_data.id
        }
    else:
        raise HTTPException(status_code=400, detail=putaway_data.message)


@router.post("/confirm_input")
async def confirm_input(
    db: AsyncSession = Depends(get_db),
    cod_posicion: str = Body(..., embed=True),
    id_input: int = Body(..., embed=True),
    current_user_role: int = Depends(get_current_user_role),
):
    putaway_data = Putaway()
    putaway_data = await input_service.confirm_input(db, cod_posicion, id_input)
    if putaway_data.result == 1:
        return {
            "message": putaway_data.message
        }
    else:
        raise HTTPException(status_code=400, detail=putaway_data.message)
    