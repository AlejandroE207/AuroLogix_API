from pydantic import BaseModel
from typing import Optional

class Item(BaseModel):
    id: Optional[int] = None
    cod_item: Optional[str] = None
    descripcion: Optional[str] = None
    unidad_medida: Optional[str] = None
    tipo_item: Optional[str] = None
    lote: Optional[str] = None
    result: Optional[int] = None
    message: Optional[str] = None
    
class ItemInventory(Item):
    cantidad: Optional[float] = None