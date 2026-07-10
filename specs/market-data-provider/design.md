# Design

## Overview

Add an application-layer `MarketDataProvider` Protocol, a shared infrastructure JSON deserializer, and a `MockMarketDataProvider` adapter that reads static fixtures from `resources/market_data/`. A thin application use case (`GetMarketData`) demonstrates constructor injection of the port. Domain modules are unchanged; they receive `MarketData` as input from orchestration code, never from infrastructure directly.

## Architecture

### Layer responsibilities

| Layer | Path | Responsibility in this feature |
|-------|------|--------------------------------|
| Domain | `src/modules/analysis/models/` | Defines `MarketData` and related types; **no changes**, no retrieval concerns |
| Application | `src/application/contracts/`, `src/application/use_cases/` | Port definition and use case that depends on the port only |
| Infrastructure | `src/infrastructure/market_data/` | Mock adapter, symbol resolution, JSON deserialization |
| Resources | `resources/market_data/` | Static JSON fixtures (unchanged from feature 2) |

### New components

```
src/
├── application/
│   ├── contracts/
│   │   ├── __init__.py
│   │   └── market_data_provider.py      # MarketDataProvider Protocol
│   ├── use_cases/
│   │   ├── __init__.py
│   │   └── get_market_data.py           # GetMarketData use case
│   └── tests/
│       └── test_get_market_data.py
├── infrastructure/
│   └── market_data/
│       ├── __init__.py
│       ├── errors.py                    # MarketDataNotFoundError, MarketDataDeserializationError
│       ├── symbol_resolver.py           # symbol → filename mapping
│       ├── deserializer.py              # JSON dict → MarketData (shared)
│       └── mock_provider.py             # MockMarketDataProvider adapter
│   └── tests/
│       ├── test_symbol_resolver.py
│       ├── test_deserializer.py
│       └── test_mock_provider.py
resources/
├── market_data/                         # existing fixtures — no content changes
│   ├── README.md
│   ├── btc_usdt.json
│   └── eth_usdt.json
└── tests/
    └── test_market_data_fixtures.py     # refactored to import shared deserializer
```

### Placement rationale

| Decision | Rationale | Requirements |
|----------|-----------|--------------|
| Port in `src/application/contracts/` | Retrieval is an application orchestration concern, not domain logic; keeps analysis/classification modules free of I/O contracts | REQ-001, NFR-001, NFR-004 |
| Adapter in `src/infrastructure/market_data/` | File I/O and JSON parsing are infrastructure responsibilities | REQ-003, REQ-005, NFR-003 |
| Deserializer shared module | Eliminates duplicate mapping in `resources/tests/`; single source of truth aligned with README | REQ-006, REQ-014 |
| Use case in `src/application/use_cases/` | Proves application depends on port abstraction only; minimal scope for feature 4 pipeline | REQ-009, NFR-004 |

### Out of scope (deferred)

- REST API endpoints for market data (feature 5)
- Live exchange API adapters
- Full analysis-to-classification pipeline wiring (feature 4)
- Modifying fixture JSON files (feature 2)

## Data Flow

### Mock provider retrieval

```
Application use case (GetMarketData)
        │
        │  calls port: get_market_data("BTC/USDT")
        ▼
MarketDataProvider port (Protocol)
        │
        │  implemented by
        ▼
MockMarketDataProvider (infrastructure)
        │
        ├─► symbol_resolver: "BTC/USDT" → "btc_usdt.json"
        │
        ├─► pathlib read: resources/market_data/btc_usdt.json
        │
        ├─► json.loads (UTF-8)
        │
        └─► deserializer.market_data_from_dict(payload)
                │
                ▼
            MarketData (domain instance)
                │
                ▼
        returned to use case / caller
```

### Substitution (open/closed)

```
GetMarketData(provider: MarketDataProvider)
        │
        ├── MockMarketDataProvider        (this feature — JSON files)
        ├── FakeProvider (tests)          (in-memory stub)
        └── FutureExchangeProvider        (feature N — HTTP API)
```

Application and domain code remain unchanged when swapping adapters.

## Interfaces

### `MarketDataProvider` port

**Location:** `src/application/contracts/market_data_provider.py`

```python
from typing import Protocol

from market_data_be.modules.analysis.models.market import MarketData


class MarketDataProvider(Protocol):
    def get_market_data(self, symbol: str) -> MarketData:
        """Retrieve market data for the given trading pair symbol."""
        ...
```

| Attribute | Value |
|-----------|-------|
| Method | `get_market_data` |
| Input `symbol` | `str` — slash-separated pair (e.g., `BTC/USDT`) |
| Return | `MarketData` |
| Errors | Implementations may raise domain-specific infrastructure errors; port does not mandate a shared exception base |

### `GetMarketData` use case

**Location:** `src/application/use_cases/get_market_data.py`

```python
class GetMarketData:
    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider

    def execute(self, symbol: str) -> MarketData:
        return self._provider.get_market_data(symbol)
```

| Attribute | Value |
|-----------|-------|
| Constructor dependency | `MarketDataProvider` (port only) |
| Method | `execute(symbol: str) -> MarketData` |
| Infrastructure imports | **None** |

### Symbol resolver

**Location:** `src/infrastructure/market_data/symbol_resolver.py`

```python
def symbol_to_fixture_filename(symbol: str) -> str:
    """Map 'BTC/USDT' → 'btc_usdt.json'. Raises ValueError for invalid format."""
    ...
```

| Input | Output | Validation |
|-------|--------|------------|
| `BTC/USDT` | `btc_usdt.json` | Exactly one `/` separator; non-empty base and quote |
| `ETH/USDT` | `eth_usdt.json` | Same rules |
| `btc/usdt` | `btc_usdt.json` | Case-insensitive base/quote segments |
| `BTC-USDT` | — | `ValueError` (invalid format) |
| `BTC` | — | `ValueError` (missing quote) |

### Shared deserializer

**Location:** `src/infrastructure/market_data/deserializer.py`

Public function:

```python
def market_data_from_dict(data: Mapping[str, object]) -> MarketData:
    ...
```

Internal helpers (module-private, not re-exported as public API unless needed by tests):

- `candle_from_dict`
- `parse_datetime` — ISO 8601 UTC (`Z` or `+00:00`)
- `parse_optional_decimal` — `str | None` → `Decimal | None`

Mapping rules follow `resources/market_data/README.md` exactly:

| JSON field | Domain type | Rule |
|------------|-------------|------|
| `symbol` | `str` | Direct |
| `current_price` | `Decimal` | `Decimal(str(value))` |
| `order_book.bids` / `asks` | `tuple[OrderLevel, ...]` | Each level: string `price`, string `quantity` |
| `series[].timeframe` | `Timeframe` | `Timeframe(str(value))` |
| `series[].candles[]` | `Candle` | All required candle fields per README |
| Optional candle fields | `Decimal \| None`, `int \| None` | `null` or typed JSON value per README |

### `MockMarketDataProvider` adapter

**Location:** `src/infrastructure/market_data/mock_provider.py`

```python
class MockMarketDataProvider:
    def __init__(
        self,
        fixtures_dir: Path | None = None,
    ) -> None:
        ...

    def get_market_data(self, symbol: str) -> MarketData:
        ...
```

| Attribute | Value |
|-----------|-------|
| Default `fixtures_dir` | `{PROJECT_ROOT}/resources/market_data` resolved relative to project root (use `Path` traversal from a known anchor, e.g., module location or explicit constructor default documented in tests) |
| Implements | `MarketDataProvider` (structural subtyping) |
| File encoding | UTF-8 |
| JSON parser | stdlib `json` |

### Error types

**Location:** `src/infrastructure/market_data/errors.py`

| Exception | When raised | Carries |
|-----------|-------------|---------|
| `MarketDataNotFoundError` | Symbol cannot be mapped; fixture file does not exist | `symbol: str`, optional `path: Path` |
| `MarketDataDeserializationError` | JSON parse failure; missing/invalid fields; invalid `Timeframe` | `symbol: str`, `cause: Exception` (chained) |

Both inherit from `Exception`. They are infrastructure concerns; the application use case does not catch them in this feature (callers propagate).

## Data Model

No new domain entities. This feature operates on the existing `MarketData` graph:

```
MarketData
├── symbol: str
├── current_price: Decimal
├── order_book: OrderBook
└── series: tuple[CandleSeries, ...]
```

Fixture-to-domain mapping is identical to feature 2; the deserializer is the authoritative runtime implementation of the README contract.

## Error Handling

| Scenario | Component | Behavior |
|----------|-----------|----------|
| Invalid symbol format (no `/`, empty segment) | `symbol_resolver` | Raise `ValueError` before file lookup |
| Fixture file not found | `MockMarketDataProvider` | Raise `MarketDataNotFoundError` with symbol and attempted path |
| Unsupported symbol with valid format but no file | `MockMarketDataProvider` | Raise `MarketDataNotFoundError` |
| Invalid JSON syntax | `MockMarketDataProvider` | Raise `MarketDataDeserializationError` chaining `json.JSONDecodeError` |
| Missing required JSON field | `deserializer` | Raise `KeyError` or `MarketDataDeserializationError` (implementer wraps in provider) |
| Invalid `timeframe` enum value | `deserializer` | Raise `MarketDataDeserializationError` chaining `ValueError` from `Timeframe(...)` |
| Successful retrieval | `MockMarketDataProvider` | Return `MarketData` with `symbol` matching request |

Recovery: no automatic retry or fallback symbols in this feature.

## Testing Strategy

| Test type | Location | Scope |
|-----------|----------|-------|
| Symbol resolver unit tests | `src/infrastructure/tests/test_symbol_resolver.py` | Valid mappings (`BTC/USDT`, `ETH/USDT`); invalid formats |
| Deserializer unit tests | `src/infrastructure/tests/test_deserializer.py` | Load fixture JSON via `json.loads`; assert `MarketData` types; optional minimal invalid-payload case |
| Mock provider unit tests | `src/infrastructure/tests/test_mock_provider.py` | Integration against real fixtures; not-found path (missing file / bad symbol); deserialization error path (temp malformed JSON) |
| Use case unit tests | `src/application/tests/test_get_market_data.py` | Fake `MarketDataProvider` stub returns known `MarketData`; verifies delegation without infrastructure imports |
| Fixture conformance (regression) | `resources/tests/test_market_data_fixtures.py` | Refactored to import `market_data_from_dict` from infrastructure; all existing assertions remain |

**Coverage expectations:**

- Happy path for both `BTC/USDT` and `ETH/USDT` through `MockMarketDataProvider`.
- Error paths for not-found and deserialization failure.
- Use case substitution test with a test double proves NFR-004 / AC-007.
- Domain import guard: no new imports of `infrastructure` or `application.contracts` under `src/modules/`.
- Deserializer logic exists in exactly one production module (`deserializer.py`).

**Test doubles:**

```python
class FakeMarketDataProvider:
    def __init__(self, data: MarketData) -> None:
        self._data = data

    def get_market_data(self, symbol: str) -> MarketData:
        return self._data
```

Used only in application tests to demonstrate port substitution.

## Package configuration

Update `pyproject.toml` `[tool.setuptools]` packages list to include new paths:

- `market_data_be.application.contracts`
- `market_data_be.application.use_cases`
- `market_data_be.application.tests`
- `market_data_be.infrastructure.market_data`
- Additional `market_data_be.infrastructure.tests` entries if not already covered

Add `[tool.setuptools.package-dir]` mappings if needed (follow existing pattern for `market_data_be.infrastructure`).

Consider adding `resources/tests` to pytest `testpaths` or document running `pytest resources/tests` alongside `src` tests so fixture conformance continues to execute after refactor.

## Requirement Traceability

| Requirement | Design decision |
|-------------|-----------------|
| REQ-001 | `MarketDataProvider` Protocol in `src/application/contracts/market_data_provider.py` |
| REQ-002 | Single `get_market_data(symbol: str) -> MarketData` method on port |
| REQ-003 | `MockMarketDataProvider` class in `src/infrastructure/market_data/mock_provider.py` |
| REQ-004 | `symbol_to_fixture_filename` in `symbol_resolver.py` per README convention |
| REQ-005 | `Path.read_text(encoding="utf-8")` + `json.loads` in mock provider |
| REQ-006 | `market_data_from_dict` in `deserializer.py` |
| REQ-007 | Full nested mapping for `MarketData`, `OrderBook`, `CandleSeries`, `Candle`, `Timeframe` |
| REQ-008 | Mock provider calls shared deserializer after JSON load |
| REQ-009 | `GetMarketData` use case with constructor-injected port |
| REQ-010 | Mock provider test asserts `BTC/USDT` retrieval |
| REQ-011 | Mock provider test asserts `ETH/USDT` retrieval |
| REQ-012 | `MarketDataNotFoundError` for unresolvable/missing symbols |
| REQ-013 | `MarketDataDeserializationError` for invalid JSON payloads |
| REQ-014 | Refactor `resources/tests/test_market_data_fixtures.py` to import infrastructure deserializer |
| NFR-001 | Port in application; no provider imports in `src/modules/` |
| NFR-002 | Strict types on Protocol and public deserializer function |
| NFR-003 | Stdlib-only deserialization; domain models imported for construction |
| NFR-004 | Adapter swap via injection; fake provider in application tests |
| NFR-005 | Tests under `src/infrastructure/tests/` and `src/application/tests/` |
| NFR-006 | Names: `MarketDataProvider`, `MockMarketDataProvider`, `GetMarketData`, `symbol_to_fixture_filename` |
