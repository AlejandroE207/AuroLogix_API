from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine (
    settings.database_url,
    pool_size=10, # Define el tamaño del pool de conexiones
    max_overflow=20, # Permite manejar hasta 20 conexiones adicionales si el pool está lleno
    pool_pre_ping=True, # Verifica que las conexiones estén activas antes de usarlas
    pool_recycle=3600, # Recicla las conexiones cada hora para evitar timeouts
    
    echo = True # Cambia a True para ver las consultas SQL en la consola   
)

SessionLocal = async_sessionmaker(
    bind=engine, # Establece la conexión con la base de datos
    class_=AsyncSession, # Utiliza sesiones asíncronas
    expire_on_commit=False # Evita que los objetos se expiren después de cada commit, lo que permite seguir trabajando con ellos sin necesidad de recargarlos desde la base de datos
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        yield session


