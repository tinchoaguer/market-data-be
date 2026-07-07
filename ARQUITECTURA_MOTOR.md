# Arquitectura del motor de análisis

Análisis arquitectónico del núcleo en `src/engine/`, restringido al motor actual (sin API, persistencia, IA ni exchanges).

**Estado:** post Etapa 2 — assessments, fachada, dataclasses frozen, 43 tests, `dependencies = []`.

---

## 1. Visión general

El motor implementa un **pipeline determinístico de interpretación**:

```
┌─────────────────────────────────────────────────────────────┐
│                  MarketAnalysisEngine                        │
│                      (facade)                                │
└──────────────────────────┬──────────────────────────────────┘
                           │
     ┌─────────────────────┼─────────────────────┐
     ▼                     ▼                     ▼
┌─────────┐         ┌─────────────┐       ┌──────────────┐
│ INPUTS  │         │  ANALYZERS  │       │  SYNTHESIS   │
│ models/ │────────▶│ analyzers/  │──────▶│ synthesis/   │
│ market  │         │  (5 módulos)│       │ catalog_     │
│portfolio│         └─────────────┘       │ builder      │
└─────────┘                               └──────┬───────┘
                                                   ▼
                                          ┌──────────────┐
                                          │   OUTPUT     │
                                          │ AnalysisResult│
                                          └──────────────┘
```

**Principio rector:** el motor **solo produce conocimiento** (`AnalysisResult`). No tiene efectos secundarios, I/O ni estado de sesión.

---

## 2. Estructura de carpetas

```
src/engine/
├── market_analysis_engine.py   # Facade — único punto de entrada público
├── models/
│   ├── __init__.py             # Re-exports
│   ├── enums.py                # MarketRegime, StrategyType, Timeframe
│   ├── market.py               # Candle, OrderBook, CandleSeries, MarketData
│   ├── portfolio.py            # PortfolioState, PortfolioConstraints
│   ├── assessments.py          # *Assessment, ExposureProfile
│   ├── strategy_catalog.py     # CatalogResult
│   └── analysis_result.py      # AnalysisResult
├── analyzers/
│   ├── candle_metrics.py       # Funciones puras (shared kernel)
│   ├── regime_detector.py
│   ├── risk_engine.py
│   ├── economic_filter.py
│   └── portfolio_manager.py
└── synthesis/
    └── catalog_builder.py
```

**Tests:** `src/engine/tests/` — un archivo por analyzer + facade + fixtures compartidos.

---

## 3. Flujo de dependencias

```
enums
  ↓
market, portfolio          ← tipos de ENTRADA
  ↓
assessments                ← tipos de SALIDA parcial
  ↓
strategy_catalog           ← salida de síntesis
  ↓
analysis_result

analyzers/*  → assessments, market, enums
candle_metrics → market (sin assessments)

synthesis/catalog_builder → assessments, strategy_catalog, enums

market_analysis_engine → analyzers + synthesis + models
```

**Regla respetada:** `models` no importa `analyzers` ni `synthesis`. La dependencia va hacia abajo en abstracción, no hacia la lógica.

---

## 4. Contratos por componente

| Componente | Entrada | Salida | Estado |
|---|---|---|---|---|
| `RegimeDetector` | `MarketData` | `RegimeAssessment` | Stateless |
| `RiskEngine` | `MarketData`, `RegimeAssessment` | `RiskAssessment` | Stateless |
| `EconomicFilter` | `MarketData` | `EconomicAssessment` | Stateless |
| `PortfolioManager` | `MarketData`, `PortfolioState`, `PortfolioConstraints?` | `ExposureProfile` | Stateless |
| `CatalogBuilder` | 4 assessments | `CatalogResult` | Stateless |
| `MarketAnalysisEngine` | `MarketData`, `PortfolioState?` | `AnalysisResult` | Stateless (DI en `__init__`) |

**Atajos legacy:** `detect()` y `score()` delegan a `assess()` — compatibilidad para tests o código antiguo.

---

## 5. Modelado de datos

### 5.1 Decisiones tomadas

| Decisión | Razón |
|---|---|
| `@dataclass(frozen=True, slots=True)` | Inmutabilidad, sin Pydantic en el core |
| `tuple` para colecciones en salidas | Inmutabilidad profunda razonable |
| `Decimal` en inputs (`Candle`, precio) | Precisión en datos de mercado |
| `float` en scores y components | Analítica interna |
| `CandleSeries` + `MarketData.series` | Multi-TF preparado; M15 vía `.candles` |
| `PortfolioState` como input externo | Separa análisis de bookkeeping de aplicación |

### 5.2 Tipos de rol

| Rol | Archivos |
|---|---|
| Vocabulario | `enums.py` |
| Observables | `market.py` |
| Contexto externo | `portfolio.py` |
| Conocimiento parcial | `assessments.py` |
| Conocimiento agregado estratégico | `strategy_catalog.py` |
| Snapshot completo | `analysis_result.py` |

---

## 6. Evaluación SOLID (solo motor)

### S — Single Responsibility

| Módulo | Responsabilidad | Veredicto |
|---|---|---|
| `candle_metrics` | Cálculos OHLC/libro | ✓ |
| Cada analyzer | Una dimensión analítica | ✓ |
| `CatalogBuilder` | Síntesis estrategia | ✓ (pero acumula reglas) |
| `MarketAnalysisEngine` | Orquestar pipeline | ✓ |

### O — Open/Closed

| Área | Veredicto |
|---|---|
| Analyzers | Cerrados; extender = nuevo analyzer + wire en facade |
| `CatalogBuilder` | **Violación documentada** — reglas inline; extender = editar archivo |
| `MarketAnalysisEngine` | Abierto vía DI (`__init__` con implementaciones opcionales) |

### L — Liskov

No hay jerarquías de herencia. Los Protocols no están formalizados aún — sustituibilidad se logra por DI manual de clases concretas.

### I — Interface Segregation

No hay interfaces explícitas. Cada analyzer expone 1–2 métodos públicos — acoplamiento bajo en la práctica.

### D — Dependency Inversion

Parcial:

- ✓ Facade depende de abstracciones *de facto* (inyecta analyzers)
- ✗ No hay `Protocol` para analyzers; tipos concretos en `MarketAnalysisEngine`
- ✓ `PortfolioState` invertido — la app provee estado, el motor no lo posee

---

## 7. Fortalezas arquitectónicas

1. **Portabilidad:** stdlib only — integrable en cualquier runtime.
2. **Testabilidad:** analyzers aislados + fixtures; 43 tests rápidos.
3. **Trazabilidad:** `reasons` y `components` en assessments — conocimiento no se pierde en logs.
4. **Frontera clara:** sin structlog, sin HTTP, sin DB en el core.
5. **Separación entrada/salida:** `market.py` vs `assessments.py` vs `strategy_catalog.py`.
6. **Shared kernel:** `candle_metrics` evita duplicar ADX/ATR/volumen.
7. **Composición en facade:** pipeline legible en ~15 líneas.

---

## 8. Deuda técnica y tensiones

### 8.1 Alta prioridad (cuando crezca el negocio)

| Tema | Detalle |
|---|---|
| `CatalogBuilder` monolítico | OCP violado a propósito; refactor si &gt;5 estrategias o gates configurables |
| Multi-TF no operativo | `Timeframe` y `CandleSeries` sin consumidores H1/H4/D1 |
| `insufficient_data` inconsistente | Regime/portfolio lo setean; catálogo no lo usa como gate |
| Enums muertos | `NEWS_TRADING` sin regla |

### 8.2 Media prioridad

| Tema | Detalle |
|---|---|
| Sin `Protocol` formal | Dificulta mocks tipados y plugins de analyzers |
| Umbrales dispersos | Constantes en cada analyzer; sin módulo `config` o `thresholds` |
| `candle_metrics` acepta `dict` en libro | Compat legacy; rompe pureza del tipo `OrderBook` |
| Sin `__init__.py` en `analyzers/` y `synthesis/` | Imports absolutos largos; no es bug pero incompleto como paquete |
| `preferred_strategy` implícito | Primera en lista — política no nombrada |

### 8.3 Baja prioridad

| Tema | Detalle |
|---|---|
| Atajos `detect()` / `score()` | Podrían deprecarse cuando no haya consumidores legacy |
| `frozen_metrics` ordena keys | Determinismo útil; documentar si se serializa |

---

## 9. Límites arquitectónicos (intencionales)

```
┌────────────────────────────────────────┐
│           DENTRO DEL MOTOR           │
│  Interpretar MarketData + Portfolio  │
│  → AnalysisResult                    │
└────────────────────────────────────────┘
          ▲                    │
          │                    ▼
   [Mapper inbound]     [Mapper outbound]
   (futuro, Pydantic)   (app, API, IA)
          ▲                    │
┌─────────┴──────┐    ┌────────┴─────────┐
│ Binance, WS,   │    │ Decisiones, bots, │
│ DB, archivos   │    │ notificaciones    │
└────────────────┘    └───────────────────┘
     INFRAESTRUCTURA        APLICACIÓN
```

El motor **no debe** importar nada de esas capas. La integración es:

1. **Inbound:** adapter construye `MarketData` + `PortfolioState`
2. **Core:** `engine.analyze(...)`
3. **Outbound:** adapter lee `AnalysisResult` (JSON, prompt IA, reglas)

---

## 10. Pipeline detallado

```python
# market_analysis_engine.py (simplificado)
regime   = regime_detector.assess(market_data)
risk     = risk_engine.assess(market_data, regime)
economic = economic_filter.assess(market_data)
exposure = portfolio_manager.evaluate(market_data, state, constraints)
catalog  = catalog_builder.evaluate(regime, risk, economic, exposure)
```

**Orden fijo y con sentido causal:**

1. Régimen no depende de riesgo (riesgo sí depende de régimen)
2. Economía es independiente del régimen en código (podría mejorarse)
3. Exposición es independiente del régimen
4. Catálogo consume **solo assessments**, no `MarketData` — síntesis desacoplada de OHLC

**Mejora arquitectónica futura:** `CatalogContext` dataclass que agrupe los 4 assessments y evite firmas largas.

---

## 11. Estrategia de testing

| Capa | Enfoque |
|---|---|
| `candle_metrics` | Unit puro con velas sintéticas |
| Analyzers | Series construidas en test (flat, trend, spike, chaotic) |
| `CatalogBuilder` | Assessments sintéticos (sin mercado) |
| Facade | Smoke test end-to-end con fixtures |

**Hueco:** no hay tests de integración con datos reales grabados (golden files). Aceptable para etapa actual.

---

## 12. Comparación con arquitectura objetivo (plan Etapa 2)

| Objetivo plan | Estado |
|---|---|
| Assessments con evidencia | ✓ |
| `ExposureProfile` + `PortfolioState` | ✓ |
| `AnalysisResult` + facade | ✓ |
| Sin structlog en core | ✓ |
| `CatalogBuilder` rename | ✓ |
| `CandleSeries` multi-TF | ✓ modelo; ✗ lógica |
| Eliminar `ParameterBounds` | ✓ |
| OCP en catálogo | ✗ diferido (documentado) |

---

## 13. Recomendaciones arquitectónicas por etapa

### Al integrar con capa de aplicación

- Mantener **un solo** `MarketAnalysisEngine` por ciclo o inyectarlo vía DI
- Mappers Pydantic **fuera** de `engine/`
- No reintroducir estado mutable en `PortfolioManager`

### Al crecer el catálogo (Etapa E negocio)

- Extraer `catalog_gates.py` y `strategy_rules.py` sin cambiar `CatalogBuilder.evaluate()` signature
- O inyectar tuplas `(gate, rule)` como se discutió para OCP

### Al agregar analyzers

```
analyzers/
  sentiment_analyzer.py   → SentimentAssessment (nuevo en assessments.py)
```

Actualizar facade y `AnalysisResult` — cambio acotado y explícito.

### Si el motor se publica como librería

- Agregar `src/engine/__init__.py` exportando `MarketAnalysisEngine`, `AnalysisResult`, tipos de entrada
- Documentar versión semántica del contrato `AnalysisResult`

---

## 14. Resumen ejecutivo

El motor es un **monolito modular pequeño**: pipeline lineal, modelos inmutables, analyzers stateless y una capa de síntesis delgada.

**Arquitectónicamente está listo** para ser consumido por otra capa. Las principales mejoras **dentro del motor** son:

1. Formalizar contratos (`Protocol`, `CatalogContext`)
2. Activar multi-TF en analyzers
3. Refactor del catálogo solo cuando el set de reglas crezca
4. Paquete público (`engine/__init__.py`) al integrar

No hace falta reestructurar carpetas antes de pasar a la siguiente etapa del **proyecto** (marketdata, app, API). El núcleo cumple su frontera.
