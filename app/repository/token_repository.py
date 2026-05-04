from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.refreshToken_model import RefreshToken
from app.repository import auth_repository


async def save_refresh_token(
    db: AsyncSession,
    id_usuario: int,
    token: str,
    expires_at
) -> Optional[RefreshToken]:
    return await auth_repository.create_refresh_token(db, id_usuario, token, expires_at)


async def get_token(
    db: AsyncSession,
    token: str
) -> Optional[RefreshToken]:
    return await auth_repository.get_refresh_token(db, token)


async def delete_token(
    db: AsyncSession,
    token: str
) -> bool:
    return await auth_repository.revoke_refresh_token(db, token)