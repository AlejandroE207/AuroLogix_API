from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/")
def get_user():
    return {"HOLA SOY UN USUARIO"}
