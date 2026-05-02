from app.core.security import create_token, verify_token
from app.repository import auth_repository


async def login_user(db, nombre: str, contrasena: str):
    return await auth_repository.login(db,  nombre, contrasena)


async def refresh_access_token(db, refresh_token: str):
    token_payload = verify_token(refresh_token, token_type="refresh")
    if not token_payload:
        return {
            "result": 0,
            "message": "Refresh token inválido o expirado",
        }

    stored_token = await auth_repository.get_refresh_token(db, refresh_token)
    if not stored_token:
        return {
            "result": 0,
            "message": "Refresh token revocado o inexistente",
        }

    new_access_token = create_token(
        data={"user_id": stored_token.id_usuario},
        token_type="access",
    )

    return {
        "result": 1,
        "message": "Access token renovado correctamente",
        "access_token": new_access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
    }


async def logout_user(db, refresh_token: str):
    revoked = await auth_repository.revoke_refresh_token(db, refresh_token)
    if not revoked:
        return {
            "result": 0,
            "message": "No se pudo revocar el refresh token",
        }

    return {
        "result": 1,
        "message": "Logout realizado correctamente",
    }


async def logout_all_user_tokens(db, user_id: int):
    revoked = await auth_repository.revoke_all_user_tokens(db, user_id)
    if not revoked:
        return {
            "result": 0,
            "message": "No se pudieron revocar los tokens del usuario",
        }

    return {
        "result": 1,
        "message": "Tokens del usuario revocados correctamente",
    }