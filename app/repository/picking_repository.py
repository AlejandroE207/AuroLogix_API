from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.picking_model import Orden, Picking, Picking_detalle, Picking_items
from app.model.picking_view_model import PickingView


async def get_items_by_codes(db: AsyncSession, codes: list[str]):
    """Obtiene los artículos existentes para los códigos del archivo de importación."""
    if not codes:
        return {}
    query = text("""
        SELECT id, cod_item, descripcion FROM items
        WHERE CAST(cod_item AS TEXT) IN :codes
    """).bindparams(bindparam("codes", expanding=True))
    result = await db.execute(query, {"codes": codes})
    return {str(row["cod_item"]).strip(): dict(row) for row in result.mappings().all()}


async def get_inventory_for_items(db: AsyncSession, item_ids: list[int]):
    """Devuelve inventario apto para salida, priorizando la zona de picking."""
    if not item_ids:
        return {}
    query = text("""
        SELECT inv.id, inv.id_item, inv.id_posicion, inv.lote, inv.cantidad,
               inv.fecha_vencimiento, pos.cod_posicion, pos.reserva
        FROM inventario AS inv
        INNER JOIN posiciones AS pos ON pos.id = inv.id_posicion
        WHERE inv.id_item IN :item_ids
          AND inv.cantidad > 0
          AND pos.estado <> 3
          AND LOWER(TRIM(pos.reserva)) IN ('picking', 'abastecimiento')
        ORDER BY
            inv.id_item,
            CASE WHEN LOWER(TRIM(pos.reserva)) = 'picking' THEN 0 ELSE 1 END,
            inv.fecha_vencimiento NULLS LAST,
            pos.cod_posicion,
            inv.id
    """).bindparams(bindparam("item_ids", expanding=True))
    result = await db.execute(query, {"item_ids": item_ids})
    inventory: dict[int, list[dict]] = {}
    for row in result.mappings().all():
        inventory.setdefault(row["id_item"], []).append(dict(row))
    return inventory


async def get_existing_order_codes(db: AsyncSession, codes: list[str]) -> set[str]:
    if not codes:
        return set()
    query = text("""SELECT codigo FROM orden_salida WHERE codigo IN :codes""").bindparams(
        bindparam("codes", expanding=True)
    )
    result = await db.execute(query, {"codes": codes})
    return {str(row["codigo"]).strip() for row in result.mappings().all()}


async def create_bulk_pickings(db: AsyncSession, orders: list[dict]) -> list[dict]:
    """Inserta órdenes, pickings y detalles sin asignar todavía el inventario."""
    created = []
    order_query = text("""
        INSERT INTO orden_salida (codigo, cliente, estado, id_usuario, tipo, detalles)
        VALUES (:codigo, :cliente, 1, :id_usuario, :tipo, :detalles) RETURNING id
    """)
    picking_query = text("""
        INSERT INTO picking (id_posicion, estado, id_orden, id_usuario)
        VALUES (NULL, 1, :id_orden, :id_usuario) RETURNING id
    """)
    detail_query = text("""
        INSERT INTO picking_detalle (id_picking, id_item, cantidad, lote)
        VALUES (:id_picking, :id_item, :cantidad, :lote)
    """)
    for order in orders:
        order_id = (await db.execute(order_query, order)).mappings().one()["id"]
        picking_id = (await db.execute(picking_query, {
            "id_orden": order_id, "id_usuario": order["id_usuario"]
        })).mappings().one()["id"]
        for item in order["items"]:
            values = {**item, "id_picking": picking_id}
            await db.execute(detail_query, values)
        created.append({"codigo": order["codigo"], "order_id": order_id, "picking_id": picking_id})
    return created


async def get_picking_details(db: AsyncSession, id_picking: int) -> list[dict]:
    query = text("""
        SELECT pd.id_item, i.cod_item, pd.cantidad, pd.lote
        FROM picking_detalle AS pd
        INNER JOIN items AS i ON i.id = pd.id_item
        WHERE pd.id_picking = :id_picking
        ORDER BY pd.id
    """)
    result = await db.execute(query, {"id_picking": id_picking})
    return [dict(row) for row in result.mappings().all()]


async def count_picking_tasks(db: AsyncSession, id_picking: int) -> int:
    query = text("SELECT COUNT(*) FROM picking_task WHERE id_picking = :id_picking")
    result = await db.execute(query, {"id_picking": id_picking})
    return int(result.scalar_one())


async def count_pending_picking_tasks(db: AsyncSession, id_picking: int) -> int:
    query = text("""
        SELECT COUNT(*)
        FROM picking_task
        WHERE id_picking = :id_picking AND estado = 1
    """)
    result = await db.execute(query, {"id_picking": id_picking})
    return int(result.scalar_one())


async def insert_picking_tasks(db: AsyncSession, id_picking: int, tasks: list[dict]) -> None:
    query = text("""
        INSERT INTO picking_task
            (id_picking, id_item, cantidad, lote, id_posicion_origen, estado)
        VALUES
            (:id_picking, :id_item, :cantidad, :lote, :id_posicion_origen, 1)
    """)
    for task in tasks:
        await db.execute(query, {**task, "id_picking": id_picking})




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
                    SELECT pt.id, pt.id_picking, pt.id_item, i.cod_item, i.descripcion,
                           pt.cantidad, pt.lote, pt.id_posicion_origen, p.cod_posicion,
                           p.reserva, pt.estado
                    FROM picking_task as pt
                    INNER JOIN posiciones as p ON id_posicion_origen = p.id 
                    INNER JOIN items as i ON pt.id_item = i.id
                    WHERE pt.id_picking = :id_picking AND pt.estado = 1
                    ORDER BY
                        CASE
                            WHEN LOWER(TRIM(p.reserva)) = 'picking' THEN 0
                            WHEN LOWER(TRIM(p.reserva)) = 'abastecimiento' THEN 1
                            ELSE 2
                        END,
                        p.cod_posicion,
                        pt.id
                    LIMIT 1
                 """)

    try:
        result = await db.execute(query, {"id_picking": id_picking})
        row = result.mappings().first()
        if row:
            task_result.id_item = row["id_item"]
            task_result.cod_item = row["cod_item"]
            task_result.nombre_item = row["descripcion"]
            task_result.cantidad = row["cantidad"]
            task_result.lote = row["lote"]
            task_result.id_posicion_origen = row["id_posicion_origen"]
            task_result.cod_posicion_origen = row["cod_posicion"]
            task_result.reserva = row["reserva"]
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


async def get_task_by_id(db: AsyncSession, id_picking: int, id_task: int):
    """Obtiene una tarea concreta y valida que pertenezca al picking."""
    query = text("""
        SELECT pt.id, pt.id_item, i.cod_item, i.descripcion, pt.cantidad,
               pt.lote, pt.id_posicion_origen, p.cod_posicion, p.reserva, pt.estado
        FROM picking_task AS pt
        INNER JOIN posiciones AS p ON p.id = pt.id_posicion_origen
        INNER JOIN items AS i ON i.id = pt.id_item
        WHERE pt.id = :id_task AND pt.id_picking = :id_picking
    """)
    result = await db.execute(query, {"id_task": id_task, "id_picking": id_picking})
    row = result.mappings().first()
    if not row:
        return None
    return Picking_items(
        id=row["id"], id_item=row["id_item"], cod_item=row["cod_item"],
        nombre_item=row["descripcion"], cantidad=row["cantidad"], lote=row["lote"],
        id_posicion_origen=row["id_posicion_origen"],
        cod_posicion_origen=row["cod_posicion"], reserva=row["reserva"],
        estado=row["estado"], result=1,
    )


async def list_picking_tasks(db: AsyncSession, id_picking: int) -> list[dict]:
    """Lista las extracciones pendientes y realizadas de un picking."""
    query = text("""
        SELECT pt.id AS task_id, pt.id_item, i.cod_item, i.descripcion AS nombre_item,
               pt.cantidad, pt.lote, pt.id_posicion_origen,
               p.cod_posicion AS cod_posicion_origen, p.reserva, pt.estado,
               CASE pt.estado
                   WHEN 1 THEN 'pendiente'
                   WHEN 3 THEN 'realizada'
                   ELSE 'en_proceso'
               END AS estado_descripcion
        FROM picking_task AS pt
        INNER JOIN posiciones AS p ON p.id = pt.id_posicion_origen
        INNER JOIN items AS i ON i.id = pt.id_item
        WHERE pt.id_picking = :id_picking
        ORDER BY CASE WHEN pt.estado = 1 THEN 0 ELSE 1 END, pt.id
    """)
    result = await db.execute(query, {"id_picking": id_picking})
    return [dict(row) for row in result.mappings().all()]


async def update_task_status(
    db: AsyncSession, id_task: int, estado: int, commit: bool = True
):
    """Actualiza el estado de una tarea de picking."""
    query = text("""
                 UPDATE picking_task
                 SET estado = :estado
                 WHERE id = :id_task
                 """)
    try:
        await db.execute(query, {"id_task": id_task, "estado": estado})
        if commit:
            await db.commit()
        return {"result": 1, "message": "Estado de la tarea actualizado exitosamente"}
    except Exception as e:
        print(f"Error al actualizar el estado de la tarea: {e}")
        if commit:
            await db.rollback()
        return {"result": 0, "message": "Error al actualizar el estado de la tarea"}

async def complete_picking(
    db: AsyncSession, id_picking: int, commit: bool = True
):
    """Marca un picking como completado cuando no hay más tareas pendientes."""
    query = text("""
                 UPDATE picking
                 SET estado = 3
                 WHERE id = :id_picking
                 """)
    try:
        await db.execute(query, {"id_picking": id_picking})
        if commit:
            await db.commit()
        return {"result": 1, "message": "Picking completado exitosamente"}
    except Exception as e:
        print(f"Error al completar el picking: {e}")
        if commit:
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
    
async def get_order_id_by_picking(db: AsyncSession, id_picking: int):
    """Obtiene el ID de la orden asociada a un picking."""
    order_data = Orden()
    query = text("""
                    SELECT p.id_orden as id, o.estado
                    FROM picking AS p
                    JOIN orden_salida AS o ON o.id = p.id_orden
                    WHERE p.id = :id_picking;
                 """)
    try:
        result = await db.execute(query, {"id_picking": id_picking})
        row = result.mappings().first()
        if row:
            order_data = Orden(**dict(row))
            order_data.result = 1
            order_data.message = "ID de la orden obtenido exitosamente"
            return order_data
        else:
            order_data.result = 0
            order_data.message = "No se encontró la orden para este picking"
            return order_data
    except Exception as e:
        print(f"Error al obtener el ID de la orden por picking: {e}")
        return None
    
async def delete_task(db: AsyncSession, id_task: int):
    """Elimina una tarea de picking."""
    query = text("""
                 DELETE FROM picking_task
                 WHERE id = :id_task
                 """)
    try:
        await db.execute(query, {"id_task": id_task})
        await db.commit()
        return {"result": 1, "message": "Tarea eliminada exitosamente"}
    except Exception as e:
        print(f"Error al eliminar la tarea: {e}")
        await db.rollback()
        return {"result": 0, "message": "Error al eliminar la tarea"}
