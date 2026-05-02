from datetime import date
from pydantic import BaseModel

class User(BaseModel):
    id: int = None
    nombre: str = None
    contrasena: str = None
    rol: int = None
    activo: bool = True
    creado: date = None
    actualizado: date = None
    result:int = None
    message:str = None
    access_token: str = None
    refresh_token: str = None
    token_type: str = None