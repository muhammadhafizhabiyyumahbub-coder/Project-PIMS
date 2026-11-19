# Personal Investment Management System (PIMS)

**A Personal Investment Management and Quantitative Analysis Platform**

PIMS is a personal investment management system designed to monitor, organize, and analyze multiple investment portfolios across different financial markets.

The platform combines portfolio management, market data visualization, quantitative analytics, risk monitoring, market scanning, and AI-assisted financial research into a unified dashboard.

The primary objective is to provide a structured environment for understanding portfolio performance, analyzing market conditions, evaluating risk, and supporting informed investment decisions.

> **Project Status:** V1 Release Candidate — not yet released.
>
> See [docs/RELEASE_NOTES_V1.md](docs/RELEASE_NOTES_V1.md) for what exists,
> [docs/RELEASE_KNOWN_ISSUES.md](docs/RELEASE_KNOWN_ISSUES.md) for open issues,
> and [docs/user/PANDUAN_PENGGUNA.md](docs/user/PANDUAN_PENGGUNA.md) for the
> Indonesian user guide.

---

## 1. Project Overview

Personal Investment Management System (PIMS) is designed as a centralized financial analysis platform.

Instead of managing investment information across multiple disconnected applications, PIMS aims to provide a unified environment for:

- Monitoring multiple portfolios.
- Tracking assets across different markets.
- Visualizing market prices and historical performance.
- Evaluating portfolio performance and risk.
- Analyzing asset allocation and correlation.
- Scanning financial markets for potential analytical opportunities.
- Generating AI-assisted research and analytical reports.

PIMS is intended for personal investment management and research. It is not a brokerage platform and does not execute trades.

## 2. Supported Markets

The initial development scope includes three market categories:

| Market | Initial Data Provider |
|---|---|
| Cryptocurrency | Bybit |
| US Stocks | Finnhub / Alpaca |
| Indonesian Stocks (IDX) | Provider to be evaluated |

Market data availability, update frequency, licensing, and API limitations depend on each provider.

The system will distinguish real-time, delayed, and historical data rather than presenting all market information as real-time.

## 3. Core Features

### Portfolio Management
- Multiple independent portfolios.
- Portfolio holdings management.
- Transaction records.
- Portfolio valuation.
- Cash and invested capital monitoring.

### Market Data & Visualization
- Market price monitoring.
- Historical OHLCV data.
- Interactive financial charts.
- Market selection across supported asset classes.
- Real-time updates where supported by the data provider.

### Quantitative Analysis
- Technical indicators.
- Portfolio performance analysis.
- Risk metrics.
- Asset allocation analysis.
- Correlation analysis.
- Market regime analysis.

### Market Scanner
- Technical screening.
- Momentum screening.
- Volume analysis.
- Volatility screening.
- Market trend detection.
- Fundamental screening where data is available.

### AI Research
- Financial research assistance.
- Market information summaries.
- Analytical report generation.
- Interpretation of quantitative analysis.
- Research context based on available market and portfolio data.

AI-generated analysis is intended to assist research and interpretation. Financial calculations and quantitative metrics must be produced by deterministic application logic.

## 4. Technology Stack

| Layer | Technology |
|---|---|
| Frontend Framework | Next.js |
| UI Library | React |
| Programming Language | TypeScript |
| Styling | Tailwind CSS |
| Charting | TradingView Lightweight Charts |
| Backend Framework | Python / FastAPI |
| Data Validation | Pydantic |
| Database | PostgreSQL |
| Cache / Messaging | Redis (optional, as needed) |
| Data Analysis | Pandas, NumPy, SciPy |
| Containerization | Docker |
| AI Integration | LLM API |

Technology choices may evolve through documented architecture decisions.

## 5. System Architecture

PIMS follows a **Monorepo + Modular Monolith** architecture.

The system is divided into several major layers:

1. **Frontend Layer** — Dashboard, charts, portfolio interfaces, and analytical visualizations.
2. **Backend Layer** — API services, business logic, and application orchestration.
3. **Market Data Layer** — Provider integrations, ingestion, normalization, validation, and storage.
4. **Analytics Layer** — Portfolio, technical, risk, allocation, correlation, and scanner engines.
5. **AI Research Layer** — AI-assisted interpretation and research reports.
6. **Database Layer** — Persistent storage for portfolios, transactions, market data, and analytical records.

### High-Level Data Flow

```text
Market Data Providers
        |
        v
Provider Adapters
        |
        v
Data Normalization
        |
        v
Data Validation
        |
        v
Storage and Cache
        |
        v
Backend Services
        |
        +------------------+
        |                  |
        v                  v
Analytics Engines     AI Research
        |                  |
        +--------+---------+
                 |
                 v
             Frontend
                 |
                 v
          PIMS Dashboard
```

For more detailed architecture documentation, see `docs/architecture/`.

## 6. Repository Structure

```text
personal-investment-management-system/
│
├── AGENTS.md
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── docs/
│   ├── architecture/
│   ├── database/
│   ├── decisions/
│   └── diagrams/
│
├── specifications/
│   ├── project/
│   ├── frontend/
│   ├── backend/
│   ├── data/
│   ├── engines/
│   ├── database/
│   ├── security/
│   └── testing/
│
├── design-reference/
│   └── dashboard/
│
├── frontend/
│
├── backend/
│
├── infrastructure/
│
├── tests/
│
└── scripts/
```

Some directories and modules may be introduced gradually as development progresses.

## 7. Documentation

Project documentation is separated by responsibility.

| Location | Purpose |
|---|---|
| `AGENTS.md` | Instructions and development rules for AI coding agents |
| `docs/architecture/` | System and application architecture |
| `docs/database/` | Database design documentation |
| `docs/decisions/` | Technical architecture decisions |
| `docs/diagrams/` | System and data flow diagrams |
| `docs/user/` | User-facing guides (Indonesian) |
| `docs/RELEASE_NOTES_V1.md` | V1 release-candidate feature summary |
| `docs/RELEASE_KNOWN_ISSUES.md` | Open issues and V1 limitations |
| `specifications/` | Detailed functional and technical requirements |
| `design-reference/` | UI and design references |

Before implementing a feature, review the relevant specifications and architecture documents.

## 8. Development Principles

The development of PIMS follows these principles:

- **Modular Architecture:** Keep application responsibilities separated into clear modules.
- **Data Integrity:** Validate and normalize market data before analytical processing.
- **Analytical Accuracy:** Perform financial calculations through deterministic logic.
- **Provider Independence:** Avoid coupling core application logic to a single market data provider.
- **Security:** Protect API credentials, configuration, and sensitive portfolio information.
- **Maintainability:** Prefer readable, testable, and reusable components.
- **Scalability:** Build a solid modular foundation before introducing distributed services.
- **Transparency:** Clearly communicate data source, timestamp, freshness, and limitations.

## 9. Development Roadmap

Development is planned in progressive stages.

| Phase | Focus |
|---|---|
| Phase 1 | Project foundation and architecture |
| Phase 2 | Frontend dashboard foundation |
| Phase 3 | Market data integration |
| Phase 4 | Interactive charting |
| Phase 5 | Portfolio management |
| Phase 6 | Quantitative analytics |
| Phase 7 | Market Scanner |
| Phase 8 | AI Research integration |
| Phase 9 | Testing, optimization, and refinement |

The roadmap is subject to refinement as requirements are validated.

## 10. Getting Started

The application setup instructions will be finalized as the initial frontend and backend foundations are implemented.

Expected development prerequisites:

- Node.js
- Python
- PostgreSQL
- Docker
- Git

Once the initial application setup is available, this section should include the exact installation, environment configuration, database initialization, and development commands.

Do not assume that placeholder commands are executable before they are verified against the actual project configuration.

## 11. Important Notes

- PIMS is at V1 release-candidate stage and has not been released.
- Market data availability depends on external providers and their licensing conditions.
- Not all market data sources guarantee real-time updates.
- Mock data must never be represented as actual market data.
- AI-generated research should not be treated as independently verified financial fact.
- The application does not execute trades.

## 12. License

License information will be defined in the root `LICENSE` file.

---

**Personal Investment Management System (PIMS)**

*Building a structured environment for portfolio management, quantitative analysis, and financial research.*