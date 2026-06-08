from datetime import datetime

from app.repository import motion_repository
from app.model.motion_view_model import MotionView

async def list_motion(db, item: str = None, tipo_movimiento: str = None, desde_fecha: datetime = None, hasta_fecha: datetime = None, limite: int = 50, offset: int = 0):
    motion_data_list = []
    motion_data_list = await motion_repository.list_motion(db, item, tipo_movimiento, desde_fecha, hasta_fecha, limite, offset)
    return motion_data_list