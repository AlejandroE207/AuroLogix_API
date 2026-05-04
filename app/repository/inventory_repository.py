from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.inventory_model import Inventory

async def create_input_inventory(db: AsyncSession, inventory: Inventory):
    inventory_data = Inventory()
    
    query = text("""
                 INSERT INTO inventarios (id, id_posicion, id_item, cantidad, lote, estado, detalles)
                 VALUES (:id, :id_posicion, :id_item, :cantidad, :lote, :estado, :detalles)
                 RETURNING id
                 """)
    try:
        result = await db.execute(query, {"id": inventory.id, "id_posicion": inventory.id_posicion, "id_item":inventory.id_item,
                                          "cantidad":inventory.cantidad, "lote": inventory.lote, "estado":inventory.estado, "detalles": inventory.detalles})
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
    
async def random_position(db:AsyncSession):
    query = text("""
                 SELECT id FROM posiciones
                 WHERE estado = 1
                 AND (SUBSTRING(cod_posicion FROM 'N([0-9]+)')::INTEGER) > 2
                 ORDER BY RANDOM()
                 LIMIT 1
                 """)
    try:
        result = await db.execute(query)
        row = result.mappings().first()
        if row:
            return row["id"]
        else:
            return None
    except Exception as e:
        print(f"Error al obtener posición aleatoria: {e}")
        return None