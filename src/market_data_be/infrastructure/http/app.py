"""FastAPI application factory and ASGI entry point.

Start the HTTP server with::

    uvicorn market_data_be.infrastructure.http.app:app --host 0.0.0.0 --port 8000

Factory alternative::

    uvicorn market_data_be.infrastructure.http.app:create_app --factory
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from market_data_be.infrastructure.http.composition import (
    build_classify_market,
    build_get_market_data,
)
from market_data_be.infrastructure.http.routes.classification import (
    router as classification_router,
)
from market_data_be.infrastructure.http.routes.health import router as health_router
from market_data_be.infrastructure.http.routes.market_data import (
    router as market_data_router,
)
from market_data_be.infrastructure.market_data.errors import (
    MarketDataDeserializationError,
    MarketDataNotFoundError,
)

APP_TITLE = "Market Data backend"
APP_VERSION = "5.5.0"


def create_app() -> FastAPI:
    application = FastAPI(title=APP_TITLE, version=APP_VERSION)
    application.state.classify_market = build_classify_market()
    application.state.get_market_data = build_get_market_data()
    application.include_router(health_router)
    application.include_router(classification_router)
    application.include_router(market_data_router)

    @application.exception_handler(MarketDataNotFoundError)
    async def market_data_not_found_handler(
        _request: Request,
        exc: MarketDataNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": f"market data not found for symbol {exc.symbol!r}"},
        )

    @application.exception_handler(MarketDataDeserializationError)
    async def market_data_deserialization_handler(
        _request: Request,
        _exc: MarketDataDeserializationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred while processing market data"},
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred"},
        )

    return application


app = create_app()
