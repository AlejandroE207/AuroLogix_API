from pydantic import BaseModel
from typing import Optional, List

class PickingView(BaseModel):
    id: Optional[int] = None
    cod_posicion: Optional[str] = None
    estado: Optional[str] = None
    codigo_orden: Optional[str] = None
    usuario: Optional[str] = None
    result: Optional[int] = None
    message: Optional[str] = None