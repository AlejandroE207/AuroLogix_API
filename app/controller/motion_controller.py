from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.service import motion_view_service
from app.model.motion_view_model import MotionView
from app.core.security import(
    get_current_token_payload,
    get_current_user_id,
    get_current_user_role,
    require_role,
)

router = APIRouter(
    prefix="/motion",
    tags=["motion"],
    dependencies=[Depends(get_current_token_payload)]
)

@router.get("/list_motion")
async def list_motion(
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
    item: Optional[str] = Query(None),
    tipo_movimiento: Optional[str] = Query(None),
    desde_fecha: Optional[datetime] = Query(None),
    hasta_fecha: Optional[datetime] = Query(None),
    limite: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    motion_data_list = []
    motion_data_list = await motion_view_service.list_motion(db, item, tipo_movimiento, desde_fecha, hasta_fecha, limite, offset)
    result = motion_data_list.get("result", 0)
    if result == 1:
        return motion_data_list.get("data", [])
    else:
        raise HTTPException(status_code=404, detail="No se encontraron movimientos con los criterios especificados")