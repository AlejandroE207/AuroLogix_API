from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.service import user_service
from app.model.user_model import User

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.get("/{user_id}")
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await user_service.get_user_by_id(db, user_id)
    if user.result == 1:
        return user
    else:
        raise HTTPException(status_code=404, detail=user.message)
    
@router.get("/search_by_name/{nombre}")
async def read_user_by_name(nombre: str, db: AsyncSession = Depends(get_db)):
    user_list = await user_service.get_list_user_by_name(db, nombre)
    if user_list and user_list[0].result == 1:
        return user_list
    else:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

@router.post("/create_user")
async def create_user(user: User, db: AsyncSession = Depends(get_db)):
    """ Endpoint para crear un nuevo usuario. Recibe un objeto User en el cuerpo de la solicitud y lo guarda en la base de datos."""
    user_data = User()
    user_data = await user_service.create_user(db, user)
    if user_data.result == 1:
        return user_data.message
    else:
        raise HTTPException(status_code=400, detail=user_data.message)
    
@router.put("/update_user/{user_id}")
async def update_user( user: User, db: AsyncSession = Depends(get_db)):
    """ Endpoint para actualizar un usuario existente. Recibe el ID del usuario a actualizar y un objeto User con los nuevos datos."""
    user_data = User()
    user_data = await user_service.update_user(db, user)
    if user_data.result == 1:
        return user_data.message
    else:
        raise HTTPException(status_code=400, detail=user_data.message)

@router.delete("/delete_user/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """ Endpoint para eliminar un usuario. Recibe el ID del usuario a eliminar."""
    result = await user_service.delete_user(db, user_id)
    if result:
        return {"message": "Usuario eliminado correctamente"}
    else:
        raise HTTPException(status_code=400, detail="Error al eliminar el usuario")

