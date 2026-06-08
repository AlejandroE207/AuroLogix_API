from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.putaway_model import Putaway

async def create_input(db: AsyncSession, putaway: Putaway):
    putaway_data = Putaway()
    putaway.fecha = datetime.now()
    query = text("""
                 INSERT INTO confirmacion_entrada(id_item, lote, cantidad, posicion_sugerida_id, 
                 id_usuario, fecha, estado, fecha_vencimiento)
                 VALUES (:id_item, :lote, :cantidad, :posicion_sugerida_id,
                 :id_usuario, :fecha, :estado, :fecha_vencimiento)
                RETURNING id, posicion_sugerida_id
                 """)
    try:
        result = await db.execute(query, {"id_item": putaway.id_item, "lote": putaway.lote, "cantidad": putaway.cantidad,
                                          "posicion_sugerida_id": putaway.posicion_sugerida_id, "id_usuario": putaway.id_usuario,
                                          "fecha": putaway.fecha, "estado": 1, "fecha_vencimiento": putaway.fecha_vencimiento})
        row = result.mappings().first()
        await db.commit()
        if row:
            putaway_data.id = row["id"]
            putaway_data.result = 1
            putaway_data.message = "Putaway creado exitosamente"
        else:
            putaway_data.result = 0
            putaway_data.message = "Error al crear el putaway"
        return putaway_data
    except Exception as e:
        print(f"Error al crear el putaway: {e}")
        putaway_data.result = 0
        putaway_data.message = "Error al crear el putaway"
        return putaway_data
    
async def get_putaway_by_id(db: AsyncSession, id: int):
    putaway_data = Putaway()
    query = text("""
                 SELECT id, id_item, lote, cantidad, fecha_vencimiento, posicion_sugerida_id, id_usuario, fecha, estado
                 FROM confirmacion_entrada
                 WHERE id = :id
                 """)
    try:
        result = await db.execute(query, {"id": id})
        row = result.mappings().first()
        if row:
            putaway_data = Putaway(**dict(row))
            putaway_data.result = 1
            putaway_data.message = "Putaway encontrado"
        else:
            putaway_data.result = 0
            putaway_data.message = "Putaway no encontrado"
        return putaway_data
    except Exception as e:
        print(f"Error al obtener el putaway por ID: {e}")
        putaway_data.result = 0
        putaway_data.message = "Error al obtener el putaway"
        return putaway_data
    
async def delete_putaway(db:AsyncSession, id: int):
    Putaway_data = Putaway()
    query = text("""
                DELETE FROM confirmacion_entrada
                WHERE id = :id
                 """)
    try:
        await db.execute(query, {"id": id})
        db.commit()
        Putaway_data.result = 1
        Putaway_data.message = "Putaway eliminado exitosamente"
        return Putaway_data
    except Exception as e:
        print(f"Error al eliminar el putaway: {e}")
        Putaway_data.result = 0
        Putaway_data.message = "Error al eliminar el putaway"
        return Putaway_data
    