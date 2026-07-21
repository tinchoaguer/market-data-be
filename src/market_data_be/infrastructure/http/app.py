"""FastAPI application factory and ASGI entry point.

Start the HTTP server with::

    uvicorn market_data_be.infrastructure.http.app:app --host 0.0.0.0 --port 8000

Factory alternative::

    uvicorn market_data_be.infrastructure.http.app:create_app --factory
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from market_data_be.infrastructure.http.composition import (
    build_analyze_market,
    build_classify_market,
    build_get_market_data,
)
from market_data_be.infrastructure.http.mappers.analysis import (
    InvalidAnalysisMessageParamsError,
    UndeclaredAnalysisMessageCodeError,
    UndeclaredAnalysisReasonError,
    UndeclaredAnalysisRegimeError,
)
from market_data_be.infrastructure.http.mappers.classification import (
    UndeclaredClassificationReasonError,
)
from market_data_be.infrastructure.http.routes.analysis import (
    router as analysis_router,
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


# Local Vite origins; FE calls the API cross-origin via VITE_API_BASE_URL.
_LOCAL_FRONTEND_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
)


def create_app() -> FastAPI:
    application = FastAPI(title=APP_TITLE, version=APP_VERSION)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(_LOCAL_FRONTEND_ORIGINS),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.state.classify_market = build_classify_market()
    application.state.get_market_data = build_get_market_data()
    application.state.analyze_market = build_analyze_market()
    application.include_router(health_router)
    application.include_router(classification_router)
    application.include_router(market_data_router)
    application.include_router(analysis_router)

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

    @application.exception_handler(UndeclaredClassificationReasonError)
    async def undeclared_classification_reason_handler(
        _request: Request,
        _exc: UndeclaredClassificationReasonError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred"},
        )

    @application.exception_handler(UndeclaredAnalysisRegimeError)
    async def undeclared_analysis_regime_handler(
        _request: Request,
        _exc: UndeclaredAnalysisRegimeError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred"},
        )

    @application.exception_handler(UndeclaredAnalysisReasonError)
    async def undeclared_analysis_reason_handler(
        _request: Request,
        _exc: UndeclaredAnalysisReasonError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred"},
        )

    @application.exception_handler(UndeclaredAnalysisMessageCodeError)
    async def undeclared_analysis_message_code_handler(
        _request: Request,
        _exc: UndeclaredAnalysisMessageCodeError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred"},
        )

    @application.exception_handler(InvalidAnalysisMessageParamsError)
    async def invalid_analysis_message_params_handler(
        _request: Request,
        _exc: InvalidAnalysisMessageParamsError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred"},
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
