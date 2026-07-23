from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.item_model import Item, ItemInventory

async def search_items(db: AsyncSession, que: str):
    items = []
    query = text("""
                 SELECT id, cod_item, descripcion, unidad_medida, tipo_item
                 FROM items
                 WHERE descripcion ILIKE :query 
                 ORDER BY id ASC
                 """)
    try:
        result = await db.execute(query, {"query": f"%{que}%"})
        rows = result.mappings().all()
        for row in rows:
            item_data = Item(**dict(row))
            item_data.result = 1
            item_data.message = "Item encontrado"
            items.append(item_data)
        if not items:
            item_data = Item()
            item_data.result = 0
            item_data.message = "No se encontraron items que coincidan con la búsqueda"
            items.append(item_data)
        return items
    except Exception as e:
        print(f"Error al buscar items: {e}")
        item_data = Item()
        item_data.result = 0
        item_data.message = "Error al buscar items"
        items.append(item_data)
        return items
    
async def search_item_by_cod_item(db: AsyncSession, cod_item: str):
    item_data = Item()
    query = text("""
                 SELECT id, cod_item, descripcion, unidad_medida, tipo_item
                 FROM items
                 WHERE cod_item = :cod_item
                 """)
    try:
        result = await db.execute(query, {"cod_item": cod_item})
        row = result.mappings().first()
        if row:
            item_data = Item(**dict(row))
            item_data.result = 1
            item_data.message = "Item encontrado"
            return item_data
        else:
            item_data.result = 0
            item_data.message = "No se encontró un item con el código proporcionado"
            return item_data
    except Exception as e:
        print(f"Error al buscar el item por código: {e}")
        item_data.result = 0
        item_data.message = "Error al buscar el item por código"
        return item_data    
    
async def search_item_inventory(db: AsyncSession, que:str):
    items=[]
    query= text("""
                    SELECT inv.id_item AS id, it.cod_item, it.descripcion, inv.cantidad, it.unidad_medida, inv.lote ,it.tipo_item
                    FROM inventario AS inv
                    INNER JOIN items AS it ON inv.id_item = it.id
                    WHERE it.descripcion ILIKE :query
                    ORDER BY inv.id_item ASC
                """)
    try:
        result = await db.execute(query, {"query": f"%{que}%"})
        rows = result.mappings().all()
        for row in rows:
            item_data = ItemInventory(**dict(row))
            item_data.result = 1
            item_data.message = "Item encontrado"
            items.append(item_data)
        if not items:
            item_data = ItemInventory()
            item_data.result = 0
            item_data.message = "No se encontraron items que coincidan con la búsqueda"
            items.append(item_data)
        return items
    except Exception as e:
        print(f"Error al buscar items con inventario: {e}")
        item_data = ItemInventory()
        item_data.result = 0
        item_data.message = "Error al buscar items con inventario"
        items.append(item_data)
        return items
    
async def get_all_items_map(db: AsyncSession) -> dict[str, int]:
    """Devuelve un diccionario {cod_item: id} con todos los items registrados.

    Se usa para resolver referencias en bloque durante importaciones masivas
    (por ejemplo, la carga de inventario desde Excel) sin hacer una consulta
    por cada fila del archivo.
    """
    query = text("""
                 SELECT id, cod_item
                 FROM items
                 """)
    try:
        result = await db.execute(query)
        rows = result.mappings().all()
        return {row["cod_item"]: row["id"] for row in rows if row["cod_item"] is not None}
    except Exception as e:
        print(f"Error al obtener el mapa de items: {e}")
        return {}


async def get_item_type_by_id(db: AsyncSession, id_item: int):
    query = text("""
                 SELECT tipo_item
                 FROM items
                 WHERE id = :id_item
                 """)
    try:
        result = await db.execute(query, {"id_item": id_item})
        row = result.mappings().first()
        if row:
            return row["tipo_item"]
        else:
            return None
    except Exception as e:
        print(f"Error al obtener el tipo de item por id: {e}")
        return None