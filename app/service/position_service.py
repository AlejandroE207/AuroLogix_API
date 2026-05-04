from app.repository import position_repository
from app.model.position_model import Position

async def get_position_by_id(db, id_position: int):
    position_data = Position()
    position_data = await position_repository.get_position_by_id(db, id_position)
    return position_data

async def get_position_by_cod_position(db, cod_posicion: str):
    position_data = Position()
    position_data = await position_repository.get_position_by_cod_position(db, cod_posicion)
    return position_data

async def get_positions_by_store(db, store: int):
    position_data_list = []
    position_data_list = await position_repository.get_positions_by_store(db, store)
    return position_data_list

async def get_positions_by_state(db, state: int):
    position_data_list = []
    position_data_list = await position_repository.get_positions_by_state(db, state)
    return position_data_list

async def update_position_state(db, id_position: int, new_state: int):
    position_data = Position()
    position_data = await position_repository.update_position_state(db, id_position, new_state)
    return position_data