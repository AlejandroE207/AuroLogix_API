from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# Campos comunes entre padre e hijo
class CommonInventory(BaseModel):
    id: Optional[int] = None
    id_item: Optional[int] = None
    lote: Optional[str] = None
    cantidad: Optional[float] = None
    result: Optional[int] = None
    message: Optional[str] = None


# Modelo padre: tiene campos propios que el hijo NO tendra
class Motion(CommonInventory):
    tipo_movimiento: Optional[int] = None
    posicion_origen_id: Optional[int] = None
    posicion_destino_id: Optional[int] = None
    fecha: Optional[datetime] = None
    id_usuario: Optional[int] = None



# Modelo hijo: no incluye los campos específicos del padre, pero añade 2 extras
class Inventory(CommonInventory):
    id_posicion: Optional[int] = None
    fecha_vencimiento: Optional[datetime] = None
    detalles: Optional[str] = None
    



    
 