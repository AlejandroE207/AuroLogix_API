from typing import Optional
from pydantic import BaseModel

class Position(BaseModel):
    id: Optional[int] = None
    cod_posicion: Optional[str] = None
    bodega: Optional[int] = None
    estado: Optional[int] = None
    reserva: Optional[str] = None
    
    result: Optional[int] = None
    message: Optional[str] = None