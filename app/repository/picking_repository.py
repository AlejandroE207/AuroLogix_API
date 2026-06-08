from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.picking_model import Picking, Picking_detalle, Picking_items
from app.model.picking_view_model import PickingView

async def create_picking(db: AsyncSession, picking_data: Picking):
    picking_result = Picking()
    query = text("""
                 INSERT INTO picking (id_posicion, estado, id_orden, id_usuario)
                 VALUES (:id_posicion, :estado, :id_orden, :id_usuario)
                RETURNING id, estado, id_orden, id_usuario
                 """)
    try:
        result = await db.execute(query, {"id_posicion": picking_data.id_posicion, "estado": picking_data.estado,
                                          "id_orden":picking_data.id_orden, "id_usuario":picking_data.id_usuario})
        row = result.mappings().first()
        await db.commit()
        if row:
            picking_result = Picking(**dict(row))
            picking_result.result = 1
            picking_result.message = "Picking creado exitosamente"
        else:
            picking_result.result = 0
            picking_result.message = "Error al crear el picking"
        return picking_result
    except Exception as e:
        print(f"Error al crear el picking: {e}")
        await db.rollback()
        picking_result.result = 0
        picking_result.message = "Error al crear el picking"
        return picking_result
    
async def create_picking_detalle(db: AsyncSession, picking_detalle: Picking_detalle):
    picking_detalle_result = Picking_detalle()
    query = text("""
                 INSERT INTO picking_detalle (id_picking, id_item, cantidad, lote)
                 VALUES (:id_picking, :id_item, :cantidad, :lote)
                 RETURNING id
                 """)
    try:
        inserted_ids = []
        if picking_detalle.items:
            for item in picking_detalle.items:
                result = await db.execute(query, {"id_picking": picking_detalle.id_picking, "id_item": item.id_item,
                                                  "cantidad": item.cantidad, "lote": item.lote})
                inserted_id = result.scalar_one()
                inserted_ids.append(inserted_id)
        
        await db.commit()
        
        if inserted_ids:
            picking_detalle_result = Picking_detalle(id=inserted_ids[0])
            picking_detalle_result.result = 1
            picking_detalle_result.message = f"Detalle del picking creado exitosamente - {len(inserted_ids)} items insertados"
        else:
            picking_detalle_result.result = 0
            picking_detalle_result.message = "No hay items para insertar en el picking"
        return picking_detalle_result
    except Exception as e:
        print(f"Error al crear el detalle del picking: {e}")
        await db.rollback()
        picking_detalle_result.result = 0
        picking_detalle_result.message = "Error al crear el detalle del picking"
        return picking_detalle_result
    
async def create_picking_task(db: AsyncSession, picking_task: Picking_detalle):
    picking_task_result = Picking_detalle()
    query = text("""
                 INSERT INTO picking_task (id_picking, id_item, cantidad, lote, id_posicion_origen, estado)
                 VALUES (:id_picking, :id_item, :cantidad, :lote, :id_posicion_origen, :estado)
                 RETURNING id
                 """)
    try:
        inserted_ids = []
        if picking_task.items:
            for item in picking_task.items:
                result = await db.execute(query, {"id_picking": picking_task.id_picking, "id_item": item.id_item,
                                                  "cantidad": item.cantidad, "lote": item.lote, "id_posicion_origen": item.id_posicion_origen, "estado": 1})
                inserted_id = result.scalar_one()
                inserted_ids.append(inserted_id)
        
        await db.commit()
        
        if inserted_ids:
            picking_task_result = Picking_detalle(id=inserted_ids[0])
            picking_task_result.result = 1
            picking_task_result.message = f"Tarea de picking creada exitosamente - {len(inserted_ids)} items insertados"
        else:
            picking_task_result.result = 0
            picking_task_result.message = "No hay items para insertar en la tarea de picking"
        return picking_task_result
    except Exception as e:
        print(f"Error al crear la tarea de picking: {e}")
        await db.rollback()
        picking_task_result.result = 0
        picking_task_result.message = "Error al crear la tarea de picking"
        return picking_task_result
    

async def get_next_task(db: AsyncSession, id_picking: int):
    """Obtiene la siguiente tarea pendiente de un picking."""
    task_result = Picking_items()
    query = text("""
                    SELECT pt.id, pt.id_picking, pt.id_item, i.descripcion ,pt.cantidad, pt.lote, pt.id_posicion_origen,p.cod_posicion, pt.estado
                    FROM picking_task as pt
                    INNER JOIN posiciones as p ON id_posicion_origen = p.id 
                    INNER JOIN items as i ON pt.id_item = i.id
                    WHERE pt.id_picking = :id_picking AND pt.estado = 1
                    ORDER BY id
                    LIMIT 1
                 """)

    try:
        result = await db.execute(query, {"id_picking": id_picking})
        row = result.mappings().first()
        if row:
            task_result.id_item = row["id_item"]
            task_result.nombre_item = row["descripcion"]
            task_result.cantidad = row["cantidad"]
            task_result.lote = row["lote"]
            task_result.id_posicion_origen = row["id_posicion_origen"]
            task_result.cod_posicion_origen = row["cod_posicion"]
            task_result.result = 1
            task_result.message = "Tarea obtenida exitosamente"
            # Agregar el ID de la tarea para referencia
            task_result.id = row["id"]
        else:
            task_result.result = 0
            task_result.message = "No hay tareas pendientes para este picking"
        return task_result
    except Exception as e:
        print(f"Error al obtener la siguiente tarea: {e}")
        task_result.result = 0
        task_result.message = "Error al obtener la siguiente tarea"
        return task_result


async def update_task_status(db: AsyncSession, id_task: int, estado: int):
    """Actualiza el estado de una tarea de picking."""
    query = text("""
                 UPDATE picking_task
                 SET estado = :estado
                 WHERE id = :id_task
                 """)
    try:
        await db.execute(query, {"id_task": id_task, "estado": estado})
        await db.commit()
        return {"result": 1, "message": "Estado de la tarea actualizado exitosamente"}
    except Exception as e:
        print(f"Error al actualizar el estado de la tarea: {e}")
        await db.rollback()
        return {"result": 0, "message": "Error al actualizar el estado de la tarea"}

async def complete_picking(db: AsyncSession, id_picking: int):
    """Marca un picking como completado cuando no hay más tareas pendientes."""
    query = text("""
                 UPDATE picking
                 SET estado = 3
                 WHERE id = :id_picking
                 """)
    try:
        await db.execute(query, {"id_picking": id_picking})
        await db.commit()
        return {"result": 1, "message": "Picking completado exitosamente"}
    except Exception as e:
        print(f"Error al completar el picking: {e}")
        await db.rollback()
        return {"result": 0, "message": "Error al completar el picking"}
    
async def list_picking_view(db:AsyncSession):
    picking_view_list = []
    query = text("""
                    SELECT pi.id, p.cod_posicion, ep.descripcion as estado, o.codigo as codigo_orden , u.nombre as usuario
                    FROM picking AS pi
                    LEFT JOIN posiciones AS p ON pi.id_posicion = p.id
                    INNER JOIN estado_picking AS ep ON pi.estado = ep.id
                    INNER JOIN orden_salida AS o ON pi.id_orden = o.id
                    INNER JOIN usuarios AS u ON pi.id_usuario = u.id
                    WHERE ep.descripcion = 'Pendiente';
                 """)
    try:
        result = await db.execute(query)
        rows = result.mappings().all()
        for row in rows:
            picking_view = PickingView(**dict(row))
            picking_view.result = 1
            picking_view.message = "Picking encontrado"
            picking_view_list.append(picking_view)
        if not picking_view_list:
            picking_view = PickingView()
            picking_view.result = 0
            picking_view.message = "No se encontraron pickings"
            picking_view_list.append(picking_view)
        return picking_view_list
    except Exception as e:
        print(f"Error al listar los pickings: {e}")
        picking_view = PickingView()
        picking_view.result = 0
        picking_view.message = "Error al listar los pickings"
        picking_view_list.append(picking_view)
        return picking_view_list