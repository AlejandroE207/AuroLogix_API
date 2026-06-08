from datetime import datetime

from app.model.position_model import Position
from app.repository import input_repository, inventory_repository, motion_repository, position_repository, item_repository
from app.model.inventory_model import Motion
from app.model.inventory_model import Inventory 
from app.model.putaway_model import Putaway
from app.service.position_service import get_random_position_storage, get_position_by_cod_position

async def create_input(db, putaway: Putaway):
    putaway_data = Putaway()
    type_item = await item_repository.get_item_type_by_id(db, putaway.id_item)
    position_random = await get_random_position_storage(db, type_item)
    putaway.posicion_sugerida_id = position_random.id
    putaway_data = await input_repository.create_input(db,putaway)
    if putaway_data.result == 1:
        putaway_data.message =  position_random.cod_posicion
    else:
        putaway_data.message = "Error al seleccionar la posición sugerida"
    return putaway_data
    
async def confirm_input(db, cod_posicion: str, id_input: int):
    putaway_data = Putaway()
    motion_data = Motion()
    inventory_data = Inventory()
    position_data = Position()
    
    putaway_data = await input_repository.get_putaway_by_id(db, id_input)
    suggested_position = await get_position_by_cod_position(db, cod_posicion)
    
    if putaway_data.result == 1 and suggested_position.result == 1:
        if suggested_position.id == putaway_data.posicion_sugerida_id:
            motion_data.tipo_movimiento = 1
            motion_data.id_item = putaway_data.id_item
            motion_data.lote = putaway_data.lote
            motion_data.cantidad = putaway_data.cantidad
            motion_data.posicion_destino_id = suggested_position.id
            motion_data.fecha = datetime.now()
            motion_data.id_usuario = putaway_data.id_usuario
            
            motion_result = await motion_repository.create_motion_input(db, motion_data)
            if motion_result.result == 1:
                inventory_data.id_item = putaway_data.id_item
                inventory_data.lote = putaway_data.lote
                inventory_data.cantidad = putaway_data.cantidad
                inventory_data.id_posicion = suggested_position.id
                inventory_data.fecha_vencimiento = putaway_data.fecha_vencimiento
                inventory_data.detalles = f"Movimiento de entrada con id {motion_result.id}"
                
                inventory_result = await inventory_repository.create_input_inventory(db, inventory_data)
                if inventory_result.result == 1:
                    position_data = await position_repository.update_position_state(db, inventory_data.id_posicion, 2) #Actualizar estado de la posición a ocupada  
                    putaway_data.result = 1
                    putaway_data.message = "Movimiento de entrada confirmado exitosamente"
                    await input_repository.delete_putaway(db, id_input) #NO ESTA ELIMINANDO EL PUTAWAY
                else:
                    putaway_data.result = 0
                    putaway_data.message = "Error al crear el inventario de entrada"
            else:
                putaway_data.result = 0
                putaway_data.message = "Error al crear el movimiento de entrada"
        else:
            putaway_data.result = 0
            putaway_data.message = "La posición seleccionada no coincide con la posición sugerida"
    else:
        putaway_data.result = 0
        putaway_data.message = "Error al obtener el putaway o la posición sugerida"
    return putaway_data

