# Data Flow Architecture

**Personal Investment Management System (PIMS)**

| Document Information | Value |
|---|---|
| Document | Data Flow Architecture |
| Version | 1.0 |
| Status | Architecture Specification |
| Architecture Style | Modular Monolith |
| Primary Database | PostgreSQL |
| Backend | Python / FastAPI |
| Frontend | Next.js / React / TypeScript |
| Real-Time Communication | WebSocket |

---

# 1. Purpose

This document defines how data moves throughout the Personal Investment Management System (PIMS).

It describes the complete data lifecycle, including:

- External market data acquisition.
- Data ingestion.
- Data normalization.
- Data validation.
- Data aggregation.
- Data storage.
- Real-time data distribution.
- Portfolio data processing.
- Quantitative analytics.
- Market scanning.
- AI research context preparation.
- Frontend data presentation.

The objective is to establish a consistent and reliable data flow across all application modules.

# 2. Data Flow Overview

PIMS processes several categories of data:

| Data Category | Description | Main Consumer |
|---|---|---|
| Market Data | Prices, candles, volume, and market information | Charts, Scanner, Analytics |
| Portfolio Data | Portfolios, holdings, and transactions | Portfolio Engine |
| Reference Data | Asset identity, market, currency, and metadata | All relevant modules |
| Analytical Data | Indicators, performance, risk, and allocation results | Dashboard and Analytics |
| Scanner Data | Screening conditions and ranked instruments | Market Scanner UI |
| Research Data | News, financial information, and research context | AI Research |
| User Data | Preferences and application settings | Frontend and Backend |

The application must maintain clear ownership and processing boundaries for each data category.

## 2.1 High-Level Data Flow

```text
                  EXTERNAL DATA SOURCES
                           |
             +-------------+-------------+
             |             |             |
           Bybit        Finnhub       IDX Provider
             |             |             |
             +-------------+-------------+
                           |
                           v
                  PROVIDER ADAPTERS
                           |
                           v
                   DATA INGESTION
                           |
                           v
                  DATA NORMALIZATION
                           |
                           v
                    DATA VALIDATION
                           |
                           v
                   DATA AGGREGATION
                           |
                  +--------+--------+
                  |                 |
                  v                 v
              PostgreSQL       Market Data
                  |             Publisher
                  |                 |
                  v                 v
           Analytics Engines    WebSocket
                  |                 |
                  v                 v
           Analytical Results   Frontend
                  |
                  v
              Dashboard
```

This represents the logical flow. Actual processing may differ depending on the type of data and provider capabilities.

# 3. Market Data Flow

Market data is the primary external data source used by PIMS.

The market data pipeline must provide standardized and validated information to the rest of the application.

## 3.1 Market Data Acquisition

Initial provider categories:

| Market | Provider |
|---|---|
| Cryptocurrency | Bybit |
| US Stocks | Finnhub / Alpaca |
| Indonesian Stocks | Provider to be evaluated |

The provider adapter is responsible for communicating with the external provider.

Two main acquisition methods are supported:

**REST API**
- Historical OHLCV data.
- Asset information.
- Reference data.
- Market snapshots where supported.

**WebSocket**
- Live trades.
- Live price updates.
- Live candle updates.
- Market events where supported.

The application must respect provider rate limits, subscription restrictions, and licensing conditions.

## 3.2 Provider Adapter Processing

Each provider returns data using its own response structure.

The provider adapter translates these responses into internal application data contracts.

Conceptual flow:

```text
External Provider
       |
       v
Provider API / WebSocket
       |
       v
Provider Adapter
       |
       v
Internal Data Contract
       |
       v
Data Ingestion Pipeline
```

Provider-specific response formats must not propagate into portfolio or analytics business logic.

## 3.3 Normalization

Normalization converts incoming data into a consistent internal format.

The normalized market data should contain relevant fields such as:

| Field | Description |
|---|---|
| Asset ID | Internal asset identifier |
| Symbol | Standardized symbol |
| Market | Crypto, US Stocks, or IDX |
| Provider | Data source identifier |
| Timestamp | Original event or candle timestamp |
| Interval | Candle interval, when applicable |
| Open | Opening price |
| High | Highest price |
| Low | Lowest price |
| Close | Closing price |
| Volume | Trading volume |
| Currency | Quote currency |
| Data Type | Trade, quote, candle, or snapshot |

Fields that do not apply to a specific data type should be optional or represented through an appropriate data contract.

The system must preserve the original provider timestamp and identify the timestamp convention used.

## 3.4 Data Validation

Before data is stored or distributed, it must pass validation.

Validation requirements:

- Required fields must be present.
- Timestamps must be valid.
- Numeric values must be valid.
- OHLC relationships must be consistent.
- Duplicate records must be handled.
- Data intervals must be checked.
- Asset identifiers must be recognized.
- Currency and market identifiers must be valid.

Example OHLC validation:

```text
High >= Open
High >= Close
Low <= Open
Low <= Close
High >= Low
```

Invalid data should be rejected, quarantined, or flagged according to its error category.

The application must not silently replace invalid data with fabricated values.

## 3.5 Data Aggregation

Aggregation is necessary when the provider supplies trade-level or tick-level data rather than candle data.

For OHLCV candles:

| Field | Calculation |
|---|---|
| Open | First trade price in the interval |
| High | Maximum trade price |
| Low | Minimum trade price |
| Close | Last trade price |
| Volume | Sum of trade volume |

Aggregation must follow a defined interval boundary and timezone convention.

If the provider already supplies valid candles, PIMS should use those candles rather than unnecessarily reconstructing them.

## 3.6 Market Data Storage

Validated market data is stored in PostgreSQL.

Potential data categories:

- Historical candles.
- Asset reference information.
- Market metadata.
- Provider metadata.
- Data quality records.
- Data update timestamps.

Historical data should be stored with enough information to identify:

- Asset.
- Provider.
- Interval.
- Timestamp.
- Currency.
- Data source.

Duplicate handling and data correction policies must be defined to prevent inconsistent historical records.

# 4. Real-Time Market Data Flow

Real-time market data uses a centralized backend connection model.

The frontend must not connect independently to external provider WebSockets for every chart or component.

## 4.1 Real-Time Pipeline

```text
Market Data Provider
        |
        v
Provider WebSocket
        |
        v
Provider Adapter
        |
        v
Normalization
        |
        v
Validation
        |
        v
Market Data Service
        |
        +----------------------+
        |                      |
        v                      v
Data Storage            Event Publisher
                               |
                               v
                         Backend WebSocket
                               |
                               v
                         Frontend Clients
```

Storage and publication may occur through coordinated processing paths. The application must define how failures and retries are handled so that a failed storage operation does not silently produce inconsistent authoritative state.

## 4.2 Subscription Management

The backend manages subscriptions based on active application requirements.

Examples:

- A user opens a BTC chart.
- A user opens an equity chart.
- A dashboard requires selected market prices.
- A scanner requires a defined market data universe.

The backend should reuse shared provider subscriptions where possible.

Subscriptions must be managed centrally to avoid duplicate provider connections and unnecessary data consumption.

## 4.3 Frontend Update Flow

The frontend receives normalized events from the backend WebSocket.

Example event categories:

```text
market.price.updated
market.trade.received
market.candle.updated
market.data.status_changed
portfolio.valuation.updated
scanner.results.updated
```

These are conceptual event names. Exact event contracts must be defined in the WebSocket specification.

The frontend updates only the relevant components.

For Lightweight Charts:

- Historical data initializes the chart.
- New candle events update the current candle.
- Completed candle events update historical chart state.
- Invalid or stale events must not overwrite newer valid data.

## 4.4 Data Freshness

Every market data stream should expose information about its freshness.

Relevant fields include:

- Provider timestamp.
- Received timestamp.
- Last successful update.
- Data interval.
- Market session.
- Data status.
- Delay information where known.

Possible data statuses:

| Status | Meaning |
|---|---|
| LIVE | Provider supports a live feed and updates are current |
| DELAYED | Data is intentionally delayed |
| STALE | Expected updates have not arrived within the configured threshold |
| HISTORICAL | Data represents historical records |
| UNAVAILABLE | Data cannot currently be obtained |
| UNKNOWN | Freshness cannot be reliably determined |

A LIVE label must not be displayed merely because a WebSocket connection is open.

Freshness thresholds should be configured according to the provider, market session, and data interval.

# 5. Historical Market Data Flow

Historical data is primarily obtained through REST API requests.

## 5.1 Historical Data Request

```text
Frontend Chart
      |
      v
Backend REST API
      |
      v
Market Data Service
      |
      +---------------------+
      |                     |
      v                     v
PostgreSQL             Provider Adapter
      |                     |
      |                     v
      |                External Provider
      |                     |
      +----------+----------+
                 |
                 v
          Data Validation
                 |
                 v
          Data Normalization
                 |
                 v
           Data Storage
                 |
                 v
          API Response
                 |
                 v
           Frontend Chart
```

The service should check whether requested historical data already exists before fetching it again.

## 5.2 Historical Data Rules

- Validate requested symbols.
- Validate supported intervals.
- Apply provider rate limits.
- Use pagination where necessary.
- Avoid unnecessary duplicate requests.
- Preserve original timestamps.
- Handle missing intervals explicitly.
- Distinguish missing data from zero-valued data.
- Return metadata describing data source and availability.

Historical data must not be represented as real-time data.

# 6. Portfolio Data Flow

Portfolio data originates from user operations rather than external market providers.

It includes portfolio configuration, transactions, holdings, and cash balances.

## 6.1 Portfolio Creation

```text
User
 |
 v
Frontend
 |
 v
Portfolio API
 |
 v
Portfolio Service
 |
 v
Business Validation
 |
 v
PostgreSQL
 |
 v
API Response
 |
 v
Frontend Dashboard
```

Portfolio creation must validate the required information before persistence.

## 6.2 Transaction Processing

Transactions are the foundation of portfolio accounting.

Conceptual flow:

```text
User Transaction Input
         |
         v
Frontend Form
         |
         v
Transaction API
         |
         v
Input Validation
         |
         v
Transaction Service
         |
         v
Business Rule Validation
         |
         v
Database Transaction
         |
         +---------------------+
         |                     |
         v                     v
Transaction Record       Holdings Update
         |                     |
         +----------+----------+
                    |
                    v
              Portfolio State
```

Transaction records and their corresponding portfolio effects must be handled consistently.

The system should use database transactions to prevent partially applied operations.

Historical corrections must follow an auditable adjustment or reversal process.

## 6.3 Holdings Calculation

Holdings are derived from valid portfolio transactions and supported adjustment records.

The application must define accounting policies for:

- Average cost.
- Realized P&L.
- Unrealized P&L.
- Fees.
- Dividends.
- Corporate actions.
- Deposits and withdrawals.

These rules must be documented before authoritative portfolio calculations are implemented.

The system should avoid maintaining conflicting independent versions of holdings without a clear reconciliation mechanism.

## 6.4 Portfolio Valuation

Portfolio valuation combines portfolio holdings with relevant market prices.

Conceptual flow:

```text
Portfolio Holdings
        |
        v
Asset Identification
        |
        v
Market Price Lookup
        |
        v
Currency Handling
        |
        v
Valuation Calculation
        |
        v
Portfolio Market Value
        |
        v
Portfolio Performance Engine
        |
        v
Dashboard
```

The system must handle unavailable prices, stale prices, and currency conversion explicitly.

A portfolio valuation should communicate its valuation timestamp and data quality.

# 7. Quantitative Analytics Data Flow

Quantitative analytics consume normalized market data and portfolio data.

Analytical engines should not connect directly to external providers.

## 7.1 General Analytics Pipeline

```text
Normalized Data
       |
       v
Data Availability Check
       |
       v
Input Validation
       |
       v
Analytical Engine
       |
       v
Calculation
       |
       v
Result Validation
       |
       v
Structured Output
       |
       v
Storage / API
       |
       v
Frontend Visualization
```

Each engine must define its own input and output contract.

## 7.2 Portfolio Performance Engine

Inputs:
- Portfolio holdings.
- Transaction history.
- Cash movements.
- Market prices.
- Currency conversion data where required.

Outputs may include:
- Portfolio value.
- Total return.
- Daily P&L.
- Realized P&L.
- Unrealized P&L.
- CAGR.
- Benchmark comparison.

Performance calculations must use explicitly defined accounting and return methodologies.

## 7.3 Risk Analysis Engine

Inputs:
- Portfolio return series.
- Asset weights.
- Historical price data.
- Benchmark data where required.

Outputs may include:
- Volatility.
- Maximum drawdown.
- Sharpe ratio.
- Sortino ratio.
- Value at Risk.
- Concentration metrics.

Each metric must document its assumptions, observation period, and calculation methodology.

## 7.4 Asset Allocation Engine

Inputs:
- Holdings.
- Market values.
- Asset classifications.
- Currency conversion data where required.

Outputs:
- Asset class allocation.
- Market allocation.
- Individual asset weights.
- Sector allocation where classification data exists.

## 7.5 Correlation Analysis Engine

Inputs:
- Historical asset return series.
- Selected time interval.
- Observation period.

Outputs:
- Correlation matrix.
- Asset pair correlations.
- Diversification indicators.

The engine must handle missing observations and different market trading calendars.

## 7.6 Technical Analysis Engine

Inputs:
- Historical OHLCV data.
- Selected asset.
- Selected timeframe.

Outputs:
- RSI.
- MACD.
- SMA.
- EMA.
- Bollinger Bands.
- ATR.
- Other supported indicators.

Indicator calculations must define warm-up periods and missing-data behavior.

# 8. Market Scanner Data Flow

The Market Scanner processes a market universe rather than only assets held in a user's portfolio.

## 8.1 Scanner Pipeline

```text
Market Universe
      |
      v
Asset Eligibility Check
      |
      v
Market Data Availability
      |
      v
Data Validation
      |
      v
Feature Calculation
      |
      v
Screening Rules
      |
      v
Result Ranking
      |
      v
Scanner Result Storage
      |
      v
Scanner API
      |
      v
Frontend Scanner
```

## 8.2 Scanner Processing Categories

Initial categories:

| Category | Purpose |
|---|---|
| Technical | Indicator-based screening |
| Momentum | Price momentum evaluation |
| Volume | Trading activity analysis |
| Volatility | Volatility-based screening |
| Fundamental | Fundamental metrics where available |
| Market Trend | Trend and regime screening |
| Anomaly | Unusual market behavior detection |
| Correlation | Relationship-based screening |

Each category should have independently defined screening criteria.

## 8.3 Scanner Scheduling

Scanning frequency should depend on the type of analysis.

Examples:

- Technical indicators: after relevant candle updates or scheduled intervals.
- Momentum: based on the selected observation interval.
- Volume: updated according to available market data.
- Fundamental: updated when new fundamental data becomes available.
- Correlation: recalculated periodically or on demand.

The scanner should avoid recalculating expensive metrics unnecessarily.

## 8.4 Scanner Output

A scanner result should include:

- Asset identifier.
- Symbol.
- Market.
- Scanner category.
- Matched conditions.
- Relevant calculated metrics.
- Ranking or score where defined.
- Calculation timestamp.
- Source data timestamp.
- Data freshness status.

Scanner results must be distinguishable from investment recommendations.

# 9. AI Research Data Flow

AI Research consumes structured application information and external research context where available.

It must not independently invent financial data.

## 9.1 Research Pipeline

```text
User Research Request
         |
         v
Research API
         |
         v
Research Service
         |
         v
Context Builder
         |
         +-----------------------+
         |                       |
         v                       v
Portfolio / Analytics       External Research
         |                       |
         +-----------+-----------+
                     |
                     v
              Context Validation
                     |
                     v
                LLM Provider
                     |
                     v
             Generated Response
                     |
                     v
              Output Validation
                     |
                     v
              Research Report
                     |
                     v
                  Frontend
```

## 9.2 Context Sources

AI Research may consume:

- Portfolio summaries.
- Risk metrics.
- Technical analysis results.
- Market regime information.
- Market data metadata.
- Fundamental information.
- News and research sources.

Only information actually available to the application should be included.

## 9.3 AI Data Boundaries

The context builder must identify:

- Data source.
- Data timestamp.
- Data freshness.
- Missing information.
- Calculation methodology where relevant.

AI output should distinguish factual inputs from generated interpretation.

Sensitive portfolio data must only be included when authorized by the user and necessary for the requested research operation.

## 9.4 Research Output

Research output may contain:

- Executive summary.
- Relevant market context.
- Quantitative findings.
- Risk observations.
- Supporting information.
- Limitations and uncertainties.
- Source references where available.

AI research must not execute trades or modify portfolio transactions.

# 10. Frontend Data Flow

The frontend receives information from the backend through REST and WebSocket.

## 10.1 REST Data Flow

REST is used for request-response operations.

Examples:
- Retrieving portfolio information.
- Loading historical candles.
- Retrieving holdings.
- Requesting analytical results.
- Loading scanner results.
- Retrieving research reports.

## 10.2 WebSocket Data Flow

WebSocket is used for supported streaming updates.

Examples:
- Market price updates.
- Candle updates.
- Portfolio valuation updates.
- Scanner notifications.

The frontend should subscribe only to relevant data channels and release subscriptions when they are no longer needed.

## 10.3 Frontend State Management

Frontend state should distinguish:

- Server data.
- Local UI state.
- Streaming data.
- Cached data.
- Loading and error states.

The frontend must handle:
- Initial loading.
- Empty results.
- API errors.
- Disconnected WebSocket.
- Reconnection.
- Stale information.
- Out-of-order updates.

The frontend should not assume that a successful WebSocket connection guarantees fresh market data.

# 11. Data Quality Management

Data quality is essential because analytical outputs depend on the quality of their inputs.

## 11.1 Quality Dimensions

| Dimension | Description |
|---|---|
| Accuracy | Values represent the supplied source data correctly |
| Completeness | Required fields and observations are available |
| Consistency | Data follows standardized formats |
| Timeliness | Data is sufficiently recent for its intended use |
| Uniqueness | Duplicate records are appropriately handled |
| Validity | Data conforms to defined rules |

## 11.2 Data Quality Status

Possible quality statuses:

- VALID.
- WARNING.
- INVALID.
- INCOMPLETE.
- STALE.
- UNAVAILABLE.

The system should retain relevant quality metadata for downstream processing.

## 11.3 Error Handling

Different errors require different handling strategies.

| Error | Handling |
|---|---|
| Provider unavailable | Retry according to policy and report status |
| Rate limit exceeded | Apply backoff and subscription control |
| Invalid response | Reject or quarantine data |
| Missing observations | Flag incomplete data |
| Duplicate records | Apply deduplication rules |
| Stale data | Mark freshness status |
| Database failure | Report failure and apply recovery policy |
| Calculation failure | Record error and avoid presenting invalid results |

# 12. Caching and Data Reuse

Caching may be introduced to reduce repeated requests and improve application responsiveness.

Potential cached data:

- Latest market prices.
- Active candle state.
- Frequently requested market metadata.
- Recent scanner results.
- Frequently accessed analytical results.

Redis may be used when justified by workload and concurrency requirements.

Caching rules:
- Define expiration policies.
- Avoid treating cached data as automatically fresh.
- Include source timestamps.
- Invalidate or refresh data appropriately.
- Do not use cache as the only authoritative record for important portfolio transactions.

# 13. Data Consistency and Processing Rules

PIMS must maintain consistency across its data pipelines.

Important rules:

1. Normalize market data before analytical consumption.
2. Preserve provider source information.
3. Preserve original event timestamps.
4. Prevent stale updates from overwriting newer valid data.
5. Keep transaction records auditable.
6. Ensure portfolio changes are applied consistently.
7. Separate calculated outputs from raw market data.
8. Validate analytical inputs before calculation.
9. Identify missing and incomplete data.
10. Track the timestamp and methodology of analytical results.

Where processing is asynchronous, the system must define retry, deduplication, and failure-recovery behavior.

# 14. Data Lifecycle

The general data lifecycle is:

```text
ACQUISITION
     |
     v
INGESTION
     |
     v
NORMALIZATION
     |
     v
VALIDATION
     |
     v
PROCESSING
     |
     v
PERSISTENCE
     |
     v
DISTRIBUTION
     |
     v
ANALYSIS
     |
     v
PRESENTATION
```

Not every data category follows exactly the same sequence.

For example:
- Historical market data may be retrieved on demand.
- Live market data may be streamed continuously.
- Portfolio data originates from user operations.
- Analytical results may be calculated periodically or on demand.
- AI research is generally request-driven.

# 15. Data Flow Implementation Priorities

Recommended implementation order:

| Phase | Data Flow Component |
|---|---|
| 1 | Database connectivity and core data contracts |
| 2 | Asset identity and reference data |
| 3 | Historical market data ingestion |
| 4 | Market data normalization and validation |
| 5 | Historical data storage and retrieval |
| 6 | Centralized WebSocket market data pipeline |
| 7 | Frontend market data integration |
| 8 | Portfolio and transaction data flow |
| 9 | Portfolio valuation and performance |
| 10 | Risk and technical analytics |
| 11 | Market Scanner pipeline |
| 12 | AI Research context pipeline |

Each stage must have defined acceptance criteria and tests.

# 16. Relationship with Other Documents

| Document | Purpose |
|---|---|
| `AGENTS.md` | Development rules |
| `docs/architecture/system-architecture.md` | Overall system architecture |
| `docs/architecture/application-architecture.md` | Internal application structure |
| `docs/architecture/engine-architecture.md` | Analytics engine design |
| `docs/database/database-design.md` | Database design |
| `specifications/data/market-data-spec.md` | Market data requirements |
| `specifications/data/provider-integration-spec.md` | Provider integration requirements |
| `specifications/data/normalization-spec.md` | Normalization requirements |
| `specifications/backend/websocket-spec.md` | WebSocket event contracts |
| `specifications/engines/` | Individual engine requirements |

# 17. Final Principle

All data flowing through PIMS must have a clear origin, defined processing path, validated structure, and identifiable status.

The system must distinguish raw data, normalized data, calculated results, and AI-generated interpretation.

Reliable data flow is the foundation of reliable portfolio management and quantitative analysis.

**PIMS must prioritize data integrity and analytical correctness before expanding the number of features.**