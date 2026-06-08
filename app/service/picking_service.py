from app.repository import picking_repository, order_repository, inventory_repository, motion_repository
from app.model.picking_model import Orden, Picking, Picking_detalle
from app.model.inventory_model import Motion
from datetime import datetime

async def create_picking(db, orden: Orden, picking_data: Picking, picking_detalle: Picking_detalle):
    create_order = await order_repository.create_order(db, orden)
    if create_order.result == 1:
        picking_data.id_orden = create_order.id
        create_picking_data = await picking_repository.create_picking(db, picking_data)
        if create_picking_data.result == 1:
            picking_detalle.id_picking = create_picking_data.id
            create_picking_detalle = await picking_repository.create_picking_detalle(db, picking_detalle)
            if create_picking_detalle.result == 1:
                for item in picking_detalle.items:
                    item_data = await inventory_repository.get_position_by_item(db, item.id_item, item.lote)
                    item.id_posicion_origen = item_data.id_posicion_origen
                create_picking_task = await picking_repository.create_picking_task(db, picking_detalle)
                if create_picking_task.result == 1:
                    return create_picking_data
                else:
                    return create_picking_data
            else:
                return create_picking_data
        else:
            return create_picking_data
    else:
        return picking_data
    


async def get_next_task(db, id_picking: int):
    """Obtiene la siguiente tarea pendiente del picking."""
    task = await picking_repository.get_next_task(db, id_picking)
    if task.result == 0:
        result = await picking_repository.complete_picking(db, id_picking)
        if result["result"] == 1:
            return {"completed":True, "message": "No hay más tareas pendientes. Picking completado."}
        else:
            return {"completed":False, "message": "Error al completar el picking"}
    return {"completed":False , "task": task}


async def confirm_task(db, id_task: int, id_picking: int, cod_posicion_escaneada: int, id_usuario: int):
    """
    Confirma una tarea de picking después de escanear la posición de origen.
    Registra el movimiento y actualiza el inventario.
    """
    # Obtener la información de la tarea
    task = await picking_repository.get_next_task(db, id_picking)
    
    if task.result == 0:
        return {"result": 0, "message": "Tarea no encontrada"}
    
    # Validar que la posición escaneada sea correcta
    if cod_posicion_escaneada != task.cod_posicion_origen:
        return {"result": 0, "message": f"Posición incorrecta. Se esperaba {task.id_posicion_origen}, se escaneó {cod_posicion_escaneada}"}
    
    try:
        # Crear registro de movimiento (salida/picking)
        # tipo_movimiento: 1=ENTRADA, 2=SALIDA
        motion = Motion(
            tipo_movimiento=2,  # SALIDA
            id_item=task.id_item,
            lote=task.lote,
            cantidad=task.cantidad,
            posicion_origen_id=task.id_posicion_origen,
            posicion_destino_id=None,  # No hay posición destino en picking
            fecha=datetime.now(),
            id_usuario=id_usuario
        )
        
        motion_result = await motion_repository.create_motion_output(db, motion)
        
        if motion_result.result == 0:
            return {"result": 0, "message": "Error al registrar el movimiento"}
        
        # Actualizar inventario (restar la cantidad)
        inventory_result = await inventory_repository.update_inventory_quantity(
            db, task.id_posicion_origen, task.id_item, task.lote, task.cantidad
        )
        
        if inventory_result["result"] == 0:
            return {"result": 0, "message": "Error al actualizar el inventario"}
        
        # Actualizar estado de la tarea a completada (estado = 2)
        task_update = await picking_repository.update_task_status(db, id_task, 3)
        
        if task_update["result"] == 0:
            return {"result": 0, "message": "Error al actualizar el estado de la tarea"}
        
        return {"result": 1, "message": "Tarea confirmada exitosamente", 
                "id_movimiento": motion_result.id}
        
    except Exception as e:
        print(f"Error al confirmar la tarea: {e}")
        return {"result": 0, "message": f"Error al confirmar la tarea: {str(e)}"}
    
    
async def list_picking_view(db):
    """Lista los pickings con su información detallada para la vista."""
    picking_view_list = await picking_repository.list_picking_view(db)
    return picking_view_list