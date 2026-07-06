from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.model.aux_inv_model import InvAux, InvAuxCont
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

#******************************* FUNCION DE INVENTARIAR ******************************
@router.get("/get_positions")
async def get_positions(
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
):
    """Obtiene el listado de posiciones utilizando una caché temporal."""
    position_data_list = await inventory_service.get_positions(db)
    if position_data_list:
        return position_data_list

    raise HTTPException(
        status_code=404,
        detail="No se encontraron posiciones",
    )
    
@router.post("/create_inv_aux")
async def create_input_inventory(
    db: AsyncSession = Depends(get_db),
    id_posicion: int = Body(..., embed=True),
    id_item: int = Body(..., embed=True),
    lote: str = Body(..., embed=True),
    cantidad: float = Body(..., embed=True),
    fecha_vencimiento: str = Body(..., embed=True),
    current_user_role: int = Depends(get_current_user_role),
    id_usuario: int = Depends(get_current_user_id)
):
    """Crea el registro de inventario de entrada y manejo de conteo"""
    invAux =  InvAux(id_posicion=id_posicion, id_item=id_item, lote=lote, fecha_vencimiento=fecha_vencimiento)
    invAuxCont = InvAuxCont(cantidad=cantidad, id_usuario=id_usuario)
    result = await inventory_service.create_input_invAux(db, invAux, invAuxCont)
    if result["result"] == 1:
        return {
            "message": result["message"]
        }
    else:
        raise HTTPException(status_code=400, detail=result["message"])
    
    
@router.get("/list_inv_aux_pending")
async def list_inv_aux_pending(
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
):
    """Obtiene el listado de inventario auxiliar pendiente de conteo"""
    invAux_data_list = await inventory_service.list_inv_aux_pending(db)
    return invAux_data_list


@router.get("/get_inventory_consolidated")
async def get_inventory_consolidated(
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
):
    """Obtiene un consolidado de inventario por item con detalle por lote."""
    consolidated = await inventory_service.get_inventory_consolidated(db)
    if consolidated:
        return consolidated

    raise HTTPException(
        status_code=404,
        detail="No se encontraron registros de inventario para consolidar",
    )
    
@router.post("/approve_inv_aux")
async def approve_inv_aux(
    db: AsyncSession = Depends(get_db),
    id_invAux: int = Body(..., embed=True),
    current_user_role: int = Depends(get_current_user_role),
):
    """Aprueba el inventario auxiliar cambiando su estado a 6."""
    result = await inventory_service.approve_inv_aux(db, id_invAux)
    if result["result"] == 1:
        return {"message": result["message"]}

    status_code = 404 if result["message"] == "Inventario auxiliar no encontrado" else 400
    raise HTTPException(status_code=status_code, detail=result["message"])