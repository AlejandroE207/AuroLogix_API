from pydantic import BaseModel

class Position(BaseModel):
    id: int = None
    cod_posicion: str = None
    bodega: int = None
    estado: int = None
    
    result: int = None
    message: str = None