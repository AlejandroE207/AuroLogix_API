import re
import random
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.inventory_model import Motion
from app.model.transfer_model import Transfer
from app.repository import item_repository, position_repository


TYPE_RULES = {
    "MP":  {"reserve": "abastecimiento"},
    "PT":  {"reserve": "abastecimiento"},
    "ME":  {"reserve": "complementario"},
    "MEE": {"reserve": "complementario"},
}


def _natural_sort_key(value: str):
    tokens = []
    for part in re.split(r"(\d+)", value or ""):
        if not part:
            continue
        if part.isdigit():
            tokens.append((1, int(part)))
        else:
            tokens.append((0, part.upper()))
    return tuple(tokens)


def _build_position_groups(rows: list[dict[str, Any]]):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["bodega"], row["reserva"] or "")].append(row)

    for group_rows in grouped.values():
        group_rows.sort(key=lambda row: _natural_sort_key(row["cod_posicion"]))

    return grouped


def _filter_positions_for_type(
    rows: list[dict[str, Any]],
    type_item: str,
    only_free: bool = False,
    allow_picking: bool = False,
):
    rule = TYPE_RULES.get(type_item)
    if not rule:
        return []

    allowed_reserves = {rule["reserve"]}
    if allow_picking:
        allowed_reserves.add("picking")

    allowed_rows = []
    for row in rows:
        reserve = (row["reserva"] or "").strip().lower()
        if reserve not in allowed_reserves:
            continue
        if only_free and row["estado"] != 1:
            continue
        allowed_rows.append(row)

    return allowed_rows


async def get_inventory_by_id(db: AsyncSession, id_inventory: int):
    query = text("""
                 SELECT id, id_posicion, id_item, cantidad, lote, fecha_vencimiento, detalles
                 FROM inventario
                 WHERE id = :id_inventory
                 """)
    result_data = Transfer()

    try:
        result = await db.execute(query, {"id_inventory": id_inventory})
        row = result.mappings().first()
        if row:
            result_data.id = row["id"]
            result_data.id_inventario = row["id"]
            result_data.posicion_origen_id = row["id_posicion"]
            result_data.id_item = row["id_item"]
            result_data.cantidad = row["cantidad"]
            result_data.lote = row["lote"]
            result_data.fecha_vencimiento = row["fecha_vencimiento"]
            result_data.result = 1
            result_data.message = "Inventario encontrado"
        else:
            result_data.result = 0
            result_data.message = "Inventario no encontrado"
        return result_data
    except Exception as e:
        print(f"Error al obtener el inventario por id: {e}")
        result_data.result = 0
        result_data.message = "Error al obtener el inventario"
        return result_data


async def get_transfer_task_by_id(db: AsyncSession, id_task: int):
    query = text("""
                 SELECT id, id_inventario, posicion_destino_id, id_usuario, fecha, estado,
                        posicion_sugerida_id, cantidad
                 FROM traslado_task
                 WHERE id = :id_task
                 """)
    result_data = Transfer()

    try:
        result = await db.execute(query, {"id_task": id_task})
        row = result.mappings().first()
        if row:
            result_data = Transfer(**dict(row))
            result_data.result = 1
            result_data.message = "Tarea encontrada"
        else:
            result_data.result = 0
            result_data.message = "Tarea no encontrada"
        return result_data
    except Exception as e:
        print(f"Error al obtener la tarea de traslado: {e}")
        result_data.result = 0
        result_data.message = "Error al obtener la tarea de traslado"
        return result_data


async def create_transfer_task(
    db: AsyncSession,
    id_inventario: int,
    posicion_destino_id: int,
    posicion_sugerida_id: int,
    cantidad: float,
    id_usuario: int,
):
    transfer_data = Transfer()
    query = text("""
                 INSERT INTO traslado_task (
                    id_inventario,
                    posicion_destino_id,
                    id_usuario,
                    fecha,
                    estado,
                    posicion_sugerida_id,
                    cantidad
                 )
                 VALUES (
                    :id_inventario,
                    :posicion_destino_id,
                    :id_usuario,
                    :fecha,
                    :estado,
                    :posicion_sugerida_id,
                    :cantidad
                 )
                 RETURNING id, id_inventario, posicion_destino_id, id_usuario, fecha, estado, posicion_sugerida_id, cantidad
                 """)

    try:
        result = await db.execute(
            query,
            {
                "id_inventario": id_inventario,
                "posicion_destino_id": posicion_destino_id,
                "id_usuario": id_usuario,
                "fecha": datetime.now(),
                "estado": 1,
                "posicion_sugerida_id": posicion_sugerida_id,
                "cantidad": cantidad,
            },
        )
        row = result.mappings().first()
        if row:
            transfer_data = Transfer(**dict(row))
            transfer_data.result = 1
            transfer_data.message = "Tarea de traslado creada exitosamente"
        else:
            transfer_data.result = 0
            transfer_data.message = "Error al crear la tarea de traslado"
        return transfer_data
    except Exception as e:
        print(f"Error al crear la tarea de traslado: {e}")
        transfer_data.result = 0
        transfer_data.message = "Error al crear la tarea de traslado"
        return transfer_data


async def update_transfer_task_state(db: AsyncSession, id_task: int, estado: int):
    query = text("""
                 UPDATE traslado_task
                 SET estado = :estado
                 WHERE id = :id_task
                 RETURNING id
                 """)
    try:
        result = await db.execute(query, {"estado": estado, "id_task": id_task})
        row = result.mappings().first()
        if row:
            return {"result": 1, "message": "Estado de la tarea actualizado", "id": row["id"]}
        return {"result": 0, "message": "No se pudo actualizar la tarea"}
    except Exception as e:
        print(f"Error al actualizar el estado de la tarea: {e}")
        return {"result": 0, "message": "Error al actualizar la tarea"}


async def get_positions_catalog(db: AsyncSession):
    """
    Trae todas las posiciones con su conteo de inventario en UN solo query.
    Se usa como fuente única en manual_positions y confirm_transfer para
    evitar múltiples viajes a la BD.
    """
    query = text("""
                 SELECT p.id, p.cod_posicion, p.bodega, p.estado, p.reserva,
                        COUNT(i.id) AS inventario_count
                 FROM posiciones p
                 LEFT JOIN inventario i ON i.id_posicion = p.id
                 GROUP BY p.id, p.cod_posicion, p.bodega, p.estado, p.reserva
                 ORDER BY p.bodega ASC, p.id ASC
                 """)

    try:
        result = await db.execute(query)
        rows = [dict(row) for row in result.mappings().all()]
        return rows
    except Exception as e:
        print(f"Error al obtener el catálogo de posiciones: {e}")
        return []


async def get_manual_positions_for_inventory(db: AsyncSession, id_inventory: int):
    inventory_data = await get_inventory_by_id(db, id_inventory)
    if inventory_data.result != 1:
        return {"result": 0, "message": inventory_data.message, "data": []}

    item_type = await item_repository.get_item_type_by_id(db, inventory_data.id_item)
    if not item_type:
        return {"result": 0, "message": "No se pudo determinar el tipo de item", "data": []}

    positions = await get_positions_catalog(db)
    allowed_positions = _filter_positions_for_type(
        positions,
        item_type,
        only_free=False,
        allow_picking=True,
    )

    return {
        "result": 1,
        "message": "Posiciones manuales obtenidas exitosamente",
        "data": [
            {
                **position,
                "ocupado": position["inventario_count"] > 0,
                "permitido": True,
            }
            for position in allowed_positions
        ],
    }


async def get_auto_suggestion_for_inventory(db: AsyncSession, id_inventory: int):
    inventory_data = await get_inventory_by_id(db, id_inventory)
    if inventory_data.result != 1:
        return {"result": 0, "message": inventory_data.message}

    item_type = await item_repository.get_item_type_by_id(db, inventory_data.id_item)
    if not item_type:
        return {"result": 0, "message": "No se pudo determinar el tipo de item"}

    positions = await get_positions_catalog(db)
    allowed_positions = _filter_positions_for_type(positions, item_type, only_free=True)

    if not allowed_positions:
        return {"result": 0, "message": "No hay posiciones libres que cumplan las reglas de ubicación"}

    suggested_position = random.choice(allowed_positions)
    return {
        "result": 1,
        "message": "Posición sugerida generada exitosamente",
        "posicion_sugerida_id": suggested_position["id"],
        "posicion_destino_id": suggested_position["id"],
        "cod_posicion_sugerida": suggested_position["cod_posicion"],
        "cod_posicion_destino": suggested_position["cod_posicion"],
        "data": suggested_position,
    }


async def create_motion_transfer(db: AsyncSession, motion: Motion):
    query = text("""
                 INSERT INTO movimientos (
                    tipo_movimiento,
                    id_item,
                    lote,
                    cantidad,
                    posicion_origen_id,
                    posicion_destino_id,
                    fecha,
                    id_usuario
                 )
                 VALUES (
                    :tipo_movimiento,
                    :id_item,
                    :lote,
                    :cantidad,
                    :posicion_origen_id,
                    :posicion_destino_id,
                    :fecha,
                    :id_usuario
                 )
                 RETURNING id
                 """)
    result_data = Transfer()

    try:
        result = await db.execute(
            query,
            {
                "tipo_movimiento": motion.tipo_movimiento,
                "id_item": motion.id_item,
                "lote": motion.lote,
                "cantidad": motion.cantidad,
                "posicion_origen_id": motion.posicion_origen_id,
                "posicion_destino_id": motion.posicion_destino_id,
                "fecha": motion.fecha,
                "id_usuario": motion.id_usuario,
            },
        )
        row = result.mappings().first()
        if row:
            result_data.id = row["id"]
            result_data.result = 1
            result_data.message = "Movimiento registrado exitosamente"
        else:
            result_data.result = 0
            result_data.message = "Error al registrar el movimiento"
        return result_data
    except Exception as e:
        print(f"Error al registrar el movimiento de traslado: {e}")
        result_data.result = 0
        result_data.message = "Error al registrar el movimiento"
        return result_data


async def confirm_transfer_core(
    db: AsyncSession,
    id_task: int,
    cod_posicion_escaneada: str,
    id_usuario: int,
):
    # ── 1. Cargar tarea ───────────────────────────────────────────────────────
    task = await get_transfer_task_by_id(db, id_task)
    if task.result != 1:
        return task

    if task.estado == 3:
        task.result = 0
        task.message = "La tarea de traslado ya fue confirmada"
        return task

    if task.id_inventario is None:
        task.result = 0
        task.message = "La tarea no tiene inventario asociado; probablemente fue eliminado"
        return task

    # ── 2. Cargar inventario (UNA sola vez — fix: era llamado dos veces) ─────
    inventory_data = await get_inventory_by_id(db, task.id_inventario)
    if inventory_data.result != 1:
        return inventory_data

    # ── 3. Cargar catálogo de posiciones (UNA sola vez — fix: era llamado
    #       3 veces en total entre get_manual_positions y confirm) ─────────────
    positions = await get_positions_catalog(db)

    scanned_position = next(
        (p for p in positions if p["cod_posicion"] == cod_posicion_escaneada), None
    )
    if not scanned_position:
        task.result = 0
        task.message = "La posición escaneada no existe"
        return task

    if scanned_position["id"] != task.posicion_sugerida_id:
        task.result = 0
        task.message = "La posición escaneada no coincide con la posición sugerida"
        return task

    # ── 4. Validaciones de cantidad ───────────────────────────────────────────
    cantidad_transferir = task.cantidad or 0
    if cantidad_transferir <= 0:
        task.result = 0
        task.message = "La cantidad de traslado no es válida"
        return task

    if cantidad_transferir > inventory_data.cantidad:
        task.result = 0
        task.message = "La cantidad a trasladar supera el inventario disponible"
        return task

    # ── 5. Transacción ────────────────────────────────────────────────────────
    started_transaction = False
    try:
        if not db.in_transaction():
            await db.begin()
            started_transaction = True

        # Fix: update_transfer_task_state se llamaba DOS veces con el mismo
        # estado=3. Se elimina la primera llamada redundante y se deja solo
        # la llamada al final, tras todas las operaciones de inventario.

        motion_data = Motion(
            tipo_movimiento=3,
            id_item=inventory_data.id_item,
            lote=inventory_data.lote,
            cantidad=cantidad_transferir,
            posicion_origen_id=inventory_data.posicion_origen_id,
            posicion_destino_id=scanned_position["id"],
            fecha=datetime.now(),
            id_usuario=id_usuario,
        )
        motion_result = await create_motion_transfer(db, motion_data)
        if motion_result.result != 1:
            raise RuntimeError(motion_result.message)

        destination_inventory_result = await db.execute(
            text("""
                 SELECT id, cantidad
                 FROM inventario
                 WHERE id_posicion = :id_posicion
                   AND id_item = :id_item
                   AND lote = :lote
                   AND id <> :id_inventory
                 ORDER BY id DESC
                 LIMIT 1
                 FOR UPDATE
                 """),
            {
                "id_posicion": scanned_position["id"],
                "id_item": inventory_data.id_item,
                "lote": inventory_data.lote,
                "id_inventory": task.id_inventario,
            },
        )
        destination_inventory = destination_inventory_result.mappings().first()

        remaining_quantity = float(inventory_data.cantidad) - float(cantidad_transferir)
        inserted_row = None
        if destination_inventory:
            destination_quantity = float(destination_inventory["cantidad"])
            if remaining_quantity > 0:
                await db.execute(
                    text("""
                         UPDATE inventario
                         SET cantidad = :cantidad
                         WHERE id = :id_inventory
                         """),
                    {"cantidad": remaining_quantity, "id_inventory": task.id_inventario},
                )
                await db.execute(
                    text("""
                         UPDATE inventario
                         SET cantidad = :cantidad
                         WHERE id = :id_destination_inventory
                         """),
                    {
                        "cantidad": destination_quantity + float(cantidad_transferir),
                        "id_destination_inventory": destination_inventory["id"],
                    },
                )
                inserted_row = {"id": destination_inventory["id"]}
            else:
                await db.execute(
                    text("""
                         UPDATE inventario
                         SET cantidad = :cantidad
                         WHERE id = :id_destination_inventory
                         """),
                    {
                        "cantidad": destination_quantity + float(cantidad_transferir),
                        "id_destination_inventory": destination_inventory["id"],
                    },
                )
                await db.execute(
                    text("""
                         UPDATE inventario
                         SET cantidad = 0
                         WHERE id = :id_inventory
                         """),
                    {"id_inventory": task.id_inventario},
                )
                inserted_row = {"id": destination_inventory["id"]}
        elif remaining_quantity > 0:
            await db.execute(
                text("""
                     UPDATE inventario
                     SET cantidad = :cantidad
                     WHERE id = :id_inventory
                     """),
                {"cantidad": remaining_quantity, "id_inventory": task.id_inventario},
            )

            inserted_inventory = await db.execute(
                text("""
                     INSERT INTO inventario (
                        id_posicion,
                        id_item,
                        cantidad,
                        lote,
                        detalles,
                        fecha_vencimiento
                     )
                     VALUES (
                        :id_posicion,
                        :id_item,
                        :cantidad,
                        :lote,
                        :detalles,
                        :fecha_vencimiento
                     )
                     RETURNING id
                     """),
                {
                    "id_posicion": scanned_position["id"],
                    "id_item": inventory_data.id_item,
                    "cantidad": cantidad_transferir,
                    "lote": inventory_data.lote,
                    "detalles": inventory_data.message or "Traslado de piso a rack",
                    "fecha_vencimiento": inventory_data.fecha_vencimiento,
                },
            )
            inserted_row = inserted_inventory.mappings().first()
            if not inserted_row:
                raise RuntimeError("No se pudo registrar el inventario en la posición destino")
        else:
            await db.execute(
                text("""
                     UPDATE inventario
                     SET id_posicion = :id_posicion
                     WHERE id = :id_inventory
                     """),
                {"id_posicion": scanned_position["id"], "id_inventory": task.id_inventario},
            )
            inserted_row = {"id": task.id_inventario}

        position_update = await position_repository.update_position_state(db, scanned_position["id"], 2)
        if position_update.result != 1:
            raise RuntimeError(position_update.message or "No se pudo actualizar la posición destino")

        # Fix: update_transfer_task_state se llamaba dos veces — se deja solo aquí,
        # al final, una vez que todas las operaciones de inventario terminaron OK.
        finish_state = await update_transfer_task_state(db, id_task, 3)
        if finish_state.get("result") != 1:
            raise RuntimeError(finish_state.get("message", "No se pudo finalizar la tarea"))

        await db.commit()
    except Exception as e:
        print(f"Error al confirmar el traslado: {e}")
        if db.in_transaction():
            await db.rollback()
        task.result = 0
        task.message = f"Error al confirmar el traslado: {str(e)}"
        return task

    task.result = 1
    task.message = "Traslado confirmado exitosamente"
    task.id = motion_result.id
    task.id_inventario = inserted_row["id"]
    task.posicion_destino_id = scanned_position["id"]
    task.cod_posicion_destino = scanned_position["cod_posicion"]
    task.cod_posicion_sugerida = scanned_position["cod_posicion"]
    task.cantidad = cantidad_transferir
    task.message = f"Traslado confirmado exitosamente. Inventario destino id {inserted_row['id']}"
    return task