from fastapi import APIRouter, Depends, HTTPException, Request

from market_data_be.application.use_cases.get_market_data import GetMarketData
from market_data_be.infrastructure.http.dtos.market_data import MarketDataResponse
from market_data_be.infrastructure.http.mappers.market_data import map_market_data_to_response
from market_data_be.infrastructure.http.validation.symbol import parse_url_symbol

router = APIRouter(tags=["market-data"])


def get_market_data_use_case(request: Request) -> GetMarketData:
    return request.app.state.get_market_data


@router.get(
    "/markets/{base}/{quote}/market-data",
    include_in_schema=False,
)
def get_market_data_slash_rejected(
    base: str,
    quote: str,
) -> MarketDataResponse:
    del base, quote
    raise HTTPException(
        status_code=422,
        detail="Invalid symbol format: expected BASE-QUOTE hyphen-separated pair",
    )


@router.get(
    "/markets/{symbol}/market-data",
    response_model=MarketDataResponse,
)
def get_market_data(
    symbol: str,
    get_market_data_uc: GetMarketData = Depends(get_market_data_use_case),
) -> MarketDataResponse:
    try:
        internal_symbol = parse_url_symbol(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    market_data = get_market_data_uc.execute(internal_symbol)
    return map_market_data_to_response(market_data)
