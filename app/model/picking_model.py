from typing import Optional
from pydantic import BaseModel, Field

class CommonPicking(BaseModel):
    id: Optional[int] = None
    estado: Optional[int] = None
    
    result: Optional[int] = None
    message: Optional[str] = None
    
class Orden(CommonPicking):
    codigo: Optional[str] = None
    cliente: Optional[str] = None
    tipo: Optional[str] = None
    id_usuario: Optional[int] = None
    detalles: Optional[str] = None
    
class Picking_items(BaseModel):
    id: Optional[int] = None
    id_item: Optional[int] = None
    cod_item: Optional[str] = None
    nombre_item: Optional[str] = None
    cantidad: Optional[int] = None
    lote: Optional[str] = None
    id_posicion_origen: Optional[int] = None
    cod_posicion_origen: Optional[str] = None
    
    result: Optional[int] = None
    message: Optional[str] = None
    

class Picking(CommonPicking):
    id_posicion: Optional[int] = None
    id_orden: Optional[int] = None
    id_usuario: Optional[int] = None
    
class Picking_detalle(CommonPicking):
    id_picking: Optional[int] = None
    items : list[Picking_items] = Field(default_factory=list)
    
    
# class Picking_task(Picking_detalle):
#     id_posicion_origen:int = None
    

    
    
    
    
    
    
    
    
    
    
    
    
    