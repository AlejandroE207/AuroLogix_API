from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from app.model.user_model import User
from app.model.refreshToken_model import RefreshToken
from app.core.config import get_settings
from app.core.security import (
    create_access_token_and_refresh_token,
    verify_password, get_hash_password, verify_token
)

settings = get_settings()


async def get_user_by_nombre(db: AsyncSession, nombre: str):
    """
    Obtiene un usuario por nombre para validar credenciales en login
    """
    user_data = User()
    query = text("""
                 SELECT id, nombre, contrasena, rol, activo, creado, actualizado
                 FROM usuarios
                 WHERE nombre = :nombre AND activo = true
                 """)
    try:
        result = await db.execute(query, {"nombre": nombre})
        row = result.mappings().first()
        if row:
            user_data.id = row["id"]
            user_data.nombre = row["nombre"]
            user_data.contrasena = row["contrasena"]
            user_data.rol = row["rol"]
            user_data.activo = row["activo"]
            user_data.creado = row["creado"]
            user_data.actualizado = row["actualizado"]
            user_data.result = 1
            user_data.message = "Usuario encontrado"
        else:
            user_data.result = 0
            user_data.message = "Usuario no encontrado o inactivo"
        return user_data
    except Exception as e:
        print(f"Error al obtener usuario por email: {e}")
        user_data.result = 0
        user_data.message = "Error al obtener el usuario"
        return user_data


async def create_refresh_token(db: AsyncSession, id_usuario: int, token: str, fecha_expiracion: datetime):
    """
    Crea un nuevo refresh token en la base de datos
    """
    token_data = RefreshToken()
    query = text("""
                 INSERT INTO refresh_tokens (id_usuario, token, fecha_creacion, fecha_expiracion)
                 VALUES (:id_usuario, :token, :fecha_creacion, :fecha_expiracion)
                 RETURNING id, id_usuario, token, fecha_creacion, fecha_expiracion
                 """)
    try:
        result = await db.execute(query, {
            "id_usuario": id_usuario,
            "token": token,
            "fecha_creacion": datetime.now(),
            "fecha_expiracion": fecha_expiracion
        })
        await db.commit()
        row = result.mappings().first()
        if row:
            token_data.id = row["id"]
            token_data.id_usuario = row["id_usuario"]
            token_data.token = row["token"]
            token_data.fecha_creacion = row["fecha_creacion"]
            token_data.fecha_expiracion = row["fecha_expiracion"]
            return token_data
        else:
            return None
    except Exception as e:
        print(f"Error al crear refresh token: {e}")
        await db.rollback()
        return None


async def get_refresh_token(db: AsyncSession, token: str):
    """
    Obtiene un refresh token válido por su valor
    """
    token_data = RefreshToken()
    query = text("""
                 SELECT id, id_usuario, token, fecha_creacion, fecha_expiracion
                 FROM refresh_tokens
                 WHERE token = :token AND fecha_expiracion > NOW()
                 """)
    try:
        result = await db.execute(query, {"token": token})
        row = result.mappings().first()
        if row:
            token_data.id = row["id"]
            token_data.id_usuario = row["id_usuario"]
            token_data.token = row["token"]
            token_data.fecha_creacion = row["fecha_creacion"]
            token_data.fecha_expiracion = row["fecha_expiracion"]
            return token_data
        else:
            return None
    except Exception as e:
        print(f"Error al obtener refresh token: {e}")
        return None


async def revoke_refresh_token(db: AsyncSession, token: str):
    """
    Revoca un refresh token eliminándolo de la base de datos
    """
    query = text("""
                 DELETE FROM refresh_tokens
                 WHERE token = :token
                 """)
    try:
        result = await db.execute(query, {"token": token})
        await db.commit()
        return result.rowcount > 0
    except Exception as e:
        print(f"Error al revocar refresh token: {e}")
        await db.rollback()
        return False


async def revoke_all_user_tokens(db: AsyncSession, id_usuario: int):
    """
    Revoca todos los refresh tokens de un usuario (logout en todos los dispositivos)
    """
    query = text("""
                 DELETE FROM refresh_tokens
                 WHERE id_usuario = :id_usuario
                 """)
    try:
        result = await db.execute(query, {"id_usuario": id_usuario})
        await db.commit()
        return result.rowcount > 0
    except Exception as e:
        print(f"Error al revocar tokens del usuario: {e}")
        await db.rollback()
        return False
    
async def login(db: AsyncSession, nombre: str, contrasena: str):
    """
    Autentica al usuario y genera access/refresh token.
    """
    try:
        user_data = await get_user_by_nombre(db, nombre)

        if user_data.result != 1:
            return user_data


        if not verify_password(contrasena, user_data.contrasena):
            user_data.result = 0
            user_data.message = "Contraseña incorrecta"
            return user_data

        tokens = create_access_token_and_refresh_token(user_data)
        refresh_expires_at = datetime.utcnow() + timedelta(
            days=settings.refresh_token_expire_days
        )

        refresh_saved = await create_refresh_token(
            db=db,
            id_usuario=user_data.id,
            token=tokens["refresh_token"],
            fecha_expiracion=refresh_expires_at,
        )

        if not refresh_saved:
            user_data.result = 0
            user_data.message = "No se pudo crear el refresh token"
            return user_data

        user_data.access_token = tokens["access_token"]
        user_data.refresh_token = tokens["refresh_token"]
        user_data.token_type = "bearer"
        user_data.result = 1
        user_data.message = "Login exitoso"
        return user_data
    except Exception as e:
        print(f"Error en el proceso de login: {e}")
        user_data = User()
        user_data.result = 0
        user_data.message = "Error al procesar el login"
        return user_data
    