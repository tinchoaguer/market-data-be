# Arquitectura por dominios

Documento de **enfoque arquitectónico** del sistema de inteligencia de trading. Define los dominios de conocimiento, cómo se materializan hoy en el código, y la evolución prevista hacia motores especializados.

**Complementa:** [`ARQUITECTURA_MOTOR.md`](ARQUITECTURA_MOTOR.md) (estructura técnica del núcleo actual) y [`ANALISIS_NEGOCIO_MOTOR.md`](ANALISIS_NEGOCIO_MOTOR.md) (cobertura analítica y gaps de negocio).

**Alcance:** dominios de interpretación y decisión. Fuera de alcance: I/O, persistencia, APIs, ejecución de órdenes, IA generativa.

---

## 1. Dominios de conocimiento

El sistema se organiza en cuatro dominios. Cada uno responde una pregunta distinta y produce un tipo de conocimiento que los dominios posteriores consumen.

| Dominio | Pregunta principal | Conocimiento que produce |
|---|---|---|
| **Market Analysis** | ¿Qué está pasando en el mercado? | Régimen, volatilidad, liquidez, microestructura observable |
| **Prediction** | ¿Qué podría pasar en el futuro? | Escenarios, probabilidades, horizontes, señales prospectivas |
| **Portfolio Intelligence** | ¿Qué capacidad y restricciones tiene la cartera? | Exposición, headroom, límites, concentración, riesgo agregado |
| **Decision Support** | ¿Qué acciones son coherentes dadas las condiciones actuales? | Estrategias permitidas/prohibidas, gates duros, preferencias |

### 1.1 Market Analysis

Interpreta el **estado observable** del mercado a partir de datos históricos y en tiempo real (velas, order book, precio).

- No predice el futuro; describe el presente con evidencia.
- Salidas típicas: régimen (`TREND_UP`, `RANGE`, `CHAOTIC`…), métricas de volatilidad, spread, imbalance, calidad de datos.
- Depende solo de `MarketData` (y utilidades puras sobre velas).

### 1.2 Prediction

Proyecta **escenarios futuros** a partir del análisis de mercado (y eventualmente de señales externas).

- Hoy **no existe** como motor independiente.
- Salidas esperadas: distribuciones de precio, probabilidad de ruptura, ventanas temporales, confianza del escenario.
- Depende de Market Analysis; no debería re-leer datos crudos sin pasar por él.

### 1.3 Portfolio Intelligence

Evalúa la **capacidad operativa** de la cartera: cuánto puede asumir, dónde está expuesto, qué límites aplican.

- Separa el estado del activo (`PortfolioState`) de las reglas de negocio (`PortfolioConstraints`).
- Salidas típicas: exposición por símbolo, headroom, % desplegado, flags de límite alcanzado.
- Hoy mezcla evaluación de exposición con señales de mercado (riesgo, economía) en el mismo pipeline; en la evolución futura concentra solo la lógica de cartera.

### 1.4 Decision Support

Sintetiza los dominios anteriores en **recomendaciones accionables** sin ejecutarlas.

- Traduce conocimiento en conjuntos de estrategias coherentes o vetadas.
- Aplica gates duros (datos insuficientes, riesgo extremo, sin capacidad).
- Hoy materializado como `CatalogBuilder`; en el futuro como `DecisionEngine` con reglas más ricas y posible intervención humana o IA downstream.

---

## 2. Estado actual — pipeline unificado

Hoy el sistema concentra responsabilidades de **tres dominios** (Market Analysis, Portfolio Intelligence parcial, Decision Support) en un único pipeline orquestado por `MarketAnalysisEngine`.

```
MarketData ──┐
             │
PortfolioState ──► MarketAnalysisEngine.analyze() ──► AnalysisResult
             │
PortfolioConstraints ──┘
```

### 2.1 Qué hace el pipeline hoy

```
MarketData + PortfolioState (+ constraints)
        │
        ▼
┌───────────────────────────────────────────────────┐
│           MarketAnalysisEngine (facade)            │
├───────────────────────────────────────────────────┤
│  RegimeDetector      → régimen de mercado          │  Market Analysis
│  RiskEngine          → score de riesgo             │  (parcialmente)
│  EconomicFilter      → viabilidad económica        │  Market Analysis
│  PortfolioManager    → exposición y headroom       │  Portfolio Intelligence
│  CatalogBuilder      → estrategias coherentes      │  Decision Support
└───────────────────────────────────────────────────┘
        │
        ▼
   AnalysisResult
     ├── regime
     ├── risk
     ├── economic
     ├── exposure
     └── catalog
```

### 2.2 Mapeo dominio → componente actual

| Dominio | Componente(s) en código | Madurez |
|---|---|---|
| Market Analysis | `RegimeDetector`, `EconomicFilter`, `candle_metrics` | Activo — núcleo del motor |
| Market Analysis (riesgo) | `RiskEngine` | Activo — hoy cruza análisis de mercado con evaluación de condiciones adversas |
| Prediction | — | **No implementado** |
| Portfolio Intelligence | `PortfolioManager`, `PortfolioState`, `PortfolioConstraints` | Parcial — evalúa exposición pero vive dentro del pipeline de análisis |
| Decision Support | `CatalogBuilder`, `CatalogResult` | Activo — reglas determinísticas sobre assessments |

### 2.3 Decisión deliberada

Unificar análisis de mercado, evaluación de riesgo, evaluación económica y evaluación de exposición en un solo pipeline es una **decisión consciente** para la etapa temprana del sistema:

| Ventaja | Costo aceptado |
|---|---|
| Un solo punto de entrada (`analyze()`) | Límites de dominio menos explícitos en el código |
| Contrato de salida único (`AnalysisResult`) | `RiskEngine` y `EconomicFilter` no son claramente "predicción" ni "mercado puro" |
| Iteración rápida sobre heurísticas | Refactor inevitable cuando aparezcan Prediction y Decision |
| Tests y fixtures centralizados en `engine/tests/` | Acoplamiento temporal entre síntesis y assessments |

**Principio rector vigente:** el motor **solo produce conocimiento**. No ejecuta acciones. Eso se mantiene independientemente de cuántos motores existan en el futuro.

---

## 3. Evolución prevista — motores especializados

A medida que crezcan las reglas, los horizontes temporales y la complejidad de cartera, los dominios tenderán a **motores independientes** con contratos explícitos entre sí.

```
                         MarketData
                             │
                             ▼
                   ┌─────────────────────┐
                   │ MarketAnalysisEngine │
                   │  (estado presente)   │
                   └──────────┬──────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               │
     ┌────────────────┐  ┌──────────────┐     │
     │ PredictionEngine│  │PortfolioEngine│    │
     │ (escenarios)    │  │ (capacidad)   │    │
     └────────┬───────┘  └──────┬───────┘     │
              │                 │             │
              └────────┬────────┘             │
                       ▼                       │
              ┌─────────────────┐              │
              │  DecisionEngine  │◄─────────────┘
              │ (coherencia)     │   PortfolioState
              └────────┬────────┘   PortfolioConstraints
                       │
                       ▼
                 DecisionResult
           (estrategias, gates, razones)
```

### 3.1 Responsabilidades futuras por motor

| Motor | Entrada principal | Salida principal | Dominio |
|---|---|---|---|
| `MarketAnalysisEngine` | `MarketData` | `MarketAssessment` (régimen, volatilidad, liquidez, calidad) | Market Analysis |
| `PredictionEngine` | `MarketAssessment` (+ opcional: features externas) | `PredictionResult` (escenarios, probabilidades) | Prediction |
| `PortfolioEngine` | `PortfolioState`, `PortfolioConstraints`, `MarketAssessment` | `PortfolioAssessment` (exposición, headroom, límites) | Portfolio Intelligence |
| `DecisionEngine` | assessments de los tres motores anteriores | `DecisionResult` (allowed/forbidden/preferred, hard gates) | Decision Support |

### 3.2 Qué migra de dónde

| Componente actual | Destino probable |
|---|---|
| `RegimeDetector`, `EconomicFilter`, `candle_metrics` | Permanecen en `MarketAnalysisEngine` |
| `RiskEngine` | Dividir: parte de mercado (volatilidad, caos) → Market; parte de cartera (drawdown, concentración) → Portfolio; parte prospectiva → Prediction |
| `PortfolioManager` | Evoluciona a `PortfolioEngine` |
| `CatalogBuilder` | Evoluciona a `DecisionEngine` |
| `AnalysisResult` | Se descompone en resultados por motor + un agregado opcional para consumidores legacy |

### 3.3 Contratos entre motores

Reglas de frontera para cuando se separen:

1. **Flujo unidireccional:** Market → Prediction / Portfolio → Decision. Sin ciclos.
2. **Motores puros:** cada motor es determinístico, sin I/O, sin efectos secundarios (igual que hoy).
3. **Evidencia explícita:** cada assessment lleva `reasons` y `components` (patrón ya presente en assessments actuales).
4. **Decision no re-analiza mercado:** consume assessments; no recalcula ATR ni régimen.
5. **Portfolio no elige estrategias:** solo informa capacidad; Decision aplica gates de exposición.

---

## 4. Etapas de transición sugeridas

| Etapa | Objetivo | Cambio arquitectónico |
|---|---|---|
| **A (actual)** | Pipeline unificado funcional | `MarketAnalysisEngine` + `AnalysisResult` monolítico |
| **B** | Separar conceptos en modelos | Extraer `MarketAssessment`, `PortfolioAssessment` como tipos distintos dentro del mismo pipeline |
| **C** | Extraer Portfolio | `PortfolioEngine` independiente; facade los compone |
| **D** | Introducir Prediction | `PredictionEngine` con escenarios mínimos (ej. probabilidad de ruptura de rango) |
| **E** | Extraer Decision | `CatalogBuilder` → `DecisionEngine`; facade opcional para compatibilidad |
| **F** | Orquestación externa | Capa de aplicación compone motores; el paquete `engine/` exporta motores, no un mega-facade |

No es obligatorio completar todas las etapas. La separación debe **justificarse por complejidad real**, no por pureza arquitectónica.

---

## 5. Qué NO cambia con esta evolución

Independientemente de cuántos motores existan:

- **Sin ejecución:** ningún motor coloca órdenes, crea bots ni persiste estado.
- **Sin dependencias externas:** el núcleo permanece con `dependencies = []`.
- **Dataclasses inmutables:** entradas y salidas como `@dataclass(frozen=True)`.
- **Tests co-locados:** `src/engine/tests/` valida cada motor o analyzer.
- **IA downstream:** si se usa LLM para elegir estrategia o parametrizar, vive **fuera** de estos dominios y consume `DecisionResult` o equivalente.

---

## 6. Resumen

| Hoy | Mañana (dirección) |
|---|---|
| Un dominio de análisis que absorbe riesgo, economía, exposición y decisión parcial | Cuatro dominios con motores especializados y contratos claros |
| `MarketAnalysisEngine.analyze()` | Composición: Market → Prediction + Portfolio → Decision |
| `AnalysisResult` único | Resultados por dominio + agregado opcional |
| Prediction inexistente | `PredictionEngine` cuando haya escenarios que justifiquen su costo |

> **En una frase:** hoy simplificamos evolucionando un pipeline único que concentra interpretación del presente y soporte de decisión; mañana especializamos cuando la complejidad de cada dominio lo exija, sin romper el principio de que el núcleo solo produce conocimiento.
