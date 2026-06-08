from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class MotionView(BaseModel):
    id: Optional[int] = None
    tipo_movimiento: Optional[str] = None
    item: Optional[str] = None
    cantidad: Optional[float] = None
    unidad_medida: Optional[str] = None
    lote: Optional[str] = None
    posicion_origen: Optional[str] = None
    posicion_destino: Optional[str] = None
    fecha: Optional[datetime] = None
    usuario: Optional[str] = None
    result: Optional[int] = None
    message: Optional[str] = None
    
