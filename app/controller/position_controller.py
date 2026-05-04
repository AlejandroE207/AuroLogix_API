from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.service import position_service
from app.model.position_model import Position
from app.core.security import(
    get_current_token_payload,
    get_current_user_role,
    require_role,
)

router = APIRouter(
    prefix="/positions",
    tags=["positions"],
    # dependencies=[Depends(get_current_token_payload)]
)

@router.get("/position_by_id/{id_position}")
async def read_position_by_id(
    id_position: int,
    db: AsyncSession = Depends(get_db),
    # current_user_role: int = Depends(get_current_user_role),
):
    """Lee una posición por su ID"""
    position_data = await position_service.get_position_by_id(db, id_position)
    if position_data.result == 1:
        return position_data
    else:
        raise HTTPException(status_code=404, detail=position_data.message)
    
@router.get("/position_by_cod_position/{cod_posicion}")
async def read_position_by_cod_position(
    cod_position: str,
    db: AsyncSession = Depends(get_db),
    # current_user_role: int = Depends(get_current_user_role),
):
    """Lee una posición por su código"""
    position_data = await position_service.get_position_by_cod_position(db, cod_position)
    if position_data.result == 1:
        return position_data
    else:
        raise HTTPException(status_code=404, detail=position_data.message)
    
@router.get("/position_by_store/{store}")
async def read_positions_by_store(
    store: int,
    db: AsyncSession = Depends(get_db),
    
):
    """Lee las posiciones de una bodega"""
    position_data_list = await position_service.get_positions_by_store(db, store)
    if position_data_list and position_data_list[0].result == 1:
        return position_data_list
    else:
        raise HTTPException(status_code=404, detail="No se encontraron posiciones para la bodega especificada")
    
@router.get("/position_by_state/{state}")
async def read_positions_by_state(
    state: int,
    db:  AsyncSession = Depends(get_db),
    
):
    """ Lee las posiciones por su estado (1: disponible, 2: ocupado, 3: deshabilitado )"""
    position_data_list = await position_service.get_positions_by_state(db, state)
    if position_data_list and position_data_list[0].result == 1:
        return position_data_list
    else:
        raise HTTPException(status_code=404, detail="No se encontraron posiciones para el estado especificado")


@router.put("/update_position_state")
async def update_position_state(
    id_position: int = Body(..., embed = True),
    new_state: int = Body(..., embed = True),
    db: AsyncSession = Depends(get_db),
    
):
    """Actualiza el estado de una posicion (1: disponible, 2: ocupado, 3: deshabilitado )"""
    position_data = await position_service.update_position_state(db, id_position, new_state)
    if position_data.result == 1:
        return position_data.message
    else:
        raise HTTPException(status_code=400, detail=position_data.message)