from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Body, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.model.aux_inv_model import InvAux, InvAuxCont
from app.service import inventory_service, adjustment_service
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
    
    
@router.post("/import_inventory")
async def import_inventory(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(require_role(2, 4)),  # Administrador, Supervisor
):
    """Actualiza el inventario a partir de un archivo Excel (.xlsx) de conteo físico.

    Columnas esperadas: UBICACIÓN, REFERENCIA, LOTE, F.V, CANTIDAD
    (DESCRIPCION es opcional y solo informativa).

    - Si la posición + item + lote ya existe en inventario, se SUMA la cantidad.
    - Si no existe, se crea un nuevo registro.
    - Los registros no presentes en el archivo no se modifican.
    - Las filas con posición/referencia inexistente se omiten y se reportan.
    """
    filename = file.filename or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension != "xlsx":
        raise HTTPException(status_code=400, detail="El archivo debe tener formato .xlsx.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo no puede superar 15 MB.")

    result = await inventory_service.import_inventory_from_excel(db, content, filename)
    if result["result"] == 0 and not result.get("errores"):
        raise HTTPException(status_code=422, detail=result["message"])
    return result


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

# ****************************** ACTUALIZACION DE POSICIONES EN INVENTARIO ******************************

@router.get("/position_inventory/{id_posicion}")
async def get_position_inventory(
    id_posicion: int,
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(require_role(2, 4)),  # Administrador, Supervisor
):
    """Lista los items almacenados en una posicion para la pantalla de edicion.

    El usuario selecciona la posicion y este endpoint devuelve todos los
    registros (item + lote + cantidad + fecha de vencimiento) que contiene,
    para que elija cual actualizar o retirar.
    """
    data = await adjustment_service.get_inventory_by_position(db, id_posicion)
    return data


@router.put("/update_position_inventory")
async def update_position_inventory(
    db: AsyncSession = Depends(get_db),
    id_inventario: int = Body(..., embed=True),
    id_item: int = Body(..., embed=True),
    lote: str | None = Body(None, embed=True),
    cantidad: float = Body(..., embed=True),
    fecha_vencimiento: datetime | None = Body(None, embed=True),
    motivo: str = Body(..., embed=True),
    current_user_role: int = Depends(require_role(2, 4)),  # Administrador, Supervisor
    id_usuario: int = Depends(get_current_user_id),
):
    """Actualiza cantidad, lote, fecha de vencimiento o item de un registro
    de inventario, dejando trazabilidad completa en inventario_ajustes y en
    movimientos (tipos 4/5 de ajuste). El motivo es obligatorio.

    Si el nuevo item + lote ya existe en la misma posicion, los registros se
    fusionan sumando las cantidades.
    """
    result = await adjustment_service.update_position_inventory(
        db, id_inventario, id_item, lote, cantidad, fecha_vencimiento, motivo, id_usuario
    )
    if result["result"] == 1:
        return result
    if result["result"] == 2:
        # Sin cambios: no es un error, pero se informa al cliente
        return result

    status_code = 404 if result["message"] == "El registro de inventario no existe" else 400
    raise HTTPException(status_code=status_code, detail=result["message"])


@router.api_route("/delete_position_inventory", methods=["POST", "DELETE"])
async def delete_position_inventory(
    db: AsyncSession = Depends(get_db),
    id_inventario: int = Body(..., embed=True),
    motivo: str = Body(..., embed=True),
    current_user_role: int = Depends(require_role(2, 4)),  # Administrador, Supervisor
    id_usuario: int = Depends(get_current_user_id),
):
    """Retira por completo un item de una posicion (ajuste negativo por el
    total). Queda registrado en inventario_ajustes como ELIMINACION y en
    movimientos como ajuste negativo. El motivo es obligatorio.
    """
    result = await adjustment_service.delete_position_inventory(db, id_inventario, motivo, id_usuario)
    if result["result"] == 1:
        return result

    status_code = 404 if result["message"] == "El registro de inventario no existe" else 400
    raise HTTPException(status_code=status_code, detail=result["message"])


@router.get("/adjustment_history")
async def adjustment_history(
    db: AsyncSession = Depends(get_db),
    cod_posicion: str | None = None,
    item: str | None = None,
    desde_fecha: datetime | None = None,
    hasta_fecha: datetime | None = None,
    limite: int = 50,
    offset: int = 0,
    current_user_role: int = Depends(require_role(2)),  # Admin, Auditor, Supervisor
):
    """Historial de ajustes de inventario con filtros opcionales y paginacion.

    - cod_posicion: busqueda parcial por codigo de posicion (ej. 'R6-N1-P2').
    - item: busqueda parcial por cod_item o nombre/descripcion del item.

    El Auditor tambien puede consultarlo (solo lectura); si no lo deseas,
    cambia require_role(2, 3, 4) por require_role(2, 4).
    """
    return await adjustment_service.list_adjustments(
        db, cod_posicion, item, desde_fecha, hasta_fecha, limite, offset
    )