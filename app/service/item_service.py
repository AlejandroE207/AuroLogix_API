from app.repository import item_repository
from app.model.item_model import Item

async def search_items(db, query: str):
    items = []
    items = await item_repository.search_items(db, query)
    return items

async def search_item_by_cod_item(db, cod_item: str):
    item = Item()
    item = await item_repository.search_item_by_cod_item(db, cod_item)
    return item

async def search_item_inventory(db, query: str):
    items = []
    items = await item_repository.search_item_inventory(db, query)
    return items
