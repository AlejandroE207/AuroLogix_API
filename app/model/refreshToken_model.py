from datetime import datetime
from pydantic import BaseModel

class RefreshToken(BaseModel):
    id: int = None
    id_usuario: int = None
    token : str = None
    fecha_creacion : datetime = None
    fecha_expiracion : datetime = None