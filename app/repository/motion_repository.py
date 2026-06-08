from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.inventory_model import Motion
from app.model.motion_view_model import MotionView

async def create_motion_input(db: AsyncSession, motion: Motion):
    motion_data = Motion()
    query = text("""
                 INSERT INTO movimientos (tipo_movimiento, id_item, lote, cantidad, posicion_origen_id,
                 posicion_destino_id, fecha, id_usuario
                 )
                  VALUES (:tipo_movimiento, :id_item, :lote, :cantidad, :posicion_origen_id,
                  :posicion_destino_id, :fecha, :id_usuario)
                  RETURNING id
                 """)
    try: 
        result = await db.execute(query, {"tipo_movimiento": motion.tipo_movimiento, "id_item": motion.id_item, "lote":motion.lote,
                                          "cantidad":motion.cantidad, "posicion_origen_id": motion.posicion_origen_id, "posicion_destino_id":motion.posicion_destino_id,
                                          "fecha":motion.fecha, "id_usuario":motion.id_usuario})
        row = result.mappings().first()
        await db.commit()
        if row:
            motion_data.id = row["id"]
            motion_data.result = 1
            motion_data.message = "Movimiento de entrada creado exitosamente"
        else:
            motion_data.result = 0
            motion_data.message = "Error al crear el movimiento de entrada"
        return motion_data
    except Exception as e:
        print(f"Error al crear el movimiento de entrada: {e}")
        motion_data.result = 0
        motion_data.message = "Error al crear el movimiento de entrada"
        return motion_data


async def create_motion_output(db: AsyncSession, motion: Motion):
    """Registra un movimiento de salida (picking/extracción)."""
    motion_data = Motion()
    query = text("""
                 INSERT INTO movimientos (tipo_movimiento, id_item, lote, cantidad, posicion_origen_id,
                 posicion_destino_id, fecha, id_usuario)
                 VALUES (:tipo_movimiento, :id_item, :lote, :cantidad, :posicion_origen_id,
                 :posicion_destino_id, :fecha, :id_usuario)
                 RETURNING id
                 """)
    try: 
        result = await db.execute(query, {"tipo_movimiento": motion.tipo_movimiento, "id_item": motion.id_item, 
                                          "lote": motion.lote, "cantidad": motion.cantidad, 
                                          "posicion_origen_id": motion.posicion_origen_id, 
                                          "posicion_destino_id": motion.posicion_destino_id,
                                          "fecha": motion.fecha, "id_usuario": motion.id_usuario})
        row = result.mappings().first()
        await db.commit()
        if row:
            motion_data.id = row["id"]
            motion_data.result = 1
            motion_data.message = "Movimiento de salida registrado exitosamente"
        else:
            motion_data.result = 0
            motion_data.message = "Error al registrar el movimiento de salida"
        return motion_data
    except Exception as e:
        print(f"Error al registrar el movimiento de salida: {e}")
        await db.rollback()
        motion_data.result = 0
        motion_data.message = "Error al registrar el movimiento de salida"
        return motion_data


from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def list_motion(
    db: AsyncSession, 
    item: str = None, 
    tipo_movimiento: str = None, 
    desde_fecha: datetime = None, 
    hasta_fecha: datetime = None, 
    limite: int = 50, 
    offset: int = 0
):
    # 1. Base de la consulta (SELECT y JOINS)
    query_str = """
        SELECT m.id, 
               tm.descripcion as tipo_movimiento, 
               i.descripcion as item, 
               m.cantidad,
               i.unidad_medida, 
               m.lote,  
               po.cod_posicion as posicion_origen, 
               pd.cod_posicion as posicion_destino,
               m.fecha,
               u.nombre as usuario
        FROM movimientos AS m
        INNER JOIN tipo_movimientos as tm ON m.tipo_movimiento = tm.id
        INNER JOIN items AS i ON m.id_item = i.id
        LEFT JOIN posiciones AS po ON m.posicion_origen_id = po.id 
        LEFT JOIN posiciones AS pd ON m.posicion_destino_id = pd.id
        INNER JOIN usuarios AS u ON m.id_usuario = u.id
    """
    
    # 2. Construcción dinámica de filtros
    filtros = []
    params = {"limite": limite, "offset": offset}

    if item:
        filtros.append("i.descripcion ILIKE :item")
        params["item"] = f"%{item}%"
    
    if tipo_movimiento:
        filtros.append("tm.descripcion ILIKE :tipo_movimiento")
        params["tipo_movimiento"] = tipo_movimiento

    if desde_fecha:
        filtros.append("m.fecha >= :desde_fecha")
        params["desde_fecha"] = desde_fecha

    if hasta_fecha:
        filtros.append("m.fecha <= :hasta_fecha")
        params["hasta_fecha"] = hasta_fecha

    # Unir filtros con WHERE
    if filtros:
        query_str += " WHERE " + " AND ".join(filtros)

    # Orden y paginación
    query_str += " ORDER BY m.fecha DESC LIMIT :limite OFFSET :offset"

    try:
        result = await db.execute(text(query_str), params)
        rows = result.mappings().all()

        if not rows:
            return {"result": 0, "message": "Movimientos no encontrados", "data": []}

        # Convertir filas a objetos Motion
        # Nota: Asumo que Motion es un Pydantic model o clase similar
        motion_data_list = []
        for row in rows:
            # Creamos el objeto con los datos de la fila
            motion_obj = MotionView(**dict(row))
            motion_data_list.append(motion_obj)

        return {
            "result": 1, 
            "message": "Movimientos encontrados", 
            "data": motion_data_list
        }

    except Exception as e:
        print(f"Error al obtener los movimientos: {e}")
        await db.rollback()
        return {
            "result": 0, 
            "message": f"Error técnico: {str(e)}", 
            "data": []
        }