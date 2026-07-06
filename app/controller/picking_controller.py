from fastapi import APIRouter, Depends, File, HTTPException, Body, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.service import picking_service
from app.model.picking_model import Picking, Picking_items, Picking_detalle, Orden
from app.core.security import(
    get_current_token_payload,
    get_current_user_id,
    get_current_user_role,
    require_role,

)

router = APIRouter(
    prefix="/picking",
    tags=["picking"],
    dependencies=[Depends(get_current_token_payload)]
)

@router.post("/create_picking")
async def create_picking(
    db: AsyncSession = Depends(get_db),
    codigo: str = Body(..., embed=True),
    cliente: str = Body(..., embed=True),
    tipo: str = Body(..., embed=True),
    id_usuario: int = Depends(get_current_user_id),
    detalles: str = Body(..., embed=True),
    lista_items: list[Picking_items] = Body(..., embed=True),
):
    """Crea un nuevo picking."""
    #ESTADO 1: Pendiente, 2: En proceso, 3: Completado
    orden = Orden(codigo=codigo, tipo=tipo ,cliente = cliente, estado= 1, id_usuario = id_usuario, detalles = detalles) 
    picking_data = Picking( estado = 1, id_usuario = id_usuario)
    picking_detalle = Picking_detalle(items = lista_items)
    
    result = await picking_service.create_picking(db, orden, picking_data, picking_detalle)
    if result.result == 1:
        return {"message": result.message, "picking_id": result.id}
    else:
        print(f"Error al crear el picking: {result.message}")
        raise HTTPException(status_code=400, detail=result.message)


@router.post("/import_orders")
async def import_orders(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    id_usuario: int = Depends(get_current_user_id),
):
    """Importa órdenes de salida y sus tareas de picking desde un CSV o XLSX.

    Debe incluir: ``Nro documento``, ``Razón social cliente factura``,
    ``Item``, ``Cantidad`` y ``Bodega``. También admite ``Fecha``, ``Estado``,
    ``Lote`` y ``Cliente factura``. Solo se importan bodegas que comiencen por
    ``M`` y las filas de un mismo documento se agrupan en una sola orden.
    """
    filename = file.filename or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in {"csv", "xlsx"}:
        raise HTTPException(status_code=400, detail="El archivo debe tener formato .csv o .xlsx.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo no puede superar 10 MB.")

    result = await picking_service.import_orders_file(db, content, extension, id_usuario)
    if result["result"] == 0:
        raise HTTPException(status_code=422, detail=result["message"])
    return result


@router.get("/{id_picking}/next_task")
async def next_task(
    id_picking: int,
    db: AsyncSession = Depends(get_db),
    id_usuario: int = Depends(get_current_user_id)
):
    """Obtiene la siguiente tarea pendiente de un picking."""
    
    result = await picking_service.get_next_task(db, id_picking)
    comp = result["completed"]
    print(f"Resultado de get_next_task: {result}")
    # Caso 1: El picking ya terminó
    if comp == True:
        return {
            "completed": True,
            "message": result.get(
                "message",
                "No hay más tareas pendientes. Picking completado."
            )
        }

    # Caso 2: Existe una tarea pendiente
    task = result.get("task")

    if task:
        return {
            "completed": False,
            "message": "Siguiente tarea encontrada.",
            "task_id": task.id,
            "id_item": task.id_item,
            "nombre_item": task.nombre_item,
            "cantidad": task.cantidad,
            "lote": task.lote,
            "id_posicion_origen": task.id_posicion_origen,
            "cod_posicion_origen": task.cod_posicion_origen
        }

    # Caso 3: Error inesperado
    raise HTTPException(
        status_code=404,
        detail=result.get("message", "No fue posible obtener la siguiente tarea.")
    )


@router.post("/{id_picking}/confirm_task")
async def confirm_task(
    id_picking: int,
    id_task: int = Body(..., embed=True),
    cod_posicion_escaneada: str = Body(..., embed=True),
    cod_item: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    id_usuario: int = Depends(get_current_user_id)
):
    """Confirma una tarea de picking después de escanear la posición de origen."""
    result = await picking_service.confirm_task(db, id_task, id_picking, cod_posicion_escaneada, cod_item, id_usuario)
    if result["result"] == 1:
        return result
    else:
        raise HTTPException(status_code=400, detail=result["message"])


@router.get("/list_picking_view")
async def list_picking_view(
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
):
    """Lista los pickings pendientes con su información detallada para la vista de la app movil."""
    picking_view_list = await picking_service.list_picking_view(db)
    if picking_view_list and picking_view_list[0].result == 1:
        return picking_view_list
    else:
        raise HTTPException(status_code=404, detail="No se encontraron pickings para mostrar en la vista")
    
@router.get("/list_orders")
async def get_list_orders(
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
    
):
    """Lista los pickings pendientes con su información detallada para la vista web"""
    order_list = await picking_service.get_list_orders(db)
    return order_list
    
