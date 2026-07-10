# Feature History: market-data-provider

```yaml
history:
  - date: 2026-07-08
    feature:
      id: 3
      slug: market-data-provider
    workflow_stage: Completed
```

## Summary

Port-based market data retrieval layer with `MarketDataProvider` contract, `MockMarketDataProvider` JSON adapter, shared deserializer, and `GetMarketData` use case.

## Deliverables

- `src/application/contracts/market_data_provider.py` — `MarketDataProvider` Protocol
- `src/infrastructure/market_data/mock_provider.py` — `MockMarketDataProvider` adapter
- `src/infrastructure/market_data/deserializer.py` — shared JSON → `MarketData` mapping
- `src/infrastructure/market_data/symbol_resolver.py` — symbol → filename resolution
- `src/infrastructure/market_data/errors.py` — `MarketDataNotFoundError`, `MarketDataDeserializationError`
- `src/application/use_cases/get_market_data.py` — port-injected use case
- Unit tests in `src/infrastructure/tests/` and `src/application/tests/`

## Review

**Decision:** APPROVED

All 14 requirements, 6 NFRs, and 8 acceptance criteria passed. 82/82 tests green. Domain modules remain provider-free.

## Usage

```python
from market_data_be.infrastructure.market_data.mock_provider import MockMarketDataProvider
from market_data_be.application.use_cases.get_market_data import GetMarketData

provider = MockMarketDataProvider()
use_case = GetMarketData(provider)
market_data = use_case.execute("BTC/USDT")
```
