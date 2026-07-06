from app.repository import inventory_repository, transfer_repository


async def get_list_piso(db):
    return await inventory_repository.get_list_piso(db)


async def get_list_stored_inventory(db):
    return await inventory_repository.get_list_stored_inventory(db)


async def get_manual_positions(db, id_inventory: int):
    return await transfer_repository.get_manual_positions_for_inventory(db, id_inventory)


async def floor_to_rack_auto(db, id_inventory: int, cantidad: float, id_usuario: int):
    inventory_data = await transfer_repository.get_inventory_by_id(db, id_inventory)
    if inventory_data.result != 1:
        return inventory_data

    if cantidad <= 0:
        inventory_data.result = 0
        inventory_data.message = "La cantidad debe ser mayor que cero"
        return inventory_data

    if cantidad > inventory_data.cantidad:
        inventory_data.result = 0
        inventory_data.message = "La cantidad solicitada supera la cantidad disponible"
        return inventory_data

    suggestion = await transfer_repository.get_auto_suggestion_for_inventory(db, id_inventory)
    if suggestion.get("result") != 1:
        inventory_data.result = 0
        inventory_data.message = suggestion.get("message", "No se pudo generar la sugerencia")
        return inventory_data

    if not db.in_transaction():
        await db.begin()

    try:
        transfer_task = await transfer_repository.create_transfer_task(
            db=db,
            id_inventario=id_inventory,
            posicion_destino_id=suggestion["posicion_destino_id"],
            posicion_sugerida_id=suggestion["posicion_sugerida_id"],
            cantidad=cantidad,
            id_usuario=id_usuario,
        )
        if transfer_task.result != 1:
            raise RuntimeError(transfer_task.message)

        await db.commit()
    except Exception as e:
        if db.in_transaction():
            await db.rollback()
        inventory_data.result = 0
        inventory_data.message = str(e)
        return inventory_data

    if transfer_task.result == 1:
        transfer_task.cod_posicion_sugerida = suggestion["cod_posicion_sugerida"]
        transfer_task.cod_posicion_destino = suggestion["cod_posicion_destino"]
        transfer_task.id_inventario = id_inventory
        transfer_task.cantidad = cantidad
    return transfer_task


async def floor_to_rack_manual(db, id_inventory: int, cantidad: float, posicion_destino_id: int, id_usuario: int):
    inventory_data = await transfer_repository.get_inventory_by_id(db, id_inventory)
    if inventory_data.result != 1:
        return inventory_data

    if cantidad <= 0:
        inventory_data.result = 0
        inventory_data.message = "La cantidad debe ser mayor que cero"
        return inventory_data

    if cantidad > inventory_data.cantidad:
        inventory_data.result = 0
        inventory_data.message = "La cantidad solicitada supera la cantidad disponible"
        return inventory_data

    positions_data = await transfer_repository.get_manual_positions_for_inventory(db, id_inventory)
    if positions_data.get("result") != 1:
        inventory_data.result = 0
        inventory_data.message = positions_data.get("message", "No se pudieron obtener las posiciones")
        return inventory_data

    allowed_positions = positions_data.get("data", [])
    selected_position = next((position for position in allowed_positions if position["id"] == posicion_destino_id), None)
    if not selected_position:
        inventory_data.result = 0
        inventory_data.message = "La posición seleccionada no cumple las reglas del traslado manual"
        return inventory_data

    if not db.in_transaction():
        await db.begin()

    try:
        transfer_task = await transfer_repository.create_transfer_task(
            db=db,
            id_inventario=id_inventory,
            posicion_destino_id=posicion_destino_id,
            posicion_sugerida_id=posicion_destino_id,
            cantidad=cantidad,
            id_usuario=id_usuario,
        )
        if transfer_task.result != 1:
            raise RuntimeError(transfer_task.message)

        await db.commit()
    except Exception as e:
        if db.in_transaction():
            await db.rollback()
        inventory_data.result = 0
        inventory_data.message = str(e)
        return inventory_data

    if transfer_task.result == 1:
        transfer_task.cod_posicion_sugerida = selected_position["cod_posicion"]
        transfer_task.cod_posicion_destino = selected_position["cod_posicion"]
        transfer_task.id_inventario = id_inventory
        transfer_task.cantidad = cantidad
    return transfer_task


async def confirm_transfer_task(db, id_task: int, cod_posicion_escaneada: str, id_usuario: int):
    return await transfer_repository.confirm_transfer_core(db, id_task, cod_posicion_escaneada, id_usuario)