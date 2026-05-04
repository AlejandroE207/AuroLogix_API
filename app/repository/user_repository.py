from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.user_model import User

async def get_user_by_id(db: AsyncSession, id: int):
    user_data = User()
    query = text("""
                 SELECT id, nombre, rol, activo, creado, actualizado
                    FROM usuarios
                    WHERE id = :user_id
                 """)
    try:
        result = await db.execute(query, {"user_id": id})
        row = result.mappings().first()
        if row:
            user_data = User(**dict(row))
            user_data.result = 1
            user_data.message = "Usuario encontrado"
        else:
            user_data.result = 0
            user_data.message = "Usuario no encontrado"
        return user_data
    except Exception as e:
        print(f"Error al obtener el usuario por ID: {e}")
        user_data.result = 0
        user_data.message = "Error al obtener el usuario"
        return user_data

async def get_user_by_name(db: AsyncSession, nombre: str):
    user_data_list = []
    query = text("""
                 SELECT id, nombre, rol, activo, creado, actualizado
                    FROM usuarios
                    WHERE nombre = :nombre  
                 """)
    try:
        result = await db.execute(query, {"nombre": nombre})
        row = result.mappings().all()
        for user in row:
            user_data = User()
            user_data= User(**dict(user))
            user_data.result = 1
            user_data.message = "Usuario encontrado"
            user_data_list.append(user_data)        
        if not user_data_list:
            user_data = User()
            user_data.result = 0
            user_data.message = "Usuario no encontrado"
            user_data_list.append(user_data)
        return user_data_list
    except Exception as e:
        print(f"Error al obtener el usuario por nombre: {e}")
        user_data = User()
        user_data.result = 0
        user_data.message = "Error al obtener el usuario"
        user_data_list.append(user_data)
        return user_data_list

async def verify_user_by_name(db: AsyncSession, nombre: str):
    query = text("""
                    SELECT id FROM usuarios
                    WHERE nombre = :nombre 
                 """)
    try:
        result = await db.execute(query, {"nombre": nombre})
        row = result.scalar()
        if row:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error al verificar el usuario por nombre: {e}")
        return False

async def create_user(db: AsyncSession, user: User):
    user_data = User()
    query = text(""" 
                 INSERT INTO usuarios (nombre, contrasena, rol, activo, creado, actualizado)
                 VALUES (:nombre, :contrasena, :rol, :activo, :creado, :actualizado)
                 RETURNING id, nombre, rol, activo
                 """)
    try:
        if await verify_user_by_name(db, user.nombre):
            user_data.result = 0
            user_data.message = "El nombre de usuario ya existe"
            return user_data
        else:
            result = await db.execute(query, {"nombre": user.nombre, "contrasena": user.contrasena, "rol": user.rol, "activo": user.activo, "creado": user.creado, "actualizado": user.actualizado})
            row = result.mappings().first()
            await db.commit()
            user_data = User(**dict(row))
            user_data.result = 1
            user_data.message = "Usuario creado exitosamente"
            return user_data
    except Exception as e:
        await db.rollback() # Si ocurre un error, se revierte la transacción para mantener la integridad de la base de datos
        user_data.result = 0
        user_data.message = "Error al crear el usuario"
        print(f"Error al crear el usuario: {e}") # Se imprime el error para fines de depuración
        raise e # Se vuelve a lanzar la excepción para que pueda ser manejada por el controlador o middleware correspondiente
    
async def update_user(db: AsyncSession,  user: User):
    user_data = User()
    query = text("""
                 UPDATE usuarios
                 SET nombre = :nombre, contrasena = :contrasena, rol = :rol, activo = :activo, actualizado = :actualizado
                 WHERE id = :user_id
                RETURNING id, nombre, rol, activo, creado, actualizado
                 """)    
    try:
        result = await db.execute(query, {"user_id": user.id, "nombre": user.nombre, 
                                          "contrasena": user.contrasena, "rol": user.rol, 
                                          "activo": user.activo, "actualizado": user.actualizado})
        await db.commit()
        row = result.mappings().first()
        user_data= User(**dict(row))
        user_data.result = 1
        user_data.message = "Usuario actualizado exitosamente"
        return user_data
    except Exception as e:
        await db.rollback() # Si ocurre un error, se revierte la transacción para mantener la integridad de la base de datos
        user_data.result = 0
        user_data.message = "Error al actualizar el usuario"
        print(f"Error al actualizar el usuario: {e}") # Se imprime el error para fines de depuración
        raise e # Se vuelve a lanzar la excepción para que pueda ser manejada por el controlador o middleware correspondiente
    
async def delete_user(db: AsyncSession, user_id: int):
    user_data = User()
    query = text(""" 
                 DELETE FROM usuarios
                 WHERE id = :user_id
                 """)
    try:
        result = await db.execute(query, {"user_id": user_id})
        await db.commit()
        user_data.result = 1
        user_data.message = "Usuario eliminado exitosamente"
        return user_data
    except Exception as e:
        await db.rollback() # Si ocurre un error, se revierte la transacción para mantener la integridad de la base de datos
        user_data.result = 0
        user_data.message = "Error al eliminar el usuario"
        print(f"Error al eliminar el usuario: {e}") # Se imprime el error para fines de depuración
        raise e # Se vuelve a lanzar la excepción para que pueda ser manejada por el controlador o middleware correspondiente