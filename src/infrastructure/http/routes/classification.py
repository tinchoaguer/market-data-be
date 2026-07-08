from fastapi import APIRouter, Depends, HTTPException, Request

from market_data_be.application.use_cases.classify_market import ClassifyMarket
from market_data_be.infrastructure.http.dtos.classification import MarketClassificationResponse
from market_data_be.infrastructure.http.mappers.classification import (
    map_market_classification_to_response,
)
from market_data_be.infrastructure.http.validation.symbol import parse_url_symbol

router = APIRouter(tags=["classification"])


def get_classify_market(request: Request) -> ClassifyMarket:
    return request.app.state.classify_market


@router.get(
    "/markets/{base}/{quote}/classification",
    include_in_schema=False,
)
def get_market_classification_slash_rejected(
    base: str,
    quote: str,
) -> MarketClassificationResponse:
    del base, quote
    raise HTTPException(
        status_code=422,
        detail="Invalid symbol format: expected BASE-QUOTE hyphen-separated pair",
    )


@router.get(
    "/markets/{symbol}/classification",
    response_model=MarketClassificationResponse,
)
def get_market_classification(
    symbol: str,
    classify_market: ClassifyMarket = Depends(get_classify_market),
) -> MarketClassificationResponse:
    try:
        internal_symbol = parse_url_symbol(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    classification = classify_market.execute(internal_symbol)
    return map_market_classification_to_response(classification)
