from app.repository import user_repository
from app.model.user_model import User
from app.core.security import get_hash_password

async def get_user_by_id(db, user_id: int):
    user_data = User()
    user_data = await user_repository.get_user_by_id(db, user_id)
    return user_data

async def get_list_user_by_name(db, nombre: str):
    user_data_list = []
    user_data_list = await user_repository.get_user_by_name(db, nombre)
    return user_data_list

async def create_user(db, user: User):
    user.contrasena = get_hash_password(user.contrasena)
    user_data = User()
    user_data = await user_repository.create_user(db, user)
    return user_data

async def update_user(db, user: User):
    user_data = User()
    user_data = await user_repository.update_user(db, user)
    return user_data

async def delete_user(db, user_id: int):
    return await user_repository.delete_user(db, user_id)