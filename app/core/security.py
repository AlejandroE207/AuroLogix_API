from passlib.context import CryptContext
from app.core.config import get_settings
import jwt
from datetime import datetime, timedelta
from typing import Optional, Union
from passlib.context import CryptContext
from app.model.user_model import User
from jose import JWSError, jwt


settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Funcion de encriptacion de la contraseña con Bycript
def get_hash_password(password: str) -> str:
    try:
        password_hash = pwd_context.hash(password)
        print(f"Contraseña original: {password} - Contraseña hasheada: {password_hash}")
        return password_hash
    except Exception as e:
        print(f"Error al hashear la contraseña: {e}")
        raise ValueError("Error al procesar la contraseña")

# Funcion de verificacion de la contraseña
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_token(data: dict, token_type: str = "access") -> str:
    to_encode = data.copy()
    
    if token_type == "access":
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    elif token_type == "refresh":
        expire = datetime.utcnow() + timedelta(
            days = settings.refresh_token_expire_days
        )
    else:
        raise ValueError("Tipo de token no válido")
    
    to_encode.update({
        "exp":expire,
        "type": token_type,
        "iat": datetime.utcnow()
    })
    encode_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm = settings.algorithm
    )
    return encode_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms = [settings.algorithm]
        )
        
        if payload.get("type") !=  token_type:
            return None
        
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    
# Metodo de creacion de access token y refresh token
def create_access_token_and_refresh_token(user_data: User) -> dict:
    access_token =  create_token(
        data = {"user_id":user_data.id,
                "nombre": user_data.nombre,
                "rol": user_data.rol,
                "activo": user_data.activo},
        token_type = "access"
    )
    
    refresh_token =  create_token(
        data = {"user_id":user_data.id,
                "nombre": user_data.nombre,
                "rol": user_data.rol,
                "activo": user_data.activo},
        token_type = "refresh"
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }


