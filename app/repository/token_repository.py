from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.refreshToken_model import RefreshToken

async def save_refresh_token(
    db: AsyncSession,
    id_usuario: int,
    token: str
) -> RefreshToken:
    refresh_token = RefreshToken(
        id_usuario=id_usuario,
        token=token
    )
    db.add(refresh_token)
    await db.commit()
    await db.refresh(refresh_token)
    return refresh_token

async def get_token(
    db: AsyncSession,
    token: str
) -> Optional[RefreshToken]:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == token)
    )
    return result.scalar_one_or_none()

async def delete_token(
    db: AsyncSession,
    token: str
) -> bool:
    rt = await get_token(db, token)
    if not rt:
        return False
    await db.delete(rt)
    await db.commit()
    return True