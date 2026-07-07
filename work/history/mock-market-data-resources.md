# Feature History: mock-market-data-resources

```yaml
history:
  - date: 2026-07-07
    feature:
      id: 2
      slug: mock-market-data-resources
    workflow_stage: Completed
```

## Summary

Static JSON market data fixtures for BTC/USDT and ETH/USDT, conforming to the `MarketData` domain model schema. Ready for use by the mock market data provider (feature 3).

## Deliverables

- `resources/market_data/btc_usdt.json` — 32 M15 candles, 5×5 order book, ~67k USDT
- `resources/market_data/eth_usdt.json` — 32 M15 candles, 5×5 order book, ~3.5k USDT
- `resources/market_data/README.md` — schema contract and serialization rules
- `resources/tests/test_market_data_fixtures.py` — 15 conformance tests

## Review

**Decision:** APPROVED

All 16 requirements, 5 NFRs, and 9 acceptance criteria passed. No domain or provider code introduced.

## Usage

Fixtures are static resources. Loading/parsing will be implemented in feature 3 (`market-data-provider`).
