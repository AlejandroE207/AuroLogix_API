from passlib.context import CryptContext
from app.core.config import get_settings
from datetime import datetime, timedelta
from typing import Optional, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.model.user_model import User
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError


settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=True)

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
    except ExpiredSignatureError:
        return None
    except JWTError:
        return None


def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Valida el access token enviado en `Authorization: Bearer <token>`."""
    payload = verify_token(credentials.credentials, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_user_id(payload: dict = Depends(get_current_token_payload)) -> int:
    """Extrae el user_id del payload del token."""
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Token no contiene user_id válido",
        )
    return user_id


def get_current_user_role(payload: dict = Depends(get_current_token_payload)) -> int:
    """Extrae el rol del payload del token."""
    role = payload.get("rol")
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Token no contiene rol válido",
        )
    return role


def require_role(*allowed_roles: int):
    """
    Crea una dependencia que valida que el usuario tenga uno de los roles permitidos.
    Uso: Depends(require_role(1, 2, 3))
    """
    async def role_checker(role: int = Depends(get_current_user_role)) -> int:
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Rol requerido: {allowed_roles}",
            )
        return role
    return role_checker

    
# Metodo de creacion de access token y refresh token
def create_access_token_and_refresh_token(user_data: Union[User, dict, int]) -> dict:
    """Crea access y refresh tokens. Acepta un objeto `User`, un diccionario con campos
    o directamente un `user_id` (int).
    """
    if isinstance(user_data, int):
        payload_base = {"user_id": user_data}
    elif isinstance(user_data, dict):
        payload_base = user_data.copy()
    else:
        # intentar extraer atributos del modelo User
        payload_base = {
            "user_id": getattr(user_data, "id", None),
            "nombre": getattr(user_data, "nombre", None),
            "rol": getattr(user_data, "rol", None),
            "activo": getattr(user_data, "activo", None),
        }

    access_token = create_token(data=payload_base, token_type="access")
    refresh_token = create_token(data=payload_base, token_type="refresh")

    return {"access_token": access_token, "refresh_token": refresh_token}

