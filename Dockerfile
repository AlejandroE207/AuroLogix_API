FROM python:3.12-slim

# Evita .pyc y hace el log de Python sin buffer (útil para ver logs en docker)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Instala dependencias primero (aprovecha la cache de capas de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código de la app
COPY app ./app
COPY run.py .

EXPOSE 8000

# En Linux no existe el problema de ProactorEventLoop de Windows,
# así que corremos uvicorn directamente.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
