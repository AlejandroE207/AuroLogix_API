from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CommonInvAux(BaseModel):
    id: Optional[int] = None
    result: Optional[int] = None
    message: Optional[str] = None
    

class InvAux(CommonInvAux):
    id_posicion : Optional[int] = None
    id_item : Optional[int] = None
    lote: Optional[str] = None
    fecha_vencimiento: Optional[datetime] = None
    estado: Optional[int] = None
    
class InvAuxCont(CommonInvAux):
    id_invAux : Optional[int] = None
    numCont: Optional[int] = None
    cantidad: Optional[float] = None
    fecha: Optional[datetime] = None
    id_usuario: Optional[int] = None