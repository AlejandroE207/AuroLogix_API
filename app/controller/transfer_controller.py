from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_token_payload, get_current_user_id, get_current_user_role
from app.db.session import get_db
from app.service import transfer_service

router = APIRouter(
    prefix="/transfer",
    tags=["transfer"],
    dependencies=[Depends(get_current_token_payload)],
)


@router.get(
    "/get_list_piso",
    description="Consulta el inventario disponible actualmente en posiciones de piso.",
)
async def get_list_piso(
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
):
    return await transfer_service.get_list_piso(db)


@router.get(
    "/get_list_stored",
    description="Consulta el inventario almacenado en posiciones de rack.",
)
async def get_list_stored(
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
):
    return await transfer_service.get_list_stored_inventory(db)


@router.get(
    "/manual_positions/{id_inventory}",
    description="Obtiene las posiciones de destino válidas para reubicar manualmente un inventario.",
)
async def get_manual_positions(
    id_inventory: int,
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
):
    result = await transfer_service.get_manual_positions(db, id_inventory)
    if result.get("result") == 1:
        return result
    raise HTTPException(status_code=400, detail=result.get("message", "No fue posible obtener las posiciones"))


@router.post(
    "/floor_to_rack_auto",
    description="Crea una tarea de traslado desde piso al rack sugerido automáticamente.",
)
async def floor_to_rack_auto(
    db: AsyncSession = Depends(get_db),
    id_inventory: int = Body(..., embed=True),
    cantidad: float = Body(..., embed=True),
    id_usuario: int = Depends(get_current_user_id),
    current_user_role: int = Depends(get_current_user_role),
):
    transfer_data = await transfer_service.floor_to_rack_auto(db, id_inventory, cantidad, id_usuario)
    if transfer_data.result == 1:
        return {
            "message": transfer_data.message,
            "id": transfer_data.id,
            "id_inventario": transfer_data.id_inventario,
            "posicion_sugerida_id": transfer_data.posicion_sugerida_id,
            "cod_posicion_sugerida": transfer_data.cod_posicion_sugerida,
            "cantidad": transfer_data.cantidad,
        }
    raise HTTPException(status_code=400, detail=transfer_data.message)


@router.post(
    "/floor_to_rack_manual",
    description="Crea una tarea de traslado desde piso hacia una posición de rack seleccionada manualmente.",
)
async def floor_to_rack_manual(
    db: AsyncSession = Depends(get_db),
    id_inventory: int = Body(..., embed=True),
    cantidad: float = Body(..., embed=True),
    posicion_destino_id: int = Body(..., embed=True),
    id_usuario: int = Depends(get_current_user_id),
    current_user_role: int = Depends(get_current_user_role),
):
    transfer_data = await transfer_service.floor_to_rack_manual(
        db,
        id_inventory,
        cantidad,
        posicion_destino_id,
        id_usuario,
    )
    if transfer_data.result == 1:
        return {
            "message": transfer_data.message,
            "id": transfer_data.id,
            "id_inventario": transfer_data.id_inventario,
            "posicion_destino_id": transfer_data.posicion_destino_id,
            "cod_posicion_destino": transfer_data.cod_posicion_destino,
            "cantidad": transfer_data.cantidad,
        }
    raise HTTPException(status_code=400, detail=transfer_data.message)


@router.post(
    "/stored_to_position_manual",
    description="Crea una tarea de traslado de inventario almacenado hacia una posición seleccionada manualmente.",
)
async def stored_to_position_manual(
    db: AsyncSession = Depends(get_db),
    id_inventory: int = Body(..., embed=True),
    cantidad: float = Body(..., embed=True),
    posicion_destino_id: int = Body(..., embed=True),
    id_usuario: int = Depends(get_current_user_id),
    current_user_role: int = Depends(get_current_user_role),
):
    transfer_data = await transfer_service.floor_to_rack_manual(
        db,
        id_inventory,
        cantidad,
        posicion_destino_id,
        id_usuario,
    )
    if transfer_data.result == 1:
        return {
            "message": transfer_data.message,
            "id": transfer_data.id,
            "id_inventario": transfer_data.id_inventario,
            "posicion_destino_id": transfer_data.posicion_destino_id,
            "cod_posicion_destino": transfer_data.cod_posicion_destino,
            "cantidad": transfer_data.cantidad,
        }
    raise HTTPException(status_code=400, detail=transfer_data.message)


@router.post(
    "/confirm_transfer",
    description="Confirma una tarea de traslado validando el código de la posición de destino escaneada.",
)
async def confirm_transfer(
    db: AsyncSession = Depends(get_db),
    id_task: int = Body(..., embed=True),
    cod_posicion_escaneada: str = Body(..., embed=True),
    id_usuario: int = Depends(get_current_user_id),
    current_user_role: int = Depends(get_current_user_role),
):
    transfer_data = await transfer_service.confirm_transfer_task(db, id_task, cod_posicion_escaneada, id_usuario)
    if transfer_data.result == 1:
        return {
            "message": transfer_data.message,
            "id_movimiento": transfer_data.id,
            "id_inventario": transfer_data.id_inventario,
            "posicion_destino_id": transfer_data.posicion_destino_id,
            "cod_posicion_destino": transfer_data.cod_posicion_destino,
            "cantidad": transfer_data.cantidad,
        }
    raise HTTPException(status_code=400, detail=transfer_data.message)

