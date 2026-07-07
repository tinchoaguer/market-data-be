# Análisis de negocio — Motor de análisis de mercado

Documento de cobertura analítica del núcleo en `src/engine/`.

**Alcance:** qué conocimiento produce el motor hoy, qué datos consume, qué dimensiones del mercado ignora, y etapas propuestas de enriquecimiento.  
**Fuera de alcance:** ejecución, APIs, persistencia, IA, integración con exchanges, orquestación de bots.

---

## 1. Propósito del motor

El motor responde una pregunta por símbolo:

> Dado el estado observable del mercado y el contexto de portafolio, **¿qué se puede saber** sobre régimen, riesgo, viabilidad económica, capacidad de exposición y estrategias coherentes?

No decide órdenes ni acciones. Devuelve un `AnalysisResult` — un snapshot de conocimiento analítico.

```
MarketData + PortfolioState
        │
        ▼
  MarketAnalysisEngine.analyze()
        │
        ▼
  AnalysisResult
    ├── regime      (RegimeAssessment)
    ├── risk        (RiskAssessment)
    ├── economic    (EconomicAssessment)
    ├── exposure    (ExposureProfile)
    └── catalog     (CatalogResult)
```

---

## 2. Datos de entrada que el motor entiende

### 2.1 `MarketData` (observación)

| Dato | Uso actual |
|---|---|
| `symbol` | Identificación en salidas |
| `current_price` | Liquidez nominal en portfolio; precio de referencia |
| `series[M15].candles` | **Única serie usada** por todos los analyzers |
| `order_book` (bids/asks) | Imbalance, spread, profundidad top-N |

Cada `Candle` aporta: OHLC, `base_volume`, `quote_volume`, `trade_count`, `buy_volume` (taker buy).

### 2.2 `PortfolioState` + `PortfolioConstraints` (contexto externo)

| Dato | Uso actual |
|---|---|
| `total_value` | Base para % y montos recomendados |
| `allocations` por símbolo | Exposición actual y headroom |
| Límites (`max_symbol_weight`, `max_portfolio_deployed`, etc.) | Tope de capacidad |

El motor **no** persiste ni muta el portafolio; solo lo interpreta.

### 2.3 Datos definidos pero no consumidos

| Dato / concepto | Estado |
|---|---|
| `Timeframe.H1`, `H4`, `D1` | Enum existe; ningún analyzer los lee |
| Series adicionales en `MarketData.series` | Estructura lista; solo M15 se usa |
| `StrategyType.NEWS_TRADING` | Enum existe; catálogo no lo asigna nunca |

---

## 3. Qué produce hoy (dimensión por dimensión)

### 3.1 Régimen de mercado (`RegimeDetector`)

**Pregunta:** ¿En qué estado estructural está el precio?

| Régimen | Señales que lo activan (resumen) |
|---|---|
| `NEWS_SPIKE` | Rango/cuerpo anormal vs ATR + pico de volumen o trades |
| `CHAOTIC` | Expansión de volatilidad, bajo ADX + ATR alto, whipsaw, muchos cambios de dirección |
| `TREND_UP` / `TREND_DOWN` | ADX fuerte, DI dominante, estructura HH/HL o LH/LL, precio vs SMA con pendiente, flujo taker |
| `RANGE` | ADX bajo y precio dentro de banda ATR alrededor de SMA |

**Evidencia:** `RegimeAssessment.reasons` (códigos como `adx_strong`, `relative_volume_spike`, etc.).

**Límite:** con &lt; 30 velas M15 devuelve `RANGE` con `insufficient_data=True` (conservador).

---

### 3.2 Riesgo (`RiskEngine`)

**Pregunta:** ¿Qué tan peligroso es operar en este contexto? (score 0–1)

| Componente | Peso | Fuente |
|---|---|---|
| Volatilidad de retornos log | 30% | `returns_volatility` M15 |
| Expansión ATR vs media histórica | 20% | ATR / ATR-SMA |
| Riesgo base por régimen | 30% | Tabla fija (ej. NEWS_SPIKE ≈ 0.95) |
| Estrés de liquidez | 20% | Imbalance del libro + volumen relativo alto |

**Pisos:** NEWS_SPIKE y CHAOTIC mantienen score mínimo aunque vol/libro parezcan calmados.

**Evidencia:** `RiskAssessment.components` (tupla nombre → valor).

---

### 3.3 Viabilidad económica (`EconomicFilter`)

**Pregunta:** ¿Hay “edge” económico para estrategias que harvestean rango/microestructura? (edge −1 a +1)

| Componente | Peso | Lógica |
|---|---|---|
| Microestructura | +25% | Imbalance del libro ponderado por volumen relativo |
| Calidad de actividad | +25% | Volumen relativo en zona “ideal” (ni thin ni spike) |
| Economía de rango | +30% | ATR% en sweet spot para harvesting |
| Arrastre de costos | −20% | Fees genéricos (taker+maker) + spread × fills estimados |

**Evidencia:** `EconomicAssessment.components`.

**Nota:** los fees son constantes de modelo, no datos reales del exchange del usuario.

---

### 3.4 Capacidad de exposición (`PortfolioManager`)

**Pregunta:** ¿Cuánto capital *podría* asignarse a este símbolo sin violar límites?

Combina:

- Headroom por símbolo (`max_symbol_weight`)
- Headroom de portafolio (`max_portfolio_deployed`)
- Presupuesto ajustado por volatilidad (menos vol → más % permitido)
- Tope por liquidez del libro (profundidad × precio × fracción)

**Evidencia:** `ExposureProfile` con `components.vol_budget_pct` y `liquidity_cap_value`.

**No considera:** PnL, drawdown, correlación entre símbolos, exposición por estrategia, margen/funding.

---

### 3.5 Catálogo de estrategias (`CatalogBuilder`)

**Pregunta:** Dado todo lo anterior, ¿qué *tipos* de estrategia son analíticamente coherentes?

**Hard gates (bloquean todo):**

| Gate | Condición |
|---|---|
| Régimen extremo | `NEWS_SPIKE` o `CHAOTIC` |
| Riesgo alto | `risk.score ≥ 0.75` |
| Edge negativo | `economic.edge < 0` |
| Sin capacidad | `recommended_allocation_value ≤ 1` |

**Estrategias evaluadas hoy:**

| Régimen | Estrategias posibles |
|---|---|
| `RANGE` | `RANGE_BOUNDING`; `PING_PONG` si riesgo bajo y edge ≥ 0.25 |
| `TREND_UP` / `TREND_DOWN` | `TREND_FOLLOWING` si riesgo moderado y edge &gt; 0 |
| Otros / gates | Ninguna → `preferred_strategy = OTHER` |

**Salida:** `allowed_strategies`, `forbidden_strategies`, `preferred_strategy`, `catalog_reason`, `hard_gate_reason`.

**No produce:** parámetros operativos, dirección long/short, sizing final, timing de entrada.

---

## 4. Mapa de cobertura analítica

```
                    CONTEMPLADO HOY          NO CONTEMPLADO
                    ───────────────          ───────────────
Precio / OHLC       ✓ M15                    Multi-TF, niveles S/R
Volatilidad         ✓ ATR, retornos          Vol implícita, term structure
Tendencia           ✓ ADX, SMA, estructura     RSI, MACD, ichimoku…
Microestructura     ✓ Libro L1–N             Flujo de trades, walls
Participación       ✓ Vol/trades relativos   OI, liquidaciones
Costos              ✓ Spread + fees fijos    Fee tier real, funding, slippage modelo
Derivados           ✗                        Funding, basis, OI
Portafolio          ✓ Alloc + límites %      Correlación, DD, beta BTC
Estrategias         ✓ 3 tipos + gates        NEWS_TRADING, scores por estrategia
Confianza           ✓ reasons (parcial)      Score de confianza unificado
Temporalidad        ✓ Una snapshot           Persistencia régimen, transiciones
Cross-asset         ✗                        Dominancia BTC, pares relacionados
Eventos             ✓ NEWS_SPIKE heurístico  Calendario, noticias reales
```

---

## 5. Huecos importantes (qué el análisis deja afuera)

### 5.1 Datos de mercado no modelados en `MarketData`

El motor no puede analizar lo que no entra en la entrada:

- Funding rate, open interest, long/short ratio
- Basis spot–futuros, premium de perp
- Volatilidad implícita
- Trades tick-by-tick o aggTrades (solo agregados en vela)
- Profundidad del libro más allá del snapshot actual (sin historial)
- Datos de otros símbolos (BTC como líder, ETH/BTC, etc.)

### 5.2 Dimensiones analíticas ausentes

| Dimensión | Por qué importa |
|---|---|
| **Multi-timeframe** | Tendencia en H4 vs rango en M15 es información clave |
| **Funding / carry** | Afecta viabilidad de hold y edge neto en perps |
| **Correlación de portafolio** | Exposición real ≠ suma de allocations independientes |
| **Drawdown / heat** | Capacidad debería reducirse tras pérdidas, no solo por % |
| **Confianza calibrada** | `insufficient_data` no corta el catálogo hoy |
| **Transición de régimen** | Saber si RANGE→TREND es incipiente vs estable |
| **Suitability por estrategia** | Hoy es binario (allowed/forbidden), no ranking fino |
| **Direccionalidad** | TREND_UP no implica long-only suitability explícita |
| **Sesión / liquidez horaria** | Asia vs US en cripto aún tiene patrones |

### 5.3 Simplificaciones de modelo (conscientes)

- Fees y fills estimados genéricos en `EconomicFilter`
- Umbrales fijos (0.75 riesgo, 0.25 edge ping-pong, etc.) sin calibración por activo
- `PortfolioState` solo por notional, sin margen ni apalancamiento
- Catálogo monolítico (OCP violado a propósito; ver `catalog_builder.py`)
- `preferred_strategy` = primera en lista, sin política de preferencia explícita

---

## 6. Etapas de mejora propuestas

### Etapa A — Completada (estado actual)

- Pipeline determinístico con assessments y evidencia
- Régimen multi-señal (5 regímenes)
- Riesgo multi-factor con pisos por régimen extremo
- Edge económico microestructura + rango + costos proxy
- Capacidad de portafolio pura (entrada externa)
- Catálogo de estrategias sin parámetros operativos
- Fachada `MarketAnalysisEngine`, 43 tests, cero dependencias externas

---

### Etapa B — Enriquecer entradas y coherencia interna

**Objetivo:** usar mejor lo que ya está modelado y cerrar inconsistencias.

| Mejora | Impacto |
|---|---|
| Propagar `insufficient_data` a gates del catálogo | Evita estrategias con datos pobres |
| Activar multi-timeframe (H1/H4 en `series`) | Régimen y riesgo con confluencia |
| Agregar `funding_rate` (y opcional `open_interest`) a `MarketData` | Edge y riesgo en perps |
| Score de confianza por assessment (0–1) | Priorizar señales débiles vs fuertes |
| Calibración de umbrales por `symbol` vía `PortfolioConstraints` extendido | BTC ≠ alt de baja cap |

**Entregable de negocio:** análisis más robusto sin nuevas capas fuera del motor.

---

### Etapa C — Profundizar dimensiones existentes

**Objetivo:** mejorar la calidad de régimen, riesgo y economía.

| Mejora | Analyzer afectado |
|---|---|
| Persistencia / edad del régimen (velas en mismo régimen) | `RegimeDetector` o nuevo `RegimeDynamics` |
| Probabilidad de transición (RANGE→TREND) | Síntesis o analyzer dedicado |
| Funding en edge neto (carry favorable/desfavorable) | `EconomicFilter` |
| Slippage estimado por profundidad y tamaño hipotético | `EconomicFilter` |
| Riesgo de cola (gaps, spikes recientes) | `RiskEngine` |
| `NEWS_TRADING` en catálogo cuando `NEWS_SPIKE` + condiciones | `CatalogBuilder` |

**Entregable de negocio:** conocimiento más granular para capas superiores (IA, reglas, ejecución).

---

### Etapa D — Portafolio y contexto multi-activo

**Objetivo:** exposición analítica más realista.

| Mejora | Descripción |
|---|---|
| `PortfolioState` con drawdown / heat | Reducir capacidad tras racha perdedora |
| Matriz de correlación simplificada (input externo) | Penalizar allocations correlacionadas |
| Exposición neta direccional por subtipo | Long-bias vs market-neutral |
| Límites por bucket (majors vs alts) | Constraints por clase de activo |

**Entregable de negocio:** `ExposureProfile` refleja riesgo de cartera, no solo de símbolo.

---

### Etapa E — Síntesis avanzada

**Objetivo:** catálogo y resultado más ricos sin volver a parámetros de bot.

| Mejora | Descripción |
|---|---|
| `StrategySuitability` (score 0–1 por estrategia) | Más allá de allowed/forbidden |
| `AnalysisSummary` en lenguaje estructurado | Texto + facts para IA downstream |
| Detección de cambio de catálogo vs ciclo anterior | Input: `CatalogResult` previo |
| Alertas analíticas (`RegimeShift`, `LiquidityStress`) | Eventos tipados en resultado |

**Entregable de negocio:** el motor produce *conocimiento accionable* para capas de decisión, no decisiones.

---

### Etapa F — Validación y calibración (meta-análisis)

**Objetivo:** confiar en los números.

| Mejora | Descripción |
|---|---|
| Backtesting offline de assessments vs histórico | Fuera del motor en runtime, pero alimenta umbrales |
| Métricas de hit-rate por régimen | Calibrar ADX/ATR thresholds |
| Sensibilidad de umbrales documentada | Qué pasa si `HIGH_RISK_GATE` es 0.65 vs 0.75 |

---

## 7. Límites explícitos del motor (no son “etapas futuras” del core)

Estas responsabilidades **pertenecen a otras capas**, no al núcleo de análisis:

| Responsabilidad | Capa futura |
|---|---|
| Fetch de velas/libro desde Binance | Infraestructura / marketdata |
| Persistir `AnalysisResult` | Persistence |
| Decidir CREATE/PAUSE/CLOSE | Application / IA |
| Traducir estrategia a órdenes | Execution / mappers |
| Scheduler y multi-símbolo en producción | Application |
| Validación JSON de IA | Application |

---

## 8. Resumen ejecutivo

Hoy el motor produce un **perfil analítico completo pero acotado**: régimen técnico en M15, riesgo compuesto, edge económico proxy, capacidad de portafolio simplificada y catálogo coarse de tres estrategias.

Lo que **más valor aportaría** en próximas etapas dentro del motor:

1. Multi-timeframe y funding (datos + lógica)
2. Confianza y gates coherentes con calidad de datos
3. Portafolio con correlación y drawdown
4. Suitability fina por estrategia (sin volver a parámetros de bot)

El motor está **listo para integrarse** con capas externas; las etapas B–E lo hacen **más preciso**, no más “ejecutivo”.
