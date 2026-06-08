from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class PositionView(BaseModel):
    posicion_id: Optional[int] = None
    cod_posicion: Optional[str] = None
    bodega: Optional[int] = None
    posicion_estado: Optional[str] = None
    reserva: Optional[str] = None
    id_item: Optional[int] = None
    producto: Optional[str] = None
    cantidad: Optional[float] = None
    unidad_medida: Optional[str] = None
    lote: Optional[str] = None
    fecha_vencimiento: Optional[datetime] = None
    dias_restantes: Optional[int] = None
    estado_alerta: Optional[str] = None
    result: Optional[int] = None
    message: Optional[str] = None
    