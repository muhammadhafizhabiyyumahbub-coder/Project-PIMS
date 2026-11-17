# Engine Architecture

**Personal Investment Management System (PIMS)**

| Document Information | Value |
|---|---|
| Document | Engine Architecture |
| Version | 1.0 |
| Status | Architecture Specification |
| Architecture Style | Modular Monolith |
| Processing Language | Python |
| Analytics Libraries | NumPy, Pandas, SciPy |
| Primary Database | PostgreSQL |

---

# 1. Purpose

This document defines the architecture, responsibilities, dependencies, processing workflows, and interaction contracts of analytical engines within the Personal Investment Management System (PIMS).

The engine layer is responsible for transforming normalized financial data and portfolio information into structured analytical results.

The architecture covers:

- Portfolio Performance Engine.
- Risk Analysis Engine.
- Asset Allocation Engine.
- Technical Analysis Engine.
- Correlation Analysis Engine.
- Market Regime Engine.
- Market Scanner Engine.
- Fundamental Analysis Engine.
- Sentiment Analysis Engine.
- Macro Analysis Engine.
- Factor Analysis Engine.
- Attribution Engine.
- Backtesting Engine.
- Scenario Analysis Engine.
- AI Research Engine.

The objective is to create an analytical architecture that is modular, deterministic where appropriate, independently testable, and extensible.

# 2. Engine Architecture Principles

All engines must follow these principles.

## 2.1 Separation of Responsibilities

Each engine must have a clearly defined analytical responsibility.

An engine must not duplicate the primary calculation responsibilities of another engine.

## 2.2 Deterministic Calculations

Financial calculations must use explicit mathematical logic and defined input data.

Given the same inputs, calculation parameters, and software version, deterministic engines should produce reproducible outputs.

## 2.3 Provider Independence

Analytical engines must not connect directly to external market data providers.

They consume standardized data supplied by the Market Data Layer.

## 2.4 Independent Testability

Each engine should be testable independently of unrelated engines, external providers, and frontend components.

## 2.5 Explicit Data Contracts

Every engine must define:
- Required inputs.
- Optional inputs.
- Configuration parameters.
- Output structure.
- Validation rules.
- Error conditions.
- Calculation methodology.

## 2.6 Controlled Dependencies

Engines should communicate through defined interfaces and structured outputs.

Direct access to another engine's private implementation is prohibited.

## 2.7 Reproducibility

Analytical results should retain sufficient metadata to reproduce or explain their calculations.

Relevant metadata includes:
- Input data references.
- Calculation timestamp.
- Observation period.
- Parameters.
- Methodology version.
- Data quality status.

# 3. Engine Classification

PIMS engines are divided into five functional categories.

| Category | Engines |
|---|---|
| Portfolio Analytics | Portfolio Performance, Risk, Allocation, Attribution |
| Market Analytics | Technical Analysis, Market Regime, Correlation, Factor |
| Market Intelligence | Fundamental, Sentiment, Macro |
| Market Screening | Market Scanner |
| Research and Simulation | AI Research, Backtesting, Scenario Analysis |

These categories represent logical groupings, not separate services.

All engines initially operate inside the backend Modular Monolith.

# 4. High-Level Engine Architecture

```text
                 NORMALIZED DATA
                        |
          +-------------+-------------+
          |                           |
          v                           v
    PORTFOLIO DATA                MARKET DATA
          |                           |
          v                           v
  +----------------+       +---------------------+
  | Portfolio      |       | Technical Analysis  |
  | Performance    |       | Market Regime       |
  +----------------+       | Correlation         |
          |                | Factor Analysis     |
          v                +---------------------+
  +----------------+                  |
  | Risk Analysis  |                  |
  +----------------+                  |
          |                           |
          v                           v
  +----------------+          +----------------+
  | Allocation     |          | Market Scanner |
  +----------------+          +----------------+
          |                           |
          +-------------+-------------+
                        |
                        v
                 ANALYTICAL RESULTS
                        |
             +----------+----------+
             |                     |
             v                     v
       Dashboard UI           AI Research
```

Fundamental and macro information may feed relevant analytical engines when the required data is available.

# 5. Standard Engine Structure

Every engine should follow a consistent internal organization.

Conceptual structure:

```text
engine_name/
├── __init__.py
├── engine.py
├── inputs.py
├── outputs.py
├── calculations.py
├── validators.py
├── config.py
└── tests/
```

This is a logical template, not a requirement to create every file for every engine.

Smaller engines may use fewer files when separation would create unnecessary complexity.

## 5.1 Engine Processing Pipeline

```text
Input Data
    |
    v
Input Validation
    |
    v
Preprocessing
    |
    v
Core Calculation
    |
    v
Output Validation
    |
    v
Structured Result
    |
    v
Application Service
```

## 5.2 Standard Input Contract

Each engine input should identify:

| Field | Purpose |
|---|---|
| Asset ID | Internal asset reference |
| Portfolio ID | Relevant portfolio, if applicable |
| Market | Market classification |
| Data Source | Source of input data |
| Data Timestamp | Time of source data |
| Observation Period | Calculation period |
| Interval | Data frequency |
| Parameters | Calculation configuration |
| Data Quality | Input reliability status |

Not every field is required by every engine.

## 5.3 Standard Output Contract

Each engine should return a structured result containing:

| Field | Purpose |
|---|---|
| Engine Name | Engine identifier |
| Engine Version | Calculation implementation version |
| Status | Execution status |
| Result | Calculated metrics |
| Timestamp | Calculation time |
| Input Reference | Relevant input identification |
| Parameters | Parameters used |
| Data Quality | Input data quality |
| Warnings | Relevant limitations |

The output schema should be specific to each engine while retaining consistent metadata.

# 6. Portfolio Performance Engine

## 6.1 Purpose

The Portfolio Performance Engine calculates the performance and valuation-related metrics of an investment portfolio.

It is responsible for translating portfolio holdings, transaction records, cash movements, and market prices into structured performance information.

## 6.2 Responsibilities

- Portfolio valuation.
- Total return calculation.
- Daily P&L.
- Realized P&L.
- Unrealized P&L.
- Historical performance.
- CAGR.
- Benchmark comparison.
- Portfolio contribution analysis where supported.

## 6.3 Input Data

- Portfolio records.
- Holdings.
- Transaction history.
- Cash balances.
- Market prices.
- Currency conversion data.
- Benchmark data where required.

## 6.4 Processing Flow

```text
Portfolio Records
       |
       v
Transaction History
       |
       v
Holdings Reconciliation
       |
       v
Market Price Lookup
       |
       v
Currency Conversion
       |
       v
Portfolio Valuation
       |
       v
Performance Calculation
       |
       v
Performance Results
```

## 6.5 Output

- Total portfolio value.
- Invested capital.
- Available cash.
- Daily P&L.
- Total return.
- Realized P&L.
- Unrealized P&L.
- Historical return series.
- Benchmark-relative performance where supported.

## 6.6 Calculation Requirements

The engine must distinguish between:
- Absolute return.
- Percentage return.
- Time-weighted return.
- Money-weighted return.

The selected methodology must be explicitly documented.

CAGR must only be calculated when the required time period and valuation data are available.

Portfolio accounting rules must be consistent with the Transaction and Holdings modules.

# 7. Risk Analysis Engine

## 7.1 Purpose

The Risk Analysis Engine evaluates portfolio risk and historical return behavior.

It transforms portfolio return series and asset exposures into measurable risk indicators.

## 7.2 Responsibilities

- Volatility measurement.
- Drawdown analysis.
- Risk-adjusted performance.
- Downside risk.
- Value at Risk.
- Conditional Value at Risk.
- Portfolio concentration.
- Asset exposure analysis.

## 7.3 Input Data

- Portfolio return series.
- Asset weights.
- Historical asset prices.
- Benchmark returns where applicable.
- Risk-free rate where required.

## 7.4 Core Metrics

| Metric | Purpose |
|---|---|
| Volatility | Measures return variability |
| Maximum Drawdown | Measures the largest observed peak-to-trough decline |
| Sharpe Ratio | Measures excess return relative to total volatility |
| Sortino Ratio | Measures excess return relative to downside deviation |
| Value at Risk | Estimates a loss threshold under a specified model |
| Conditional VaR | Estimates expected loss beyond a VaR threshold |
| Beta | Measures sensitivity relative to a benchmark |
| Concentration | Measures portfolio exposure concentration |

## 7.5 Processing Flow

```text
Portfolio Returns
       |
       v
Data Validation
       |
       v
Return Series Preparation
       |
       v
Risk Metric Calculations
       |
       v
Risk Result Validation
       |
       v
Risk Report
```

## 7.6 Calculation Requirements

Every risk metric must document:
- Observation period.
- Return frequency.
- Annualization convention.
- Confidence level where applicable.
- Statistical assumptions.
- Missing-data policy.

Historical risk measurements must not be presented as guarantees of future outcomes.

# 8. Asset Allocation Engine

## 8.1 Purpose

The Asset Allocation Engine evaluates portfolio composition and exposure distribution.

## 8.2 Responsibilities

- Asset allocation.
- Asset class distribution.
- Market exposure.
- Sector exposure where available.
- Individual asset weights.
- Currency exposure.
- Concentration analysis.

## 8.3 Input Data

- Portfolio holdings.
- Asset classifications.
- Current market prices.
- Currency conversion data.

## 8.4 Output

- Allocation by asset class.
- Allocation by market.
- Allocation by asset.
- Sector allocation where available.
- Currency exposure.
- Largest portfolio positions.

## 8.5 Processing Flow

```text
Portfolio Holdings
        |
        v
Asset Classification
        |
        v
Market Valuation
        |
        v
Weight Calculation
        |
        v
Exposure Aggregation
        |
        v
Allocation Results
```

All allocation weights must use a clearly defined portfolio value denominator.

# 9. Technical Analysis Engine

## 9.1 Purpose

The Technical Analysis Engine calculates technical indicators using historical market data.

## 9.2 Responsibilities

- Trend indicators.
- Momentum indicators.
- Volatility indicators.
- Volume indicators.
- Technical signal generation.

## 9.3 Supported Indicators

| Indicator | Category |
|---|---|
| SMA | Trend |
| EMA | Trend |
| RSI | Momentum |
| MACD | Momentum |
| Bollinger Bands | Volatility |
| ATR | Volatility |
| Stochastic Oscillator | Momentum |
| VWAP | Price and volume |

The initial implementation should prioritize a manageable indicator set rather than implementing every indicator simultaneously.

## 9.4 Input Data

- OHLCV data.
- Asset identifier.
- Time interval.
- Indicator parameters.

## 9.5 Processing Flow

```text
Historical OHLCV
       |
       v
Input Validation
       |
       v
Indicator Calculation
       |
       v
Signal Evaluation
       |
       v
Technical Analysis Output
```

## 9.6 Output

- Indicator values.
- Trend classification where defined.
- Momentum classification where defined.
- Volatility measurements.
- Technical conditions.
- Calculation timestamps.

Indicator values and signal interpretations must be distinguishable.

The engine must not represent an indicator condition as a guaranteed future price movement.

# 10. Correlation Analysis Engine

## 10.1 Purpose

The Correlation Analysis Engine measures relationships between asset returns.

## 10.2 Responsibilities

- Pairwise correlation.
- Correlation matrix.
- Rolling correlation.
- Asset relationship analysis.
- Diversification-related metrics.

## 10.3 Input Data

- Historical asset prices.
- Historical asset returns.
- Observation period.
- Return frequency.
- Selected assets.

## 10.4 Processing Flow

```text
Historical Prices
       |
       v
Return Calculation
       |
       v
Calendar Alignment
       |
       v
Missing Data Handling
       |
       v
Correlation Calculation
       |
       v
Correlation Matrix
```

## 10.5 Output

- Correlation matrix.
- Pairwise correlation values.
- Rolling correlation series.
- Data coverage information.

The engine must define its missing-data and market-calendar alignment policies.

Correlation does not establish causation and does not independently measure total portfolio risk.

# 11. Market Regime Engine

## 11.1 Purpose

The Market Regime Engine classifies prevailing market conditions using defined quantitative criteria.

## 11.2 Responsibilities

- Trend classification.
- Volatility regime classification.
- Market condition analysis.
- Regime transition detection.
- Historical regime identification.

## 11.3 Possible Regimes

Initial regime categories:

- Bullish.
- Bearish.
- Sideways.
- High Volatility.
- Low Volatility.

The system may later support more sophisticated regime models.

## 11.4 Input Data

- Historical price series.
- Trend indicators.
- Volatility indicators.
- Market benchmark data where applicable.

## 11.5 Processing Flow

```text
Historical Market Data
         |
         v
Feature Calculation
         |
         v
Regime Rules / Model
         |
         v
Classification
         |
         v
Regime Result
```

## 11.6 Output

- Current regime classification.
- Regime confidence or classification strength where defined.
- Supporting metrics.
- Historical regime series.
- Timestamp.

The engine must document its classification methodology and avoid presenting a regime label as an objective certainty.

# 12. Market Scanner Engine

## 12.1 Purpose

The Market Scanner Engine identifies instruments matching defined analytical screening criteria across the supported market universe.

It is a separate analytical engine and must not be limited to assets already held in a portfolio.

## 12.2 Responsibilities

- Market universe management.
- Asset eligibility evaluation.
- Screening condition evaluation.
- Feature calculation coordination.
- Result ranking.
- Scanner result generation.

## 12.3 Scanner Categories

| Category | Description |
|---|---|
| Technical | Indicator-based conditions |
| Momentum | Price momentum |
| Volume | Trading activity |
| Volatility | Price variability |
| Fundamental | Financial metrics |
| Market Trend | Trend conditions |
| Anomaly | Unusual observations |
| Correlation | Asset relationship conditions |

## 12.4 Processing Flow

```text
Market Universe
       |
       v
Eligibility Filter
       |
       v
Market Data Retrieval
       |
       v
Feature Calculation
       |
       v
Screening Rules
       |
       v
Ranking
       |
       v
Scanner Results
```

## 12.5 Output

Each scanner result should contain:
- Asset identifier.
- Symbol.
- Market.
- Matched criteria.
- Relevant metrics.
- Ranking or score where defined.
- Data timestamp.
- Calculation timestamp.
- Data quality status.

Ranking logic must be explicit, documented, and reproducible.

The scanner provides analytical screening results, not personalized trading instructions.

# 13. Fundamental Analysis Engine

## 13.1 Purpose

The Fundamental Analysis Engine evaluates company financial information and relevant valuation metrics.

## 13.2 Responsibilities

- Financial statement analysis.
- Revenue and earnings growth.
- Profitability analysis.
- Financial health.
- Cash flow analysis.
- Valuation ratios.
- Fundamental screening.

## 13.3 Input Data

- Income statements.
- Balance sheets.
- Cash flow statements.
- Share information.
- Market capitalization.
- Financial ratios.
- Reporting period and currency.

## 13.4 Output

- Revenue growth.
- Profitability metrics.
- Debt and liquidity metrics.
- Cash flow metrics.
- Valuation metrics.
- Fundamental screening results.

The engine must account for differences in reporting periods, accounting conventions, currencies, and data availability.

It must not compare financial metrics across companies without considering comparability limitations.

# 14. Sentiment Analysis Engine

## 14.1 Purpose

The Sentiment Analysis Engine evaluates available news and public information to produce structured sentiment indicators.

## 14.2 Responsibilities

- News classification.
- Sentiment scoring.
- Topic identification.
- Entity recognition.
- Sentiment trend analysis.

## 14.3 Input Data

- News articles.
- Publication timestamps.
- Source metadata.
- Asset or company identifiers.
- Relevant public information.

## 14.4 Output

- Sentiment classification.
- Sentiment score.
- Related topics.
- Source references.
- Publication timestamps.
- Confidence or quality metadata where supported.

The engine must distinguish publication time from ingestion time and avoid treating sentiment scores as direct price predictions.

# 15. Macro Analysis Engine

## 15.1 Purpose

The Macro Analysis Engine organizes and evaluates macroeconomic information relevant to financial markets.

## 15.2 Responsibilities

- Inflation monitoring.
- Interest rate monitoring.
- Economic growth analysis.
- Currency and exchange rate analysis.
- Employment indicators.
- Macroeconomic trend analysis.

## 15.3 Input Data

- Macroeconomic indicators.
- Central bank data.
- Economic releases.
- Currency data.
- Historical macroeconomic observations.

## 15.4 Output

- Macro indicator summaries.
- Historical trends.
- Relevant economic changes.
- Market context indicators.

The engine must account for publication schedules, revisions, and differences between observation dates and release dates.

# 16. Factor Analysis Engine

## 16.1 Purpose

The Factor Analysis Engine evaluates portfolio or asset exposure to defined quantitative factors.

## 16.2 Initial Factor Categories

- Momentum.
- Value.
- Quality.
- Growth.
- Low Volatility.
- Size.

## 16.3 Responsibilities

- Factor metric calculation.
- Factor exposure analysis.
- Portfolio factor aggregation.
- Factor comparison.
- Historical factor exposure.

## 16.4 Output

- Factor scores.
- Portfolio factor exposures.
- Asset factor profiles.
- Historical factor exposure series.

Factor definitions, normalization methods, and required datasets must be documented before implementation.

# 17. Attribution Engine

## 17.1 Purpose

The Attribution Engine evaluates the sources of portfolio performance.

## 17.2 Responsibilities

- Asset contribution analysis.
- Sector contribution analysis where data exists.
- Allocation contribution.
- Selection contribution where methodology permits.
- Benchmark-relative attribution.

## 17.3 Input Data

- Portfolio holdings.
- Historical weights.
- Asset returns.
- Sector classifications.
- Benchmark returns.

## 17.4 Output

- Contribution by asset.
- Contribution by sector.
- Allocation effects.
- Selection effects.
- Total attribution reconciliation.

Attribution methodology must be explicitly selected and documented.

# 18. Backtesting Engine

## 18.1 Purpose

The Backtesting Engine evaluates historical strategy rules against historical market data.

## 18.2 Responsibilities

- Historical simulation.
- Strategy rule execution.
- Portfolio simulation.
- Transaction cost modeling.
- Performance measurement.
- Risk measurement.

## 18.3 Input Data

- Historical market data.
- Strategy parameters.
- Starting capital.
- Position sizing rules.
- Transaction costs.
- Slippage assumptions.
- Trading calendar and execution assumptions.

## 18.4 Output

- Historical equity curve.
- Total return.
- Drawdown.
- Trade statistics.
- Risk metrics.
- Benchmark comparison.

The engine must prevent look-ahead bias and account for survivorship bias where relevant.

Historical backtest results must not be presented as guaranteed future performance.

# 19. Scenario Analysis Engine

## 19.1 Purpose

The Scenario Analysis Engine evaluates hypothetical portfolio outcomes under defined assumptions.

## 19.2 Responsibilities

- What-if analysis.
- Price shock scenarios.
- Currency movement scenarios.
- Interest rate scenarios where relevant.
- Portfolio exposure impact.
- Scenario comparison.

## 19.3 Input Data

- Current portfolio state.
- Asset exposures.
- Scenario assumptions.
- Relevant sensitivity parameters.

## 19.4 Output

- Scenario portfolio value.
- Estimated P&L impact.
- Asset-level impact.
- Exposure changes.
- Comparison between scenarios.

All scenario outputs must be clearly labeled as hypothetical estimates.

# 20. AI Research Engine

## 20.1 Purpose

The AI Research Engine assists users in interpreting structured financial information and generating research reports.

It is an interpretation and research subsystem, not a replacement for quantitative engines.

## 20.2 Internal Components

- AI Provider Adapter.
- Context Builder.
- Research Orchestrator.
- Report Generator.
- Output Validation.

## 20.3 Input Data

- Portfolio summaries.
- Quantitative analytics results.
- Market regime outputs.
- Technical analysis results.
- Fundamental information.
- Sentiment information.
- Macro information.
- External research sources where available.

## 20.4 Processing Flow

```text
User Research Request
        |
        v
Research Orchestrator
        |
        v
Context Builder
        |
        v
Structured Data Validation
        |
        v
LLM Provider
        |
        v
Response Validation
        |
        v
Research Report
```

## 20.5 Output

- Research summary.
- Market context.
- Analytical interpretation.
- Risk observations.
- Supporting data references.
- Limitations and uncertainties.

AI-generated statements must be distinguishable from verified data and deterministic calculations.

# 21. Engine Dependency Architecture

Dependencies must remain controlled.

Conceptual dependency relationships:

```text
Market Data
     |
     +-------------------+
     |                   |
     v                   v
Technical Analysis   Fundamental Analysis
     |                   |
     v                   v
Market Regime        Factor Analysis
     |                   |
     +---------+---------+
               |
               v
         Market Scanner


Portfolio Transactions
          |
          v
    Holdings State
          |
          v
  Portfolio Performance
          |
          +------------------+
          |                  |
          v                  v
    Risk Analysis      Asset Allocation
          |                  |
          +---------+--------+
                    |
                    v
             Correlation Analysis


Analytics Results
        |
        v
   AI Research
```

This diagram describes conceptual dependencies, not mandatory direct engine-to-engine calls.

Application services should coordinate multi-engine workflows.

For example, Risk Analysis may consume portfolio return series from a portfolio data service rather than importing private calculation functions from Portfolio Performance.

# 22. Engine Execution Strategy

Not all engines require the same execution frequency.

PIMS should support three execution modes.

## 22.1 Request-Driven Execution

Executed when requested by the user or another application workflow.

Examples:
- Portfolio performance report.
- Historical correlation analysis.
- Scenario analysis.
- Backtesting.
- AI research.

## 22.2 Scheduled Execution

Executed periodically or according to a defined market-data schedule.

Examples:
- Market Scanner.
- Fundamental data refresh.
- Macro data refresh.
- Periodic portfolio analytics.

## 22.3 Event-Driven Execution

Triggered by relevant data or application events.

Examples:
- Candle completion.
- New market data.
- Portfolio transaction recorded.
- Updated market reference data.

Event-driven execution must include deduplication and controlled processing so that the same event does not produce inconsistent duplicate results.

The initial implementation should use the simplest execution mechanism that satisfies workload requirements. A distributed task queue should only be introduced when justified.

# 23. Performance and Computational Efficiency

Engine performance must be considered as the number of supported assets and analytical requests grows.

Requirements:

- Reuse normalized input data.
- Avoid repeated unnecessary calculations.
- Cache appropriate intermediate results.
- Support batch processing for scanner workloads.
- Avoid loading entire historical datasets when only a limited window is required.
- Use vectorized numerical operations where appropriate.
- Define execution time and resource limits for expensive tasks.
- Track execution status and failures.

Optimization must not compromise calculation correctness.

# 24. Testing and Validation

Every engine must have independent tests.

## 24.1 Unit Testing

Test:
- Calculation correctness.
- Input validation.
- Boundary conditions.
- Missing data.
- Invalid values.
- Output consistency.

## 24.2 Integration Testing

Test:
- Data contracts.
- Repository integration.
- Application service orchestration.
- Dependencies between analytical modules.

## 24.3 Financial Calculation Validation

Where possible, verify financial metrics against independently calculated reference examples.

Use fixed datasets and known expected results.

Pay particular attention to:
- Precision.
- Rounding.
- Annualization.
- Time alignment.
- Currency conversion.
- Missing observations.
- Accounting conventions.

## 24.4 Reproducibility

Tests should verify that identical inputs and parameters produce identical outputs for deterministic engines.

Any intentional nondeterministic or model-based processing must be documented separately.

# 25. Implementation Priority

Not all engines should be implemented simultaneously.

Recommended priority:

| Priority | Engine | Reason |
|---|---|---|
| 1 | Portfolio Performance | Core portfolio visibility |
| 2 | Risk Analysis | Portfolio risk understanding |
| 3 | Asset Allocation | Portfolio composition |
| 4 | Technical Analysis | Market analysis foundation |
| 5 | Correlation Analysis | Diversification analysis |
| 6 | Market Regime | Market condition context |
| 7 | Market Scanner | Market-wide screening |
| 8 | Fundamental Analysis | Company-level evaluation |
| 9 | AI Research | Interpretation and reporting |
| 10 | Sentiment / Macro / Factor | Expanded research capabilities |
| 11 | Attribution | Deeper performance analysis |
| 12 | Backtesting / Scenario | Advanced simulation |

This priority is a development sequence, not a ranking of investment importance.

Each engine must have its own detailed specification before implementation.

# 26. Architectural Constraints

The following constraints are mandatory:

1. Engines must remain modular components of the backend Modular Monolith.
2. Engines must not connect directly to external market data providers.
3. Financial calculations must be deterministic where mathematically applicable.
4. AI must not replace authoritative financial calculations.
5. Engines must define explicit input and output contracts.
6. Engines must be independently testable.
7. Engine dependencies must not create circular relationships.
8. Expensive calculations must use appropriate execution strategies.
9. Results must retain calculation and data-source metadata.
10. No engine should be implemented without sufficiently defined requirements.
11. Ranking and scoring logic must be documented.
12. Historical simulation must account for methodological biases and assumptions.

# 27. Relationship with Other Documents

| Document | Purpose |
|---|---|
| `AGENTS.md` | Coding agent instructions |
| `docs/architecture/system-architecture.md` | Overall system architecture |
| `docs/architecture/application-architecture.md` | Internal application architecture |
| `docs/architecture/data-flow.md` | Data processing and movement |
| `docs/database/database-design.md` | Database design |
| `specifications/engines/portfolio-engine-spec.md` | Portfolio engine requirements |
| `specifications/engines/risk-engine-spec.md` | Risk engine requirements |
| `specifications/engines/allocation-engine-spec.md` | Allocation engine requirements |
| `specifications/engines/technical-analysis-spec.md` | Technical analysis requirements |
| `specifications/engines/correlation-engine-spec.md` | Correlation requirements |
| `specifications/engines/market-regime-spec.md` | Market regime requirements |
| `specifications/engines/market-scanner-spec.md` | Scanner requirements |
| `specifications/engines/ai-research-spec.md` | AI research requirements |

# 28. Final Principle

The PIMS Engine Architecture must provide a reliable foundation for quantitative analysis, portfolio evaluation, market intelligence, and research.

Each engine must have a clearly defined purpose, validated inputs, reproducible calculations where applicable, structured outputs, and controlled dependencies.

The system should prioritize analytical correctness and architectural clarity before expanding into more advanced models.

**The goal is to build an integrated analytical platform, not a collection of disconnected financial calculators.**