from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.dashboard_model import Summary
from app.model.inventory_model import Inventory
from app.model.picking_model import Picking_items

async def create_input_inventory(db: AsyncSession, inventory: Inventory):
    inventory_data = Inventory()
    
    query = text("""
                 INSERT INTO inventario ( id_posicion, id_item, cantidad, lote, detalles, fecha_vencimiento)
                 VALUES (:id_posicion, :id_item, :cantidad, :lote, :detalles, :fecha_vencimiento)
                 RETURNING id
                 """)
    try:
        result = await db.execute(query, {"id_posicion": inventory.id_posicion, "id_item":inventory.id_item,
                                          "cantidad":inventory.cantidad, "lote": inventory.lote, "detalles": inventory.detalles, "fecha_vencimiento": inventory.fecha_vencimiento})
        row = result.mappings().first()
        await db.commit()
        if row:
            inventory_data.id = row["id"]
            inventory_data.result = 1
            inventory_data.message = "Inventario de entrada creado exitosamente"
        else:
            inventory_data.result = 0
            inventory_data.message = "Error al crear el inventario de entrada"
        return inventory_data
    except Exception as e:
        print(f"Error al crear el inventario de entrada: {e}")
        inventory_data.result = 0
        inventory_data.message = "Error al crear el inventario de entrada"
        return inventory_data
    



async def get_position_by_item(db: AsyncSession, id_item:int, lote:str):
    picking_item = Picking_items()
    query = text("""
                 SELECT id_item, id_posicion, lote
                 FROM inventario
                 WHERE id_item = :id_item AND lote = :lote
                 """)
    try:
        result = await db.execute(query, {"id_item": id_item, "lote":lote})
        row = result.mappings().first()
        if row:
            picking_item = Picking_items(**dict(row))
            picking_item.id_posicion_origen = row["id_posicion"]
            picking_item.result = 1
            picking_item.message = "Inventario encontrado"
        else:
            picking_item.result = 0
            picking_item.message = "Inventario no encontrado"
        return picking_item
    except Exception as e:
        print(f"Error al obtener el inventario por item: {e}")
        picking_item.result = 0
        picking_item.message = "Error al obtener el inventario"
        return picking_item


async def update_inventory_quantity(db: AsyncSession, id_posicion: int, id_item: int, lote: str, cantidad_salida: float):
    """Actualiza la cantidad de inventario después de una salida (picking)."""
    query = text("""
                 UPDATE inventario
                 SET cantidad = cantidad - :cantidad_salida
                 WHERE id_posicion = :id_posicion AND id_item = :id_item AND lote = :lote
                 """)
    try:
        await db.execute(query, {"id_posicion": id_posicion, "id_item": id_item, 
                                 "lote": lote, "cantidad_salida": cantidad_salida})
        await db.commit()
        return {"result": 1, "message": "Inventario actualizado exitosamente"}
    except Exception as e:
        print(f"Error al actualizar el inventario: {e}")
        await db.rollback()
        return {"result": 0, "message": "Error al actualizar el inventario"}
    
    
async def count_expiration_alerts(db: AsyncSession):
    summary_aux = Summary()
    query = text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE i.fecha_vencimiento::date < CURRENT_DATE) AS vencidos,
                        COUNT(*) FILTER (WHERE i.fecha_vencimiento::date >= CURRENT_DATE AND i.fecha_vencimiento::date <= CURRENT_DATE + INTERVAL '90 days') AS criticos,
                        COUNT(*) FILTER (WHERE i.fecha_vencimiento::date > CURRENT_DATE + INTERVAL '90 days' AND i.fecha_vencimiento::date <= CURRENT_DATE + INTERVAL '150 days') AS leve
                    FROM inventario AS i;
                 """)
    try:
        result = await db.execute(query)
        row = result.mappings().first()
        if row:
            summary_aux.alertas_vencido = row["vencidos"]
            summary_aux.alertas_vencimiento_leve = row["leve"]
            summary_aux.alertas_vencimiento_critico = row["criticos"]
            summary_aux.result = 1
            summary_aux.message = "Alertas de vencimiento obtenidas exitosamente"
        else:
            summary_aux.result = 0
            summary_aux.message = "Error al obtener las alertas de vencimiento"
        return summary_aux
    except Exception as e:
        print(f"Error al contar las alertas de vencimiento: {e}")
        summary_aux.result = 0
        summary_aux.message = "Error al obtener las alertas de vencimiento"
        return summary_aux
    
