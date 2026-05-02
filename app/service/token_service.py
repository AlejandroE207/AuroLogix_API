from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.core.security import create_access_token_and_refresh_token, verify_token, create_token
from app.core.config import get_settings
from app.repository.token_repository import TokenRepository

settings = get_settings()

class TokenService:
    def __init__(self, db: Session):
        self.repository = TokenRepository(db)

    async def issue_new_tokens(self, user_id: int):
        """
        Lógica para el Login: crea tokens y guarda el refresh en DB.
        """
        # 1. Generar los strings JWT (usando tu security.py)
        tokens = await create_access_token_and_refresh_token(user_id)
        
        # 2. Calcular expiración para la DB
        expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        
        # 3. Persistir en base de datos
        self.repository.save_refresh_token(
            user_id=user_id,
            token=tokens["refresh_token"],
            expires_at=expires_at
        )
        
        return tokens

    async def refresh_access_token(self, refresh_token: str):
        """
        Lógica para renovar el Access Token sin pedir contraseña.
        """
        # 1. Verificar validez del JWT string
        payload = await verify_token(refresh_token, token_type="refresh")
        if not payload:
            raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")

        # 2. Verificar existencia y estado en la Base de Datos
        db_token = self.repository.get_token_from_db(refresh_token)
        if not db_token or db_token.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Token revocado o inexistente")

        # 3. Generar un NUEVO Access Token
        new_access_token = await create_token(
            data={"user_id": db_token.user_id},
            token_type="access"
        )

        return {
            "access_token": new_access_token,
            "refresh_token": refresh_token, # Reutilizamos el mismo refresh
            "token_type": "bearer"
        }