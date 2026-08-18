from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# NOTA IMPORTANTE:
# Las funciones de escritura de este repositorio NO hacen commit ni rollback.
# El servicio (adjustment_service) es el responsable de confirmar o revertir
# la transaccion completa, de modo que la actualizacion del inventario, el
# registro en el historial (inventario_ajustes) y los movimientos queden
# grabados de forma atomica: o se guarda todo, o no se guarda nada.


async def get_inventory_record(db: AsyncSession, id_inventario: int):
    """Obtiene un registro de inventario por su id, con datos del item y la posicion."""
    query = text("""
                 SELECT i.id, i.id_posicion, p.cod_posicion, i.id_item,
                        it.cod_item, it.descripcion, it.unidad_medida,
                        i.cantidad, i.lote, i.detalles, i.fecha_vencimiento
                 FROM inventario AS i
                 INNER JOIN posiciones AS p ON i.id_posicion = p.id
                 INNER JOIN items AS it ON i.id_item = it.id
                 WHERE i.id = :id_inventario
                 """)
    try:
        result = await db.execute(query, {"id_inventario": id_inventario})
        row = result.mappings().first()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error al obtener el registro de inventario: {e}")
        return None


async def get_inventory_by_position(db: AsyncSession, id_posicion: int):
    """Lista los registros de inventario de una posicion especifica.

    Pensado para la pantalla de edicion: el usuario selecciona la posicion
    y ve todos los items/lotes que contiene para elegir cual actualizar.
    """
    query = text("""
                 SELECT i.id, i.id_posicion, p.cod_posicion, i.id_item,
                        it.cod_item, it.tipo_item, it.descripcion, it.unidad_medida,
                        i.cantidad, i.lote, i.detalles, i.fecha_vencimiento
                 FROM inventario AS i
                 INNER JOIN posiciones AS p ON i.id_posicion = p.id
                 INNER JOIN items AS it ON i.id_item = it.id
                 WHERE i.id_posicion = :id_posicion
                 ORDER BY it.descripcion ASC, i.lote ASC NULLS LAST
                 """)
    try:
        result = await db.execute(query, {"id_posicion": id_posicion})
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error al obtener el inventario de la posicion: {e}")
        return []


async def item_exists(db: AsyncSession, id_item: int):
    """Verifica que el item exista antes de asignarlo a una posicion."""
    query = text("SELECT id FROM items WHERE id = :id_item")
    try:
        result = await db.execute(query, {"id_item": id_item})
        return result.mappings().first() is not None
    except Exception as e:
        print(f"Error al validar el item: {e}")
        return False


async def find_merge_target(db: AsyncSession, id_posicion: int, id_item: int, lote: str, exclude_id: int):
    """Busca otro registro de inventario en la misma posicion con el mismo
    item + lote (excluyendo el registro que se esta editando). Si existe,
    la edicion debe fusionarse con ese registro para no duplicar filas."""
    query = text("""
                 SELECT id, id_posicion, id_item, cantidad, lote, fecha_vencimiento
                 FROM inventario
                 WHERE id_posicion = :id_posicion
                   AND id_item = :id_item
                   AND lote IS NOT DISTINCT FROM :lote
                   AND id <> :exclude_id
                 """)
    try:
        result = await db.execute(query, {
            "id_posicion": id_posicion,
            "id_item": id_item,
            "lote": lote,
            "exclude_id": exclude_id,
        })
        row = result.mappings().first()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error al buscar registro para fusion: {e}")
        return None


async def update_record(db: AsyncSession, id_inventario: int, id_item: int, lote: str,
                        cantidad: float, fecha_vencimiento: datetime):
    """Actualiza los campos editables de un registro de inventario. SIN commit."""
    query = text("""
                 UPDATE inventario
                 SET id_item = :id_item,
                     lote = :lote,
                     cantidad = :cantidad,
                     fecha_vencimiento = :fecha_vencimiento
                 WHERE id = :id_inventario
                 RETURNING id
                 """)
    result = await db.execute(query, {
        "id_inventario": id_inventario,
        "id_item": id_item,
        "lote": lote,
        "cantidad": cantidad,
        "fecha_vencimiento": fecha_vencimiento,
    })
    return result.mappings().first() is not None


async def set_quantity(db: AsyncSession, id_inventario: int, cantidad: float):
    """Fija la cantidad de un registro. Si queda en 0, el trigger de la BD
    elimina la fila automaticamente. SIN commit."""
    query = text("""
                 UPDATE inventario
                 SET cantidad = :cantidad
                 WHERE id = :id_inventario
                 RETURNING id
                 """)
    try:
        if cantidad > 0:    
            result = await db.execute(query, {"id_inventario": id_inventario, "cantidad": cantidad})
            return result.mappings().first() is not None
        else:
            return True
    except Exception as e:
        print(f"Error al fijar la cantidad del registro de inventario: {e}")
        return False


async def delete_record(db: AsyncSession, id_inventario: int):
    """Elimina explicitamente un registro de inventario. SIN commit.

    No se depende del trigger de la BD (que elimina filas con cantidad 0)
    porque ese trigger puede no dispararse en todos los flujos; la
    eliminacion queda garantizada desde la aplicacion. Si el trigger ya
    borro la fila, esta operacion simplemente no afecta ninguna fila y
    tambien se considera exitosa (idempotente).
    """
    query = text("""
                 DELETE FROM inventario
                 WHERE id = :id_inventario
                 """)
    await db.execute(query, {"id_inventario": id_inventario})
    return True


async def add_quantity_to_target(db: AsyncSession, id_inventario: int, cantidad_sumar: float,
                                 fecha_vencimiento: datetime):
    """Suma cantidad a un registro destino de fusion y actualiza su fecha de
    vencimiento con el valor indicado por el usuario en la edicion. SIN commit."""
    query = text("""
                 UPDATE inventario
                 SET cantidad = cantidad + :cantidad_sumar,
                     fecha_vencimiento = :fecha_vencimiento
                 WHERE id = :id_inventario
                 RETURNING id, cantidad
                 """)
    result = await db.execute(query, {
        "id_inventario": id_inventario,
        "cantidad_sumar": cantidad_sumar,
        "fecha_vencimiento": fecha_vencimiento,
    })
    return result.mappings().first() is not None


async def get_inventory_by_position_item_lote(db: AsyncSession, id_posicion: int, id_item: int, lote: str):
    """Busca un registro de inventario existente para una combinacion exacta
    de posicion + item + lote. Se usa en el registro de conteo ciclico para
    decidir si se crea un registro nuevo o se reemplaza la cantidad del
    existente."""
    query = text("""
                 SELECT id, id_posicion, id_item, cantidad, lote, fecha_vencimiento
                 FROM inventario
                 WHERE id_posicion = :id_posicion
                   AND id_item = :id_item
                   AND lote IS NOT DISTINCT FROM :lote
                 """)
    try:
        result = await db.execute(query, {
            "id_posicion": id_posicion,
            "id_item": id_item,
            "lote": lote,
        })
        row = result.mappings().first()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error al buscar el inventario por posicion/item/lote: {e}")
        return None


async def set_position_occupied(db: AsyncSession, id_posicion: int):
    """Marca una posicion como ocupada (estado 2) si no lo estaba ya. SIN commit."""
    query = text("""
                 UPDATE posiciones
                 SET estado = 2
                 WHERE id = :id_posicion AND estado <> 2
                 """)
    await db.execute(query, {"id_posicion": id_posicion})
    return True


async def insert_adjustment(db: AsyncSession, data: dict):
    """Inserta el registro de auditoria en inventario_ajustes. SIN commit."""
    query = text("""
                 INSERT INTO inventario_ajustes (
                     id_inventario, id_inventario_destino, id_posicion, tipo_ajuste,
                     id_item_anterior, id_item_nuevo,
                     lote_anterior, lote_nuevo,
                     cantidad_anterior, cantidad_nueva,
                     fecha_vencimiento_anterior, fecha_vencimiento_nueva,
                     motivo, id_usuario, fecha
                 )
                 VALUES (
                     :id_inventario, :id_inventario_destino, :id_posicion, :tipo_ajuste,
                     :id_item_anterior, :id_item_nuevo,
                     :lote_anterior, :lote_nuevo,
                     :cantidad_anterior, :cantidad_nueva,
                     :fecha_vencimiento_anterior, :fecha_vencimiento_nueva,
                     :motivo, :id_usuario, :fecha
                 )
                 RETURNING id
                 """)
    result = await db.execute(query, data)
    row = result.mappings().first()
    return row["id"] if row else None


async def insert_adjustment_motion(db: AsyncSession, tipo_movimiento: int, id_item: int,
                                   lote: str, cantidad: float, id_posicion: int,
                                   id_usuario: int, fecha: datetime):
    """Inserta un movimiento de ajuste (tipo 4 = ajuste positivo, 5 = ajuste negativo).

    - Ajuste positivo: la posicion 'recibe' cantidad -> posicion_destino_id.
    - Ajuste negativo: la posicion 'pierde' cantidad -> posicion_origen_id.
    SIN commit.
    """
    posicion_origen_id = id_posicion if tipo_movimiento == 5 else None
    posicion_destino_id = id_posicion if tipo_movimiento == 4 else None

    query = text("""
                 INSERT INTO movimientos (tipo_movimiento, id_item, lote, cantidad,
                     posicion_origen_id, posicion_destino_id, fecha, id_usuario)
                 VALUES (:tipo_movimiento, :id_item, :lote, :cantidad,
                     :posicion_origen_id, :posicion_destino_id, :fecha, :id_usuario)
                 RETURNING id
                 """)
    result = await db.execute(query, {
        "tipo_movimiento": tipo_movimiento,
        "id_item": id_item,
        "lote": lote,
        "cantidad": cantidad,
        "posicion_origen_id": posicion_origen_id,
        "posicion_destino_id": posicion_destino_id,
        "fecha": fecha,
        "id_usuario": id_usuario,
    })
    row = result.mappings().first()
    return row["id"] if row else None


async def list_adjustments(db: AsyncSession, cod_posicion: str = None, item: str = None,
                           desde_fecha: datetime = None, hasta_fecha: datetime = None,
                           limite: int = 50, offset: int = 0):
    """Lista el historial de ajustes con filtros opcionales y paginacion."""
    query_str = """
        SELECT a.id,
               a.id_inventario,
               a.id_inventario_destino,
               a.tipo_ajuste,
               p.cod_posicion,
               ita.cod_item AS cod_item_anterior,
               ita.descripcion AS item_anterior,
               itn.cod_item AS cod_item_nuevo,
               itn.descripcion AS item_nuevo,
               a.lote_anterior,
               a.lote_nuevo,
               a.cantidad_anterior,
               a.cantidad_nueva,
               a.fecha_vencimiento_anterior,
               a.fecha_vencimiento_nueva,
               a.motivo,
               u.nombre AS usuario,
               a.fecha
        FROM inventario_ajustes AS a
        INNER JOIN posiciones AS p ON a.id_posicion = p.id
        LEFT JOIN items AS ita ON a.id_item_anterior = ita.id
        LEFT JOIN items AS itn ON a.id_item_nuevo = itn.id
        INNER JOIN usuarios AS u ON a.id_usuario = u.id
    """

    filtros = []
    params = {"limite": limite, "offset": offset}

    if cod_posicion:
        filtros.append("p.cod_posicion ILIKE :cod_posicion")
        params["cod_posicion"] = f"%{cod_posicion}%"

    if item:
        filtros.append("""(
            ita.cod_item ILIKE :item OR ita.descripcion ILIKE :item
            OR itn.cod_item ILIKE :item OR itn.descripcion ILIKE :item
        )""")
        params["item"] = f"%{item}%"

    if desde_fecha:
        filtros.append("a.fecha >= :desde_fecha")
        params["desde_fecha"] = desde_fecha

    if hasta_fecha:
        filtros.append("a.fecha <= :hasta_fecha")
        params["hasta_fecha"] = hasta_fecha

    if filtros:
        query_str += " WHERE " + " AND ".join(filtros)

    query_str += " ORDER BY a.fecha DESC LIMIT :limite OFFSET :offset"

    try:
        result = await db.execute(text(query_str), params)
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error al listar el historial de ajustes: {e}")
        return []