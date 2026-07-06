"""
Punto de entrada para levantar el servidor en Windows.

Por qué existe este archivo:
psycopg (en modo async) necesita el SelectorEventLoop, pero Uvicorn 0.46
en Windows fuerza internamente `asyncio.ProactorEventLoop` como loop
factory sin importar la política global de asyncio que se configure
(no basta con asyncio.set_event_loop_policy(...) antes de uvicorn.run()).

Por eso aquí NO usamos uvicorn.run() (que es el que fuerza el
ProactorEventLoop en Windows). En su lugar, construimos el servidor
manualmente y llamamos a asyncio.run() nosotros mismos, indicando
explícitamente loop_factory=asyncio.SelectorEventLoop.

Uso:
    python run.py
"""
import asyncio

import uvicorn
from uvicorn._compat import asyncio_run


def main() -> None:
    config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        # reload=True,  # descomenta esto solo cuando programes tú solo,
                         # NUNCA mientras pruebas la app desde el celular
    )
    server = uvicorn.Server(config)
    asyncio_run(server.serve(), loop_factory=asyncio.SelectorEventLoop)


if __name__ == "__main__":
    main()