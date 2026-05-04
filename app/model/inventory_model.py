from datetime import datetime

from pydantic import BaseModel


# Campos comunes entre padre e hijo
class CommonInventory(BaseModel):
    id: int = None
    id_item: int = None
    lote: str = None
    cantidad: float = None


# Modelo padre: tiene campos propios que el hijo NO tendra
class Motion(CommonInventory):
    tipo_movimiento: str = None
    posicion_origen_id: int = None
    posicion_destino_id: int = None
    fecha: datetime = None
    id_usuario: int = None
    result: int = None
    message: str = None


# Modelo hijo: no incluye los campos específicos del padre, pero añade 2 extras
class Inventory(CommonInventory):
    id_posicion: int = None
    estado: str = None
    detalles: str = None



    
 