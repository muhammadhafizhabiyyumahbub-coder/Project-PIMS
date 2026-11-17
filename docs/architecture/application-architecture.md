# Application Architecture

**Personal Investment Management System (PIMS)**

| Document Information | Value |
|---|---|
| Document | Application Architecture |
| Version | 1.0 |
| Status | Architecture Specification |
| Architecture Style | Modular Monolith |
| Repository Structure | Monorepo |
| Frontend | Next.js, React, TypeScript |
| Backend | Python, FastAPI |
| Database | PostgreSQL |

---

# 1. Purpose

This document defines the internal application architecture of the Personal Investment Management System (PIMS).

It describes how the application is organized into modules, how responsibilities are separated, how components communicate, and how dependencies are managed.

The purpose is to establish a maintainable application structure that supports the development of portfolio management, market data processing, quantitative analytics, market scanning, and AI-assisted financial research.

This document focuses on application-level architecture rather than infrastructure deployment or external system integration details.

# 2. Architectural Approach

## 2.1 Modular Monolith

PIMS will use a Modular Monolith architecture.

The application will initially operate as a unified backend application while maintaining clearly separated internal modules.

Each module has:
- A defined responsibility.
- Its own business logic.
- Explicit input and output contracts.
- Controlled access to other modules.
- Independent testing boundaries.

Modules must not directly depend on the internal implementation details of unrelated modules.

The Modular Monolith approach is selected to reduce initial infrastructure complexity while preserving the ability to expand the application in the future.

## 2.2 Architecture Principles

The application must follow these principles:

1. **Separation of Concerns** — Each component must have a clearly defined responsibility.
2. **Single Responsibility** — A module should focus on one major business domain.
3. **Explicit Dependencies** — Dependencies between modules must be clear and controlled.
4. **Provider Independence** — Business logic must not depend directly on external provider implementations.
5. **Deterministic Analytics** — Financial calculations must be performed by deterministic application logic.
6. **Data Integrity** — Data must be validated before entering analytical processing.
7. **Loose Coupling** — Modules should communicate through defined interfaces or application services.
8. **Testability** — Business logic must be testable independently of external services.
9. **Incremental Development** — Only necessary modules should be implemented in each development phase.

# 3. Application Layer Structure

PIMS is organized into six major application layers.

```text
PIMS APPLICATION
│
├── 1. Presentation Layer
│
├── 2. API and Application Layer
│
├── 3. Domain and Business Logic Layer
│
├── 4. Data Processing Layer
│
├── 5. Intelligence Layer
│
└── 6. Persistence Layer
```

## 3.1 Presentation Layer

Responsible for displaying information and receiving user interactions.

Technology:
- Next.js
- React
- TypeScript
- Tailwind CSS
- TradingView Lightweight Charts

Main responsibilities:
- Dashboard rendering.
- Portfolio visualization.
- Market data visualization.
- Analytical reports.
- User navigation.
- Search and filtering.
- Data presentation.
- Real-time interface updates.

The frontend must not independently calculate authoritative portfolio performance, risk metrics, or other financial results.

It may perform lightweight presentation calculations, such as formatting values and displaying visual states.

## 3.2 API and Application Layer

Responsible for receiving requests and coordinating application operations.

Technology:
- FastAPI
- Pydantic

Responsibilities:
- REST API endpoints.
- WebSocket endpoints.
- Request validation.
- Authentication and authorization integration.
- Application service orchestration.
- Response formatting.
- Error handling.

The API layer must not contain complex financial calculations or direct database business logic.

Requests should be delegated to the appropriate application services.

## 3.3 Domain and Business Logic Layer

Contains the primary business rules of PIMS.

Main domains:
- Portfolio Management.
- Holdings Management.
- Transaction Management.
- Asset Management.
- Watchlist Management.
- Market Analysis.
- Portfolio Performance.

Responsibilities:
- Portfolio rules.
- Transaction processing rules.
- Holdings calculations.
- Portfolio valuation logic.
- Business validation.
- Domain-level consistency.

Business logic should remain independent of frontend frameworks and external market data providers.

## 3.4 Data Processing Layer

Responsible for acquiring, processing, validating, and standardizing market information.

Main modules:
- Provider Adapters.
- Market Data Ingestion.
- Data Normalization.
- Data Validation.
- Data Aggregation.
- Market Data Storage.

Responsibilities:
- Fetching historical data.
- Receiving market data streams.
- Standardizing symbols and timestamps.
- Normalizing currencies and market identifiers.
- Validating incoming data.
- Aggregating OHLCV data when required.
- Managing provider-specific limitations.

External provider implementations must be isolated from the rest of the application.

## 3.5 Intelligence Layer

Contains analytical and research capabilities.

It consists of two major subsystems.

**A. Quantitative Analytics**

Responsible for deterministic financial calculations and analytical models.

**B. AI Research**

Responsible for interpreting available information, generating summaries, and assisting research workflows.

AI must not replace deterministic financial calculations.

## 3.6 Persistence Layer

Responsible for storing and retrieving application data.

Primary technology:
- PostgreSQL.

Potential future technology:
- Redis for caching and transient real-time state.
- TimescaleDB for time-series workloads if justified.

Responsibilities:
- Portfolio persistence.
- Holdings persistence.
- Transaction records.
- Market data storage.
- Analytical result storage.
- User preferences.
- Research records.

Database access should be managed through repositories or controlled data-access services.

# 4. Frontend Architecture

## 4.1 Frontend Structure

The frontend follows a feature-oriented architecture.

Suggested structure:

```text
frontend/
└── src/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   ├── markets/
    │   ├── scanner/
    │   ├── portfolios/
    │   ├── holdings/
    │   ├── performance/
    │   ├── risk/
    │   ├── allocation/
    │   ├── correlation/
    │   ├── research/
    │   └── settings/
    │
    ├── components/
    │   ├── ui/
    │   ├── layout/
    │   ├── charts/
    │   └── common/
    │
    ├── features/
    │   ├── dashboard/
    │   ├── markets/
    │   ├── scanner/
    │   ├── portfolios/
    │   ├── holdings/
    │   ├── transactions/
    │   ├── performance/
    │   ├── risk/
    │   ├── allocation/
    │   ├── correlation/
    │   ├── watchlist/
    │   └── research/
    │
    ├── hooks/
    ├── services/
    ├── stores/
    ├── types/
    ├── utils/
    └── config/
```

This structure is a logical organization guideline. Actual directories should be created when their functionality is implemented.

## 4.2 Frontend Responsibilities

The frontend is responsible for:

- Rendering user interfaces.
- Managing local UI state.
- Managing user interactions.
- Requesting data from backend APIs.
- Subscribing to WebSocket updates.
- Formatting and displaying financial information.
- Rendering charts and analytical visualizations.

The frontend must not:
- Connect directly to private market data provider credentials.
- Implement authoritative portfolio accounting.
- Independently calculate official risk metrics.
- Store sensitive API credentials in client-side code.
- Treat sample data as actual market data.

## 4.3 Feature-Based Organization

Each major feature should contain its own components, hooks, types, and service logic when appropriate.

For example:

```text
features/
└── portfolios/
    ├── components/
    ├── hooks/
    ├── services/
    ├── types/
    └── utils/
```

This prevents the frontend from becoming a collection of unrelated components with unclear responsibilities.

## 4.4 Chart Architecture

The chart subsystem must be independent from the market data provider.

Its responsibilities include:
- Rendering historical OHLCV data.
- Displaying price updates.
- Handling chart interactions.
- Managing visible time ranges.
- Displaying volume and supported indicators.
- Managing chart lifecycle.

TradingView Lightweight Charts will be used as the initial chart rendering library.

The chart component receives normalized data through frontend services or state management.

It must not implement provider-specific API connections.

# 5. Backend Architecture

## 5.1 Backend Structure

The backend follows a modular structure organized around business domains and application responsibilities.

Suggested structure:

```text
backend/
└── app/
    ├── api/
    │   ├── rest/
    │   └── websocket/
    │
    ├── core/
    │   ├── exceptions/
    │   ├── logging/
    │   └── security/
    │
    ├── config/
    │
    ├── domain/
    │   ├── portfolios/
    │   ├── holdings/
    │   ├── transactions/
    │   ├── assets/
    │   └── watchlists/
    │
    ├── application/
    │   ├── services/
    │   ├── interfaces/
    │   └── dto/
    │
    ├── data/
    │   ├── providers/
    │   ├── ingestion/
    │   ├── normalization/
    │   ├── validation/
    │   ├── aggregation/
    │   └── storage/
    │
    ├── engines/
    │   ├── technical/
    │   ├── scanner/
    │   ├── portfolio/
    │   ├── risk/
    │   ├── allocation/
    │   ├── correlation/
    │   ├── market_regime/
    │   ├── fundamental/
    │   ├── sentiment/
    │   ├── macro/
    │   ├── factor/
    │   ├── attribution/
    │   ├── backtesting/
    │   └── scenario/
    │
    ├── ai/
    │   ├── providers/
    │   ├── research/
    │   ├── context_builder/
    │   └── report_generator/
    │
    ├── database/
    │   ├── models/
    │   ├── repositories/
    │   └── migrations/
    │
    └── schemas/
```

The structure represents logical boundaries. It does not require every module to be implemented immediately.

## 5.2 API Module

The API module provides external access to application capabilities.

Two communication mechanisms are used:

**REST API**
- Portfolio operations.
- Holdings queries.
- Transaction records.
- Historical market data.
- Scanner results.
- Analytical reports.
- User settings.

**WebSocket**
- Live market updates.
- Streaming candle updates.
- Real-time portfolio valuation updates where appropriate.
- Scanner notifications.
- Other supported live application events.

API endpoints should delegate operations to application services rather than directly implementing domain logic.

## 5.3 Application Services

Application services coordinate operations across domain modules, data services, and analytical engines.

Examples:

| Service | Responsibility |
|---|---|
| Portfolio Service | Coordinate portfolio operations |
| Market Data Service | Provide normalized market data |
| Scanner Service | Coordinate market scanning |
| Analytics Service | Coordinate analytical calculations |
| Research Service | Prepare research requests |
| Reporting Service | Assemble analytical reports |

Application services should orchestrate existing modules rather than duplicate their business logic.

# 6. Domain Modules

## 6.1 Portfolio Management

Responsible for managing multiple portfolios.

Core responsibilities:
- Portfolio creation and updates.
- Portfolio configuration.
- Portfolio-level currency.
- Portfolio valuation.
- Portfolio ownership boundaries.

A portfolio must be logically isolated from other portfolios.

## 6.2 Holdings Management

Responsible for tracking assets held in a portfolio.

Responsibilities:
- Asset quantity.
- Average cost.
- Current valuation.
- Unrealized profit and loss.
- Asset allocation contribution.

Holdings should be consistent with the underlying transaction records and the selected accounting rules.

## 6.3 Transaction Management

Responsible for recording portfolio activities.

Initial transaction categories may include:
- Buy.
- Sell.
- Deposit.
- Withdrawal.
- Fee.
- Dividend.
- Other supported adjustments.

Transaction records should be auditable.

Historical records should not be silently overwritten when a correction is required. Corrections should follow a controlled adjustment or reversal process.

## 6.4 Asset Management

Responsible for maintaining a standardized asset identity.

An asset should contain sufficient identifiers to distinguish:
- Asset symbol.
- Asset name.
- Market.
- Asset class.
- Currency.
- Provider-specific identifiers.

Provider symbols must not be treated as globally unique identifiers.

# 7. Market Data Architecture

## 7.1 Provider Adapter

Each external data provider must have an isolated adapter.

Initial provider categories:

```text
providers/
├── crypto/
├── us_stocks/
└── indonesia/
```

The adapter translates provider-specific responses into the internal market data format.

Business logic must consume normalized data instead of provider-specific response structures.

## 7.2 Normalization

The normalization module standardizes:

- Symbol identifiers.
- Asset identifiers.
- Market identifiers.
- Currency.
- Timestamp.
- Timezone.
- OHLCV values.
- Data interval.
- Provider metadata.

The application should preserve source and timestamp information for traceability.

## 7.3 Validation

Incoming data should be checked for:

- Missing required fields.
- Invalid timestamps.
- Duplicate records.
- Invalid numeric values.
- Incorrect OHLC relationships.
- Unexpected data intervals.
- Stale or delayed data.

Invalid data must not silently enter authoritative analytical calculations.

## 7.4 Aggregation

Aggregation is used when the upstream provider supplies trades or ticks rather than completed candles.

For OHLCV aggregation:

- Open: first trade price.
- High: maximum trade price.
- Low: minimum trade price.
- Close: latest trade price.
- Volume: accumulated volume.

If the provider already supplies valid candle data, unnecessary re-aggregation should be avoided.

# 8. Analytics Engine Architecture

Each analytical engine has a defined responsibility and should expose a consistent interface to the application.

## 8.1 Initial Engines

| Engine | Primary Responsibility |
|---|---|
| Portfolio Performance | Return, P&L, and performance metrics |
| Risk Analysis | Volatility, drawdown, and risk metrics |
| Asset Allocation | Portfolio exposure and allocation |
| Technical Analysis | Technical indicators |
| Correlation Analysis | Relationships between assets |
| Market Regime | Market condition classification |
| Market Scanner | Screening and ranking of market instruments |

## 8.2 Future Engines

The following engines are planned for later development:

- Fundamental Analysis.
- Sentiment Analysis.
- Macro Analysis.
- Factor Analysis.
- Attribution Analysis.
- Backtesting.
- Scenario Analysis.
- Stress Testing.
- Liquidity Analysis.
- Tax and Fee Analysis.

These engines must not be implemented merely to populate the directory structure.

They should be introduced when their data requirements, calculation definitions, and use cases are sufficiently specified.

## 8.3 Engine Contract

Every analytical engine should define:

1. Input requirements.
2. Output schema.
3. Calculation or processing rules.
4. Data dependencies.
5. Validation requirements.
6. Error handling.
7. Unit tests.

Example conceptual interface:

```text
Input Data
    |
    v
Validation
    |
    v
Engine Processing
    |
    v
Result Validation
    |
    v
Structured Analytical Output
```

Analytical engines should be independently testable.

## 8.4 Engine Independence

An engine should not directly access another engine's private implementation.

If one engine requires another engine's result, it should consume a defined output contract or use application-level orchestration.

For example:

- Risk Analysis may consume portfolio return series.
- Allocation Analysis may consume portfolio holdings and market values.
- Market Scanner may consume normalized market data and technical indicator outputs.

This keeps dependencies explicit and prevents circular module relationships.

# 9. Market Scanner Architecture

The Market Scanner is a separate analytical subsystem.

It must not be implemented merely as a frontend filtering feature.

Its responsibilities include:
- Defining the scan universe.
- Obtaining eligible market data.
- Applying screening criteria.
- Calculating relevant metrics.
- Evaluating screening conditions.
- Ranking matching instruments.
- Producing structured scanner results.

Conceptual processing:

```text
Market Universe
      |
      v
Data Availability Check
      |
      v
Scanner Processing
      |
      v
Screening Rules
      |
      v
Ranking
      |
      v
Scanner Results
      |
      v
Frontend Visualization
```

The scanner should use centralized market data services rather than creating separate provider connections for every instrument.

Scanning frequency must depend on the metric being evaluated and the available data interval.

# 10. AI Research Architecture

The AI Research subsystem is responsible for research assistance and interpretation.

Main components:

**AI Provider**
- Handles communication with an external LLM API.

**Context Builder**
- Collects relevant structured information.
- Prepares portfolio and market context.
- Applies data availability and freshness checks.

**Research Module**
- Coordinates research requests.
- Produces structured analytical context.

**Report Generator**
- Generates research summaries and reports.

## 10.1 AI Boundaries

AI must not:
- Invent market prices or financial metrics.
- Replace deterministic financial calculations.
- Present unavailable information as verified fact.
- Execute investment transactions.
- Access private provider credentials through frontend code.

AI should distinguish between:
- Verified application data.
- External research information.
- Model-generated interpretation.
- Missing or unavailable information.

AI-generated conclusions should include relevant data context and limitations.

# 11. Inter-Module Communication

Modules should communicate through explicit interfaces and application services.

Preferred communication:

- Function calls for internal synchronous operations.
- Application service orchestration for multi-module workflows.
- REST for frontend-to-backend requests.
- WebSocket for supported streaming updates.
- Database repositories for controlled persistence.

Avoid:
- Direct access to another module's private database models.
- Circular imports.
- Shared global mutable state.
- Duplicated business rules.
- Direct provider calls from domain modules.

## 11.1 Dependency Direction

The preferred dependency direction is:

```text
Presentation
     |
     v
API Layer
     |
     v
Application Services
     |
     v
Domain and Analytics Modules
     |
     v
Interfaces / Repositories
     |
     v
External Providers and Persistence
```

The dependency structure should ensure that core business rules do not depend on frontend frameworks or provider-specific SDKs.

# 12. Data Ownership and Persistence

Each domain module should have clearly defined ownership of its data.

| Data Category | Logical Owner |
|---|---|
| Portfolio | Portfolio Domain |
| Holdings | Holdings Domain |
| Transactions | Transaction Domain |
| Asset Identity | Asset Domain |
| Market Data | Market Data Module |
| Scanner Results | Scanner Module |
| Analytical Results | Relevant Analytics Engine |
| Research Reports | AI Research Module |
| User Preferences | User / Settings Domain |

Modules may share data through defined interfaces and repositories.

A shared PostgreSQL database does not mean unrestricted access to every table from every module.

Data ownership and transaction boundaries should be explicit.

# 13. Real-Time Application Processing

Real-time processing should be centralized.

Conceptual flow:

```text
Market Data Provider
        |
        v
Provider Connection
        |
        v
Normalization and Validation
        |
        v
Market Data Service
        |
        +----------------------+
        |                      |
        v                      v
Market Data Storage      WebSocket Publisher
                               |
                               v
                         Frontend Clients
```

The backend should manage provider connections and distribute updates to subscribed frontend clients.

The frontend must not establish an independent market data provider connection for every chart or dashboard component.

Update frequency should depend on:
- Provider capabilities.
- Subscription requirements.
- Market session.
- Data interval.
- Rate limits.
- System capacity.

# 14. Error Handling and Observability

All major application modules should follow consistent error-handling and logging conventions.

Important error categories:

- Provider connection errors.
- Data validation errors.
- Database errors.
- API request errors.
- Analytical calculation errors.
- WebSocket connection errors.
- AI provider errors.

Logs should include useful contextual information without exposing secrets or sensitive portfolio information.

Important operational information includes:
- Provider availability.
- Last successful data update.
- Data freshness.
- Processing failures.
- API errors.
- Engine execution status.

The application must distinguish between missing data, stale data, invalid data, and calculation failures.

# 15. Security Boundaries

Security must be applied across all application layers.

Requirements:

- Store secrets in environment variables or an appropriate secret-management mechanism.
- Never expose provider credentials to the browser.
- Validate and authorize sensitive API operations.
- Apply portfolio-level access controls.
- Validate incoming user input.
- Avoid logging credentials and sensitive information.
- Protect database connections.
- Apply secure WebSocket connection handling.

Security controls must be designed before exposing the application beyond its local development environment.

# 16. Testing Architecture

Testing should follow the application boundaries.

| Test Type | Target |
|---|---|
| Unit Tests | Business logic and analytical calculations |
| Integration Tests | Database, repositories, and provider adapters |
| API Tests | REST endpoints |
| WebSocket Tests | Streaming and connection behavior |
| Engine Tests | Analytical input/output correctness |
| Frontend Tests | Components and user interactions |
| End-to-End Tests | Complete application workflows |

Financial calculations should include test cases for:
- Normal inputs.
- Boundary values.
- Missing data.
- Invalid data.
- Zero values.
- Negative values where applicable.
- Precision and rounding behavior.

Tests should verify correctness rather than merely successful execution.

# 17. Implementation Strategy

The application should be developed incrementally.

Recommended implementation sequence:

| Phase | Application Components |
|---|---|
| 1 | Project foundation, configuration, and core structure |
| 2 | Frontend layout and dashboard foundation |
| 3 | Backend API foundation and database connectivity |
| 4 | Asset and market data foundation |
| 5 | Provider adapters and normalized market data |
| 6 | Chart integration |
| 7 | Portfolio, holdings, and transaction modules |
| 8 | Portfolio performance and risk engines |
| 9 | Allocation, correlation, and technical analysis |
| 10 | Market Scanner |
| 11 | AI Research |
| 12 | Advanced analytics and optimization |

Each phase should be tested and reviewed before expanding into the next major subsystem.

# 18. Architectural Constraints

The following constraints must be maintained:

1. PIMS remains a Modular Monolith during the initial development stages.
2. Do not introduce microservices without an approved architectural decision.
3. Do not allow frontend components to own authoritative financial calculations.
4. Do not couple analytical engines to external provider implementations.
5. Do not allow direct provider connections from frontend components.
6. Do not duplicate market data ingestion across modules.
7. Do not implement unnecessary engines before their requirements are defined.
8. Do not use AI-generated numbers as authoritative financial calculations.
9. Do not introduce new infrastructure without a documented justification.
10. Changes to core module boundaries require architectural review.

# 19. Relationship with Other Documents

This document should be read together with:

| Document | Purpose |
|---|---|
| `AGENTS.md` | Development instructions and coding-agent rules |
| `docs/architecture/system-architecture.md` | Overall system architecture |
| `docs/architecture/data-flow.md` | Data movement and processing |
| `docs/architecture/engine-architecture.md` | Analytical engine design |
| `docs/database/database-design.md` | Database structure |
| `specifications/frontend/frontend-spec.md` | Frontend requirements |
| `specifications/backend/backend-spec.md` | Backend requirements |
| `specifications/data/market-data-spec.md` | Market data requirements |
| `specifications/engines/` | Individual analytical engine specifications |

# 20. Final Architectural Principle

PIMS should be built as a collection of clearly defined and independently testable modules within a unified application.

The architecture prioritizes correctness, modularity, data integrity, and maintainability over premature complexity.

The objective is not to build every feature at once, but to establish a strong application foundation that can support increasingly sophisticated portfolio management, quantitative analysis, market intelligence, and research capabilities.