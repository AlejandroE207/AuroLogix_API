from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.service import user_service
from app.model.user_model import User
from app.core.security import (
    get_current_token_payload,
    get_current_user_id,
    get_current_user_role,
    require_role,
)

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_token_payload)]
)

@router.get("/user_by_id/{user_id}")
async def read_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
):
    """Lee un usuario. Accesible para roles 1 y 2."""
    user = await user_service.get_user_by_id(db, user_id)
    if user.result == 1:
        return user
    else:
        raise HTTPException(status_code=404, detail=user.message)
    
@router.get("/user_by_name/{nombre}")
async def read_user_by_name(
    nombre: str,
    db: AsyncSession = Depends(get_db),
    current_user_role: int = Depends(get_current_user_role),
):
    """Busca usuarios por nombre. Accesible para roles 1 y 2."""
    user_list = await user_service.get_list_user_by_name(db, nombre)
    if user_list and user_list[0].result == 1:
        return user_list
    else:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

@router.post("/create_user")
async def create_user(
    user: User,
    db: AsyncSession = Depends(get_db),
    role_check: int = Depends(require_role(2)),
):
    """Crea un nuevo usuario. Solo para rol 2 (admin)."""
    user_data = User()
    user_data = await user_service.create_user(db, user)
    if user_data.result == 1:
        return user_data.message
    else:
        raise HTTPException(status_code=400, detail=user_data.message)
    
@router.put("/update_user/{user_id}")
async def update_user(
    user: User,
    db: AsyncSession = Depends(get_db),
    role_check: int = Depends(require_role(2)),
):
    """Actualiza un usuario existente. Solo para rol 2 (admin)."""
    user_data = User()
    user_data = await user_service.update_user(db, user)
    if user_data.result == 1:
        return user_data.message
    else:
        raise HTTPException(status_code=400, detail=user_data.message)

@router.delete("/delete_user/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    role_check: int = Depends(require_role(2)),
):
    """Elimina un usuario. Solo para rol 2 (admin)."""
    result = await user_service.delete_user(db, user_id)
    if result:
        return {"message": "Usuario eliminado correctamente"}
    else:
        raise HTTPException(status_code=400, detail="Error al eliminar el usuario")

