# Tasks

## Implementation Tasks

Tasks are ordered to minimize dependencies. Each task maps to one or more requirements.

- [x] Create directory `resources/market_data/` at the project root (REQ-001)

- [x] Add `resources/market_data/README.md` documenting: directory purpose, filename convention (`btc_usdt.json`, `eth_usdt.json`), root JSON schema, `MarketData` field mapping, Decimal-as-string rule, ISO 8601 UTC datetime rule, and `Timeframe` enum values (REQ-015, REQ-004, REQ-010, REQ-011)

- [x] Author `resources/market_data/btc_usdt.json` with `symbol: "BTC/USDT"`, realistic BTC price magnitude, ≥ 30 contiguous M15 candles, ≥ 5 bid and ≥ 5 ask levels, and `current_price` consistent with the last M15 close (REQ-002, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-012, REQ-013, REQ-014, NFR-003, NFR-004)

- [x] Author `resources/market_data/eth_usdt.json` with `symbol: "ETH/USDT"`, realistic ETH price magnitude, ≥ 30 contiguous M15 candles, ≥ 5 bid and ≥ 5 ask levels, and `current_price` consistent with the last M15 close (REQ-003, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-012, REQ-013, REQ-014, NFR-003, NFR-004)

- [x] Validate both JSON files are well-formed UTF-8 and all Decimal domain fields use JSON strings (REQ-011, NFR-002)

- [x] Add conformance tests (recommended path: `resources/tests/test_market_data_fixtures.py`) that load each fixture, map JSON to `MarketData` via the documented contract, and assert: file existence, field presence, M15 candle count ≥ 30, order book depth ≥ 5 per side, `current_price` equals last M15 close, bid/ask price ordering, and OHLC invariants (REQ-004 through REQ-014, AC-004 through AC-007)

- [x] Confirm no provider, loader, or domain module code was added; only `resources/market_data/` artifacts and conformance tests (REQ-016, NFR-001, AC-009)

- [x] Run conformance tests and fix any fixture or documentation gaps until all acceptance criteria pass (AC-001 through AC-009)
