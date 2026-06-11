from pydantic import BaseModel
from typing import List, Optional

class ItemsOrderView(BaseModel):
    id_item: int
    cod_item: int
    item: str
    cantidad: float
    unidad_medida: str
    lote: str | None
    
class OrderView(BaseModel):
    id: int
    codigo: str
    cliente: str
    estado: int
    productos: List[ItemsOrderView]
    result: Optional[int] = None
    message: Optional[str] = None