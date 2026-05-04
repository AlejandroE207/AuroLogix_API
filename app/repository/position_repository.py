from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.position_model import Position

async def get_position_by_id(db: AsyncSession, id_position: int):
    position_data = Position()
    query = text("""
                 SELECT id, cod_posicion, bodega, estado
                 FROM posiciones
                 WHERE id = :id_position
                 ORDER BY id ASC
                 """)
    try:
        result = await db.execute(query, {"id_position": id_position})
        row = result.mappings().first()
        if row:
            position_data = Position(**dict(row))
            position_data.result = 1
            position_data.message = "Posición encontrada"
        else:
            position_data.result = 0
            position_data.message = "Posición no encontrada"
        return position_data
    except Exception as e:
        print(f"Error al obtener la posición por ID: {e}")
        position_data.result = 0
        position_data.message = "Error al obtener la posición"
        return position_data
    
async def get_position_by_cod_position(db: AsyncSession, cod_posicion: str):
    position_data = Position()
    query = text("""
                 SELECT id, cod_posicion, bodega, estado
                 FROM posiciones
                 WHERE cod_posicion = :cod_posicion
                 ORDER BY id ASC
                 """)
    try:
        result = await db.execute(query, {"cod_posicion": cod_posicion})
        row = result.mappings().first()
        if row:
            position_data = Position(**dict(row))
            position_data.result = 1
            position_data.message = "Posición encontrada"
        else:
            position_data.result = 0
            position_data.message = "Posición no encontrada"
        return position_data
    except Exception as e:
        print(f"Error al obtener la posición por código: {e}")
        position_data.result = 0
        position_data.message = "Error al obtener la posición"
        return position_data
    
async def get_positions_by_store(db: AsyncSession, store:int):
    position_data_list = []
    query = text("""
                SELECT id, cod_posicion, bodega, estado
                FROM posiciones
                WHERE bodega = :store
                ORDER BY id ASC
                 """)
    try:
        result = await db.execute(query, {"store":store})
        row = result.mappings().all()
        for position in row:
            position_data = Position()
            position_data = Position(**dict(position))
            position_data.result=1
            position_data.message = "Posición encontrada"
            position_data_list.append(position_data)
        if not position_data_list:
            position_data = Position()
            position_data.result = 0
            position_data.message = "Posición no encontrada"
            position_data_list.append(position_data)
        return position_data_list
    except Exception as e:
        print(f"Error al obtener las posiciones por bodega: {e}")
        position_data = Position()
        position_data.result = 0
        position_data.message = "Error al obtener las posiciones"
        position_data_list.append(position_data)
        return position_data_list
    
async def get_positions_by_state(db: AsyncSession, state:int):
    position_data_list = []
    query = text("""
                 SELECT id, cod_posicion, bodega, estado
                 FROM posiciones
                 WHERE estado = :state
                 ORDER BY id ASC
                 """)
    try:
        result = await db.execute(query, {"state":state})
        row = result.mappings().all()
        for position in row:
            position_data = Position()
            position_data = Position(**dict(position))
            position_data.result=1
            position_data.message = "Posición encontrada"
            position_data_list.append(position_data)
        if not position_data_list:
            position_data = Position()
            position_data.result = 0
            position_data.message = "Posición no encontrada"
            position_data_list.append(position_data)
        return position_data_list
    except Exception as e:
        print(f"Error al obtener las posiciones por estado: {e}")
        position_data = Position()
        position_data.result = 0
        position_data.message = "Error al obtener las posiciones"
        position_data_list.append(position_data)
        return position_data_list
    
async def update_position_state(db: AsyncSession, id_position:int, new_state: int):
    position_data = Position()
    query = text("""
                 UPDATE posiciones
                 SET estado = :new_state
                 WHERE id = :id_position
                 RETURNING id
                 """)
    try:
        result = await db.execute(query, {"new_state": new_state, "id_position": id_position})
        await db.commit()
        row = result.mappings().first()
        if row:
            position_data.id = row["id"]
            position_data.result = 1
            position_data.message = "Estado de la posición actualizado correctamente"
        else:
            position_data.result = 0
            position_data.message = "Posición no encontrada para actualizar"
        return position_data
    except Exception as e:
        print(f"Error al actualizar el estado de la posición: {e}")
        position_data.result = 0
        position_data.message = "Error al actualizar el estado de la posición"
        return position_data
            
    
