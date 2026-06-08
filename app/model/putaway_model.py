from typing import Optional

from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import mapped_column
from sqlalchemy import DateTime

class Putaway(BaseModel):
    id: int = None
    id_item: int = None
    lote: str = None
    cantidad: float = None
    posicion_sugerida_id: int = None
    posicion_confirmada_id: int = None
    id_usuario: int = None
    fecha: datetime = datetime.now()
    estado: int = None
    fecha_vencimiento: Optional[datetime] = None
    
    result: int = None
    message: str = None