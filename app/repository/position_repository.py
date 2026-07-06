from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.position_model import Position
from app.model.position_view_model import PositionView

async def get_position_by_id(db: AsyncSession, id_position: int):
    position_data = Position()
    query = text("""
                 SELECT id, cod_posicion, bodega, estado, reserva
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
                 SELECT id, cod_posicion, bodega, estado, reserva
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
                SELECT id, cod_posicion, bodega, estado, reserva
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
                 SELECT id, cod_posicion, bodega, estado, reserva
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

async def get_position_random_storage(db: AsyncSession, type_item: str):
    position_data = Position()
    match type_item:
        case "MP":
            reserva = "abastecimiento"
        case "PT":
            reserva = "abastecimiento"
        case "ME":
            reserva = "complementario"
        case "MEE":
            reserva = "complementario"
        case _:
            return "Tipo de item no reconocido"
    
    query = text("""
                 SELECT id, cod_posicion, bodega, estado, reserva
                 FROM posiciones
                 WHERE estado = 1
                 AND reserva = :reserva
                 ORDER BY RANDOM()
                 LIMIT 1
                 """)
    try:
        result = await db.execute(query, {"reserva": reserva})
        row = result.mappings().first()
        if row:
            position_data = Position(**dict(row))
            position_data.result = 1
            position_data.message = "Posición de almacenamiento aleatoria generada"
        else:
            position_data.result = 0
            position_data.message = "No se encontró una posición de almacenamiento disponible"
        return position_data
    except Exception as e:
        print(f"Error al obtener una posición de almacenamiento aleatoria: {e}")
        position_data.result = 0
        position_data.message = "Error al obtener una posición de almacenamiento aleatoria"
        return position_data
    

async def count_positions(db: AsyncSession):
    query = text("""
                 SELECT COUNT(*) AS total
                 FROM posiciones
                 """)
    try:
        result = await db.execute(query)
        row = result.mappings().first()
        if row:
            total_positions = row["total"]
            return total_positions
        else:
            return 0
    except Exception as e:
        print(f"Error al contar las posiciones: {e}")
        return 0
    
async def count_occupied_positions(db: AsyncSession):
    query = text("""
                 SELECT COUNT(*) AS total
                 FROM posiciones
                 WHERE estado = 2
                 """)
    try:
        result = await db.execute(query)
        row = result.mappings().first()
        if row:
            occupied_positions = row["total"]
            return occupied_positions
        else:
            return 0
    except Exception as e:
        print(f"Error al contar las posiciones ocupadas: {e}")
        return 0
    
async def count_available_positions(db: AsyncSession):
    query = text("""
                 SELECT COUNT(*) AS total
                 FROM posiciones
                 WHERE estado = 1
                 """)
    try:
        result = await db.execute(query)
        row = result.mappings().first()
        if row:
            available_positions = row["total"]
            return available_positions
        else:
            return 0
    except Exception as e:
        print(f"Error al contar las posiciones disponibles: {e}")
        return 0
    
async def get_all_positions_table(db: AsyncSession, item: str = None, posicion_estado: str = None, lote: str = None, estado_alerta: str = None, limite: int = 50, offset: int = 0):
    position_data_list = []
    query = """
                    SELECT 
                        p.id AS posicion_id,
                        p.cod_posicion,
                        p.bodega,
                        ep.descripcion AS posicion_estado,
                        p.reserva,
                        i.id_item,
                        it.descripcion AS producto,
                        i.cantidad,
                        it.unidad_medida,
                        i.lote,
                        i.fecha_vencimiento,
                        (i.fecha_vencimiento::date - CURRENT_DATE) AS dias_restantes,
                        CASE
                            WHEN i.fecha_vencimiento::date < CURRENT_DATE THEN 'vencido'
                            WHEN i.fecha_vencimiento::date >= CURRENT_DATE AND i.fecha_vencimiento::date <= CURRENT_DATE + INTERVAL '90 days' THEN 'critico'
                            WHEN i.fecha_vencimiento::date > CURRENT_DATE + INTERVAL '90 days' AND i.fecha_vencimiento::date <= CURRENT_DATE + INTERVAL '150 days' THEN 'leve'
                        END AS estado_alerta
                    FROM posiciones p
                    LEFT JOIN inventario i ON p.id = i.id_posicion
                    LEFT JOIN items it ON i.id_item = it.id
                    LEFT JOIN estado_posicion ep ON p.estado = ep.id
                 """
    
    filtros = []
    params = {"limite": limite, "offset": offset}
    if item:
        filtros.append("it.descripcion ILIKE :item")
        params["item"] = f"%{item}%"
        
    if posicion_estado:
        filtros.append("ep.descripcion = :posicion_estado")
        params["posicion_estado"] = posicion_estado

    if lote:
        filtros.append("i.lote ILIKE :lote")
        params["lote"] = f"%{lote}%"
        
    if estado_alerta:
        filtros.append("CASE WHEN i.fecha_vencimiento::date < CURRENT_DATE THEN 'vencido' WHEN i.fecha_vencimiento::date >= CURRENT_DATE AND i.fecha_vencimiento::date <= CURRENT_DATE + INTERVAL '30 days' THEN 'critico' WHEN i.fecha_vencimiento::date > CURRENT_DATE + INTERVAL '30 days' AND i.fecha_vencimiento::date <= CURRENT_DATE + INTERVAL '60 days' THEN 'leve' END = :estado_alerta")
        params["estado_alerta"] = estado_alerta
            
    if filtros:
        query += " WHERE " + " AND ".join(filtros)
    
    query += " ORDER BY posicion_id ASC LIMIT :limite OFFSET :offset"
    
    try:
        result = await db.execute(text(query), params)
        rows = result.mappings().all()
        for row in rows:
            position_view = PositionView(**dict(row))
            position_view.result = 1
            position_view.message = "Posición obtenida exitosamente"
            position_data_list.append(position_view)
        if not position_data_list:
            position_view = PositionView()
            position_view.result = 0
            position_view.message = "No se encontraron posiciones"
            position_data_list.append(position_view)
        return position_data_list
    except Exception as e:
        print(f"Error al obtener todas las posiciones: {e}")
        position_view = PositionView()
        position_view.result = 0
        position_view.message = "Error al obtener las posiciones"
        position_data_list.append(position_view)
        return position_data_list

async def get_all_positions(db: AsyncSession):
    position_data_list = []
    query = """
                    SELECT 
                        p.id AS posicion_id,
                        p.cod_posicion,
                        p.bodega,
                        ep.descripcion AS posicion_estado,
                        p.reserva,
                        i.id_item,
                        it.cod_item,
                        it.descripcion AS producto,
                        i.cantidad,
                        it.unidad_medida,
                        i.lote,
                        i.fecha_vencimiento,
                        (i.fecha_vencimiento::date - CURRENT_DATE) AS dias_restantes,
                        CASE
                            WHEN i.fecha_vencimiento::date < CURRENT_DATE THEN 'vencido'
                            WHEN i.fecha_vencimiento::date >= CURRENT_DATE AND i.fecha_vencimiento::date <= CURRENT_DATE + INTERVAL '92 days' THEN 'critico'
                            WHEN i.fecha_vencimiento::date > CURRENT_DATE + INTERVAL '90 days' AND i.fecha_vencimiento::date <= CURRENT_DATE + INTERVAL '150 days' THEN 'leve'
                        END AS estado_alerta
                    FROM posiciones p
                    LEFT JOIN inventario i ON p.id = i.id_posicion
                    LEFT JOIN items it ON i.id_item = it.id
                    LEFT JOIN estado_posicion ep ON p.estado = ep.id
                    ORDER BY posicion_id ASC;
                 """
    
    
    try:
        result = await db.execute(text(query))
        rows = result.mappings().all()
        for row in rows:
            position_view = PositionView(**dict(row))
            position_view.result = 1
            position_view.message = "Posición obtenida exitosamente"
            position_data_list.append(position_view)
        if not position_data_list:
            position_view = PositionView()
            position_view.result = 0
            position_view.message = "No se encontraron posiciones"
            position_data_list.append(position_view)
        return position_data_list
    except Exception as e:
        print(f"Error al obtener todas las posiciones: {e}")
        position_view = PositionView()
        position_view.result = 0
        position_view.message = "Error al obtener las posiciones"
        position_data_list.append(position_view)
        return position_data_list
    
async def get_positions_by_item(db: AsyncSession, item: str = None, lote: str = None):
    position_data_list = []
    query = """
            SELECT iv.id_posicion as posicion_id, p.cod_posicion, p.bodega
            FROM inventario as iv
            LEFT JOIN posiciones as p ON p.id = iv.id_posicion
            LEFT JOIN items as it ON it.id = iv.id_item
            """
    filtros = []
    params = {}
    
    if item: 
        filtros.append("it.descripcion ILIKE :item")
        params["item"] = f"%{item}%"
    if lote:
        filtros.append("iv.lote ILIKE :lote")
        params["lote"] = f"%{lote}%"
    
    if filtros:
        query += " WHERE " + " AND ".join(filtros)
        
    query += " ;"
    
    try:
        result = await db.execute(text(query), params)
        rows = result.mappings().all()
        
        for row in rows:
            position_view = PositionView(**dict(row))
            position_view.result = 1
            position_view.message = "Posición obtenida exitosamente"
            position_data_list.append(position_view)
        if not position_data_list:
            position_view = PositionView()
            position_view.result = 0
            position_view.message = "No se encontraron posiciones para el item especificado"
            position_data_list.append(position_view)
        return position_data_list
    except Exception as e:
        print(f"Error al obtener las posiciones por item: {e}")
        position_view = PositionView()
        position_view.result = 0
        position_view.message = "Error al obtener las posiciones por item"
        position_data_list.append(position_view)
        return position_data_list
        
        
async def create_rack(db: AsyncSession, posiciones: list[Position]):
    position_data_list = []
    query = text("""
                 INSERT INTO posiciones (cod_posicion, bodega, estado, reserva)
                 VALUES (:cod_posicion, :bodega, :estado, :reserva)
                 RETURNING id
                 """)
    try:
        for posicion in posiciones:
            result = await db.execute(query, {"cod_posicion": posicion.cod_posicion, "bodega": posicion.bodega, "estado": posicion.estado, "reserva": posicion.reserva})
            await db.commit()
            row = result.mappings().first()
            if row:
                posicion.id = row["id"]
                posicion.result = 1
                posicion.message = "Posición creada exitosamente"
            else:
                posicion.result = 0
                posicion.message = "Error al crear la posición"
            position_data_list.append(posicion)
        return position_data_list
    except Exception as e:
        print(f"Error al crear las posiciones: {e}")
        await db.rollback()
        for posicion in posiciones:
            posicion.result = 0
            posicion.message = "Error al crear la posición"
            position_data_list.append(posicion)
        return position_data_list