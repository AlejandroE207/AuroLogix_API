from app.repository import motion_repository, inventory_repository
from app.model.inventory_model import Motion
from app.model.inventory_model import Inventory

async def create_input_inventory(db, motion: Motion, inventory: Inventory):
    motion_data = Motion()
    inventory_data = Inventory()
    id_posicion = await inventory_repository.random_position(db)
    if id_posicion is None:
        inventory_data.result = 0
        inventory_data.message = "No hay posiciones disponibles para asignar el inventario de entrada"
        return inventory_data
    else:
        inventory.id_posicion = id_posicion
        motion.posicion_destino_id = id_posicion
    
    motion_data = await motion_repository.create_motion_input(db, motion)
    if motion_data.result == 1:
        inventory_data = await inventory_repository.create_input_inventory(db, inventory)
        if inventory_data.result == 1:
            inventory_data.result = 1
            inventory_data.message = "Inventario de entrada creado exitosamente"
        else:
            inventory_data.result = 0
            inventory_data.message = "Error al crear el inventario de entrada"
    else:
        inventory_data.result = 0
        inventory_data.message = "Error al crear el movimiento de entrada"
    return inventory_data
    