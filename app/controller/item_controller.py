from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.service import item_service
from app.model.item_model import Item
from app.core.security import(
    get_current_token_payload,
    get_current_user_id,
    get_current_user_role,
    require_role
)

router = APIRouter(
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(get_current_token_payload)]
)

@router.get("/search")
async def search_items(
    query: str, 
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role)
):
    """Busca items por nombre o descripción. Accesible para roles 1 y 2."""
    items = await item_service.search_items(db, query)
    if items and items[0].result == 1:
        return items
    else:
        raise HTTPException(status_code=404, detail="No se encontraron items que coincidan con la búsqueda")
    
@router.get("/search_item_by_cod_item")
async def search_item_by_cod_item(
    cod_item: str,
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role)
):
    """Busca un item por su codigo de item. Accesible para roles 1 y 2."""
    item = await item_service.search_item_by_cod_item(db, cod_item)
    if item and item.result == 1:
        return item
    else:
        raise HTTPException(status_code=404, detail="No se encontró un item con el código proporcionado")
    
@router.get("/search_item_inventory")
async def search_item_inventory(
    query: str, 
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role)
):
    """Busca items por nombre o descripción y muestra su inventario. Accesible para roles 1 y 2."""
    items = await item_service.search_item_inventory(db, query)
    if items and items[0].result == 1:
        return items
    else:
        raise HTTPException(status_code=404, detail="No se encontraron items que coincidan con la búsqueda")    