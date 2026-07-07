"""Portfolio exposure and allocation capacity (pure analysis, no session state)."""

from ..models.assessments import ExposureComponents, ExposureProfile
from ..models.market import MarketData
from ..models.portfolio import PortfolioConstraints, PortfolioState
from . import candle_metrics as cm

MIN_KLINES = 30
DEFAULT_TOTAL_VALUE = 10_000.0
VOL_PERIOD = 20


class PortfolioManager:
    def evaluate(
        self,
        market_data: MarketData,
        portfolio_state: PortfolioState,
        constraints: PortfolioConstraints | None = None,
    ) -> ExposureProfile:
        limits = constraints or PortfolioConstraints()
        symbol = market_data.symbol
        total_value = portfolio_state.total_value
        allocated = portfolio_state.allocated_for(symbol)
        total_allocated = portfolio_state.total_allocated
        exposure_pct = allocated / total_value if total_value > 0 else 0.0
        portfolio_exposure_pct = total_allocated / total_value if total_value > 0 else 0.0

        if len(market_data.candles) < MIN_KLINES:
            recommended_pct = limits.insufficient_data_recommended_pct
            recommended_value = total_value * recommended_pct
            return ExposureProfile(
                symbol=symbol,
                total_value=total_value,
                exposure_pct=exposure_pct,
                allocated_value=allocated,
                portfolio_exposure_pct=portfolio_exposure_pct,
                available_capacity_pct=max(0.0, 1.0 - portfolio_exposure_pct),
                symbol_weight_cap_pct=limits.max_symbol_weight,
                recommended_allocation_pct=recommended_pct,
                recommended_allocation_value=recommended_value,
                components=ExposureComponents(
                    vol_budget_pct=0.0,
                    liquidity_cap_value=0.0,
                ),
                insufficient_data=True,
            )

        components = self._compute_components(market_data, limits)
        recommended_value = self._recommended_allocation_value(
            total_value=total_value,
            allocated=allocated,
            total_allocated=total_allocated,
            components=components,
            limits=limits,
        )
        recommended_pct = recommended_value / total_value if total_value > 0 else 0.0

        return ExposureProfile(
            symbol=symbol,
            total_value=total_value,
            exposure_pct=exposure_pct,
            allocated_value=allocated,
            portfolio_exposure_pct=portfolio_exposure_pct,
            available_capacity_pct=max(0.0, 1.0 - portfolio_exposure_pct),
            symbol_weight_cap_pct=limits.max_symbol_weight,
            recommended_allocation_pct=recommended_pct,
            recommended_allocation_value=recommended_value,
            components=components,
        )

    @staticmethod
    def _recommended_allocation_value(
        *,
        total_value: float,
        allocated: float,
        total_allocated: float,
        components: ExposureComponents,
        limits: PortfolioConstraints,
    ) -> float:
        symbol_headroom = total_value * limits.max_symbol_weight - allocated
        portfolio_headroom = total_value * limits.max_portfolio_deployed - total_allocated
        vol_budget_value = total_value * components.vol_budget_pct
        liquidity_cap = components.liquidity_cap_value
        return max(
            0.0,
            min(symbol_headroom, portfolio_headroom, vol_budget_value, liquidity_cap),
        )

    @staticmethod
    def _compute_components(
        market_data: MarketData, limits: PortfolioConstraints
    ) -> ExposureComponents:
        candles = market_data.candles
        try:
            vol = cm.returns_volatility(candles, VOL_PERIOD)
        except ValueError:
            vol = limits.vol_reference

        vol_scalar = limits.vol_reference / max(vol, 0.001)
        vol_budget_pct = min(
            limits.max_symbol_weight,
            max(limits.vol_budget_min, vol_scalar * limits.vol_budget_base),
        )

        depth_base = cm.book_top_depth_base(
            market_data.order_book, limits.liquidity_depth_levels
        )
        liquidity_cap_value = (
            depth_base * float(market_data.current_price) * limits.liquidity_depth_fraction
        )

        return ExposureComponents(
            vol_budget_pct=vol_budget_pct,
            liquidity_cap_value=liquidity_cap_value,
        )
