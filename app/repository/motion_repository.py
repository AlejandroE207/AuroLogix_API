from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.inventory_model import Motion

async def create_motion_input(db: AsyncSession, motion: Motion):
    motion_data = Motion()
    query = text("""
                 INSERT INTO movimientos (id, tipo_movimiento, id_item, lote, cantidad, posicion_origen_id,
                 posicion_destino_id, fecha, id_usuario
                 )
                  VALUES (:id, :tipo_movimiento, :id_item, :lote, :cantidad, :posicion_origen_id,
                  :posicion_destino_id, :fecha, :id_usuario)
                  RETURNING id
                 """)
    try: 
        result = await db.execute(query, {"id": motion.id, "tipo_movimiento": motion.tipo_movimiento, "id_item": motion.id_item, "lote":motion.lote,
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
