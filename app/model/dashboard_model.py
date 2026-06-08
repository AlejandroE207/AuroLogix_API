from typing import Optional
from pydantic import BaseModel

class Summary(BaseModel):
    total_posiciones: Optional[int] = None
    posiciones_ocupadas: Optional[int] = None
    posiciones_disponibles: Optional[int] = None
    alertas_vencido: Optional[int] = None
    alertas_vencimiento_leve: Optional[int] = None
    alertas_vencimiento_critico: Optional[int] = None
    
    result: Optional[int] = None
    message: Optional[str] = None
    