from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.service import auth_service
from app.model.user_model import User

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

@router.post("/login")
async def login(name: str, password: str, db: AsyncSession = Depends(get_db)):
    """Inicia sesión con nombre y contraseña, y devuelve access y refresh token."""
    user_data = await auth_service.login_user(db, name, password)
    if user_data.result == 1:
        return {
            "access_token": user_data.access_token,
            "refresh_token": user_data.refresh_token,
            "token_type": user_data.token_type,
        }
    else:
        raise HTTPException(status_code=400, detail=user_data.message)


@router.post("/refresh")
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    """Renueva el access token si el refresh token sigue siendo válido."""
    token_data = await auth_service.refresh_access_token(db, refresh_token)
    if token_data["result"] == 1:
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "token_type": token_data["token_type"],
        }

    raise HTTPException(status_code=401, detail=token_data["message"])


@router.post("/logout")
async def logout(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    """Revoca el refresh token actual para cerrar sesión."""
    result = await auth_service.logout_user(db, refresh_token)
    if result["result"] == 1:
        return {"message": result["message"]}

    raise HTTPException(status_code=400, detail=result["message"])