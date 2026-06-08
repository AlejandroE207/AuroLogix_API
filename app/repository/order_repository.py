from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.picking_model import Orden

async def create_order (db:AsyncSession, orden: Orden):
    order_data = Orden()
    query = text("""
                 INSERT INTO orden_salida (codigo, cliente, estado, id_usuario)
                 VALUES (:codigo, :cliente, :estado, :id_usuario)
                RETURNING id, codigo, cliente, estado, id_usuario
                 """)
    
    try:
        result = await db.execute(query, {"codigo": orden.codigo, "cliente": orden.cliente, 
                                          "estado": orden.estado, "id_usuario": orden.id_usuario})
        row = result.mappings().first()
        await db.commit()
        if row:
            order_data = Orden(**dict(row))
            order_data.result = 1
            order_data.message = "Orden creada exitosamente"
        else:
            order_data.result = 0
            order_data.message = "Error al crear la orden"
        return order_data
    except Exception as e:
        print(f"Error al crear la orden: {e}")
        order_data.result = 0
        order_data.message = "Error al crear la orden"
        return order_data
    