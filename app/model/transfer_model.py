from typing import Optional

from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import mapped_column
from sqlalchemy import DateTime

class Transfer(BaseModel):
    id: Optional[int]= None
    id_inventario: Optional[int] = None
    id_item: Optional[int] = None
    lote: Optional[str] = None
    # tipo_item : Optional[str] = None
    cantidad: Optional[float] = None
    posicion_origen_id: Optional[int] = None
    posicion_sugerida_id: Optional[int] = None
    posicion_destino_id: Optional[int] = None
    cod_posicion_sugerida: Optional[str] = None
    cod_posicion_destino: Optional[str] = None
    id_usuario: Optional[int] = None
    fecha: Optional[datetime] = datetime.now()
    estado: Optional[int] = None
    fecha_vencimiento: Optional[datetime] = None
    
    result: Optional[int] = None
    message: Optional[str] = None