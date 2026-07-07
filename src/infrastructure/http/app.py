"""FastAPI application factory and ASGI entry point.

Start the HTTP server with::

    uvicorn market_data_be.infrastructure.http.app:app --host 0.0.0.0 --port 8000

Factory alternative::

    uvicorn market_data_be.infrastructure.http.app:create_app --factory
"""

from fastapi import FastAPI

from market_data_be.infrastructure.http.routes.health import router as health_router

APP_TITLE = "Market Data backend"
APP_VERSION = "5.5.0"


def create_app() -> FastAPI:
    application = FastAPI(title=APP_TITLE, version=APP_VERSION)
    application.include_router(health_router)
    return application


app = create_app()
