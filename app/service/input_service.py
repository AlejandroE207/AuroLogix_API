from datetime import datetime

from app.model.position_model import Position
from app.repository import input_repository, inventory_repository, motion_repository, position_repository, item_repository
from app.model.inventory_model import Motion
from app.model.inventory_model import Inventory
from app.model.putaway_model import Putaway
from app.service.position_service import get_random_position_storage, get_position_by_cod_position


async def create_input(db, putaway: Putaway):
    """
    Registra una entrada al piso (posición fija 1329).
    Toda la operación corre en una sola transacción atómica:
      INSERT confirmacion_entrada → INSERT movimientos → INSERT inventario → commit
    Si cualquier paso falla → rollback completo.
    """
    putaway_data = Putaway()
    motion_data = Motion()
    inventory_data = Inventory()

    putaway.posicion_sugerida_id = 1329   # PISO
    putaway.posicion_confirmada_id = 1329  # PISO

    try:
        await db.begin()

        putaway_data = await input_repository.create_input(db, putaway)
        putaway_data.posicion_sugerida_id = putaway.posicion_sugerida_id
        putaway_data.posicion_confirmada_id = putaway.posicion_confirmada_id

        if putaway_data.result != 1:
            raise RuntimeError(putaway_data.message or "Error al crear el putaway")

        motion_data.tipo_movimiento = 1
        motion_data.id_item = putaway_data.id_item
        motion_data.lote = putaway_data.lote
        motion_data.cantidad = putaway_data.cantidad
        motion_data.posicion_destino_id = putaway_data.posicion_sugerida_id
        motion_data.fecha = datetime.now()
        motion_data.id_usuario = putaway_data.id_usuario

        motion_result = await motion_repository.create_motion_input(db, motion_data)
        if motion_result.result != 1:
            raise RuntimeError(motion_result.message or "Error al crear el movimiento de entrada")

        inventory_data.id_item = putaway_data.id_item
        inventory_data.lote = putaway_data.lote
        inventory_data.cantidad = putaway_data.cantidad
        inventory_data.id_posicion = putaway_data.posicion_sugerida_id
        inventory_data.fecha_vencimiento = putaway_data.fecha_vencimiento
        inventory_data.detalles = f"Movimiento de entrada con id {motion_result.id}"

        inventory_result = await inventory_repository.create_input_inventory(db, inventory_data)
        if inventory_result.result != 1:
            raise RuntimeError(inventory_result.message or "Error al crear el inventario de entrada")

        await position_repository.update_position_state(db, inventory_data.id_posicion, 2)

        # Fix: delete_putaway ya no hace su propio commit — se elimina dentro
        # de esta misma transacción y el commit de abajo lo confirma todo junto.
        await input_repository.delete_putaway(db, putaway_data.id)

        await db.commit()

        putaway_data.result = 1
        putaway_data.message = "Movimiento de entrada registrado exitosamente"

    except Exception as e:
        print(f"Error en create_input: {e}")
        if db.in_transaction():
            await db.rollback()
        putaway_data.result = 0
        putaway_data.message = str(e)

    return putaway_data


async def confirm_input(db, cod_posicion: str, id_input: int):
    """
    Confirma la entrada escaneando la posición de destino.
    Toda la operación corre en una sola transacción atómica:
      validaciones → INSERT movimientos → INSERT inventario → UPDATE posicion
      → DELETE confirmacion_entrada → commit
    Si cualquier paso falla → rollback completo.
    """
    putaway_data = Putaway()
    motion_data = Motion()
    inventory_data = Inventory()

    # ── Validaciones previas (fuera de transacción — solo lecturas) ───────────
    putaway_data = await input_repository.get_putaway_by_id(db, id_input)
    if putaway_data.result != 1:
        putaway_data.result = 0
        putaway_data.message = "Entrada no encontrada"
        return putaway_data

    # Fix: validar que la entrada no haya sido ya confirmada (estado = 2)
    if getattr(putaway_data, "estado", None) == 2:
        putaway_data.result = 0
        putaway_data.message = "Esta entrada ya fue confirmada anteriormente"
        return putaway_data

    suggested_position = await get_position_by_cod_position(db, cod_posicion)
    if suggested_position.result != 1:
        putaway_data.result = 0
        putaway_data.message = "La posición escaneada no existe"
        return putaway_data

    if suggested_position.id != putaway_data.posicion_sugerida_id:
        putaway_data.result = 0
        putaway_data.message = "La posición escaneada no coincide con la posición sugerida"
        return putaway_data

    # ── Transacción atómica ───────────────────────────────────────────────────
    try:
        await db.begin()

        motion_data.tipo_movimiento = 1
        motion_data.id_item = putaway_data.id_item
        motion_data.lote = putaway_data.lote
        motion_data.cantidad = putaway_data.cantidad
        motion_data.posicion_destino_id = suggested_position.id
        motion_data.fecha = datetime.now()
        motion_data.id_usuario = putaway_data.id_usuario

        motion_result = await motion_repository.create_motion_input(db, motion_data)
        if motion_result.result != 1:
            raise RuntimeError(motion_result.message or "Error al crear el movimiento de entrada")

        inventory_data.id_item = putaway_data.id_item
        inventory_data.lote = putaway_data.lote
        inventory_data.cantidad = putaway_data.cantidad
        inventory_data.id_posicion = suggested_position.id
        inventory_data.fecha_vencimiento = putaway_data.fecha_vencimiento
        inventory_data.detalles = f"Movimiento de entrada con id {motion_result.id}"

        inventory_result = await inventory_repository.create_input_inventory(db, inventory_data)
        if inventory_result.result != 1:
            raise RuntimeError(inventory_result.message or "Error al crear el inventario de entrada")

        await position_repository.update_position_state(db, inventory_data.id_posicion, 2)

        # Fix: delete_putaway usaba 'db.commit()' sin await — nunca se ejecutaba.
        # Ahora está dentro de la transacción y el commit de abajo lo confirma.
        await input_repository.delete_putaway(db, id_input)

        await db.commit()

        putaway_data.result = 1
        putaway_data.message = "Movimiento de entrada confirmado exitosamente"

    except Exception as e:
        print(f"Error en confirm_input: {e}")
        if db.in_transaction():
            await db.rollback()
        putaway_data.result = 0
        putaway_data.message = str(e)

    return putaway_data