from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.service import dashboard_service
from app.core.security import (
    get_current_token_payload,
    get_current_user_id,
    get_current_user_role,
    require_role,
)

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_token_payload)]
)

@router.get("/get_summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
):
    summary_data = await dashboard_service.get_summary(db)
    if summary_data.result == 1:
        return summary_data
    else:
        raise HTTPException(status_code=400, detail=summary_data.message)
    

@router.get("/get_all_positions_table")
async def get_all_positions_table(
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
    item: Optional[str] = None,
    lote: Optional[str] = None,
    posicion_estado: Optional[str] = None,
    estado_alerta: Optional[str] = None,
    limite: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    position_data_list = []
    position_data_list = await dashboard_service.get_all_positions_table(db, item, posicion_estado, lote,estado_alerta ,limite, offset)
    if position_data_list:
        return position_data_list
    else:
        raise HTTPException(status_code=400, detail="Error al obtener las posiciones")

@router.get("/get_all_positions")
async def get_all_positions(
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
):
    position_data_list = []
    position_data_list = await dashboard_service.get_all_positions(db)
    if position_data_list:
        return position_data_list
    else:
        raise HTTPException(status_code=400, detail="Error al obtener las posiciones")

@router.get("/get_positions_by_item")
async def get_positions_by_item(
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
    item: Optional[str] = Query(None),
    lote: Optional[str] = Query(None)
):
    position_data_list = []
    position_data_list = await dashboard_service.get_positions_by_item(db, item, lote)
    if position_data_list:
        return position_data_list
    else:
        raise HTTPException(status_code=400, detail="Error al obtener las posiciones por ítem")