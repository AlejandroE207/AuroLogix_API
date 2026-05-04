from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from fastapi import HTTPException

from app.core.security import create_access_token_and_refresh_token, verify_token, create_token
from app.core.config import get_settings
from app.repository import auth_repository

settings = get_settings()


class TokenService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def issue_new_tokens(self, user_id: int):
        """Genera access+refresh y guarda el refresh en BD usando `auth_repository`."""
        tokens = create_access_token_and_refresh_token(user_id)

        expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

        saved = await auth_repository.create_refresh_token(
            db=self.db,
            id_usuario=user_id,
            token=tokens["refresh_token"],
            fecha_expiracion=expires_at,
        )

        if not saved:
            raise HTTPException(status_code=500, detail="No se pudo guardar refresh token")

        return tokens

    async def refresh_access_token(self, refresh_token: str):
        """Valida el refresh token y genera un nuevo access token si está OK."""
        payload = verify_token(refresh_token, token_type="refresh")
        if not payload:
            raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")

        db_token = await auth_repository.get_refresh_token(self.db, refresh_token)
        if not db_token:
            raise HTTPException(status_code=401, detail="Refresh token revocado o inexistente")

        new_access_token = create_token(data={"user_id": db_token.id_usuario}, token_type="access")

        return {
            "access_token": new_access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }