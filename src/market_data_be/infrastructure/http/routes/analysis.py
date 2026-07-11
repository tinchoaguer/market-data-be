from fastapi import APIRouter, Depends, HTTPException, Request

from market_data_be.application.use_cases.analyze_market import AnalyzeMarket
from market_data_be.infrastructure.http.dtos.analysis import MarketAnalysisResponse
from market_data_be.infrastructure.http.mappers.analysis import (
    map_analysis_result_to_response,
)
from market_data_be.infrastructure.http.validation.symbol import parse_url_symbol

router = APIRouter(tags=["analysis"])


def get_analyze_market(request: Request) -> AnalyzeMarket:
    return request.app.state.analyze_market


@router.get(
    "/markets/{base}/{quote}/analysis",
    include_in_schema=False,
)
def get_market_analysis_slash_rejected(
    base: str,
    quote: str,
) -> MarketAnalysisResponse:
    del base, quote
    raise HTTPException(
        status_code=422,
        detail="Invalid symbol format: expected BASE-QUOTE hyphen-separated pair",
    )


@router.get(
    "/markets/{symbol}/analysis",
    response_model=MarketAnalysisResponse,
)
def get_market_analysis(
    symbol: str,
    use_case: AnalyzeMarket = Depends(get_analyze_market),
) -> MarketAnalysisResponse:
    try:
        internal_symbol = parse_url_symbol(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    analysis_result = use_case.execute(internal_symbol)
    return map_analysis_result_to_response(analysis_result)
