import React, { useState, useMemo, useRef, useCallback, useEffect } from 'react';
import {
  LayoutDashboard,
  Globe,
  Radar,
  Eye,
  Briefcase,
  Layers,
  ArrowLeftRight,
  TrendingUp,
  ShieldAlert,
  PieChart,
  GitCompare,
  CandlestickChart,
  Sparkles,
  Newspaper,
  Settings,
  Search,
  Bell,
  ChevronDown,
  ChevronRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  SlidersHorizontal,
  Clock,
  CheckCircle2,
  FileText,
  Star,
  Info,
  X,
  Sun,
  Moon,
  Activity,
  BarChart3,
} from 'lucide-react';

// ============================================================================
// 1. STRICT TYPES & INTERFACES (Zero `any`)
// ============================================================================

export type ThemeMode = 'dark' | 'light';

export type MarketSegment = 'ALL' | 'CRYPTO' | 'US' | 'IDX';

export type PortfolioScopeId =
  | 'MASTER'
  | 'GLOBAL_EQUITY'
  | 'IDX_CORE'
  | 'DIGITAL_ALPHA';

export type TimeRange = '1D' | '1W' | '1M' | '3M' | '6M' | 'YTD' | '1Y' | 'ALL';

export type BenchmarkId = 'NONE' | 'SPX' | 'IHSG' | 'BTC' | 'BALANCED_60_40';

export type AllocationDimension = 'ASSET_CLASS' | 'MARKET' | 'TOP_ASSETS';

export type SortField =
  | 'name'
  | 'symbol'
  | 'market'
  | 'quantity'
  | 'avgCost'
  | 'currentPrice'
  | 'marketValue'
  | 'unrealizedPnL'
  | 'allocationPct';

export type SortDirection = 'asc' | 'desc';

export type NavGroupId =
  | 'main'
  | 'portfolio'
  | 'analytics'
  | 'research'
  | 'system';

export type NavRouteId =
  | 'overview'
  | 'markets'
  | 'scanner'
  | 'watchlist'
  | 'portfolios'
  | 'holdings'
  | 'transactions'
  | 'performance'
  | 'risk'
  | 'allocation'
  | 'correlation'
  | 'technical'
  | 'ai-research'
  | 'intelligence'
  | 'settings';

export interface ThemeTokens {
  mode: ThemeMode;
  canvasBg: string;
  cardBg: string;
  secondaryBg: string;
  recessedBg: string;
  hoverBg: string;
  borderDefault: string;
  borderActive: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  gainText: string;
  gainBg: string;
  gainBorder: string;
  lossText: string;
  lossBg: string;
  lossBorder: string;
  accentText: string;
  accentBg: string;
  accentBorder: string;
  chartPalette: readonly [string, string, string, string, string];
  gridLine: string;
  crosshairStroke: string;
  trackBg: string;
}

export interface NavItemConfig {
  id: NavRouteId;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

export interface NavGroupConfig {
  id: NavGroupId;
  section: string;
  icon: React.ComponentType<{ className?: string }>;
  items: NavItemConfig[];
}

export interface PortfolioProfile {
  id: PortfolioScopeId;
  name: string;
  code: string;
  mandate: string;
  marketsIncluded: Exclude<MarketSegment, 'ALL'>[];
}

export interface HoldingPosition {
  id: string;
  symbol: string;
  name: string;
  market: Exclude<MarketSegment, 'ALL'>;
  assetClass: 'Equities' | 'Index ETF' | 'Digital Assets';
  sector: string;
  quantity: number;
  avgCostUsd: number;
  currentPriceUsd: number;
  nativeCurrency: 'USD' | 'IDR';
  nativeAvgCostIdr?: number;
  nativePriceIdr?: number;
  dayChangePct: number;
  targetWeightPct: number;
  strategyTag: string;
}

export interface ComputedHolding extends HoldingPosition {
  costBasisUsd: number;
  marketValueUsd: number;
  unrealizedPnLUsd: number;
  unrealizedPnLPct: number;
  dailyPnLUsd: number;
  allocationPct: number;
  holdingsWeightPct: number;
}

export interface PortfolioSummaryMetrics {
  totalValueUsd: number;
  totalReturnUsd: number;
  totalReturnPct: number;
  dailyPnLUsd: number;
  dailyPnLPct: number;
  investedCapitalUsd: number;
  holdingsMarketValueUsd: number;
  availableCashUsd: number;
  cashWeightPct: number;
  positionCount: number;
  sparklines: {
    totalValue: number[];
    totalReturn: number[];
    dailyPnL: number[];
    investedCapital: number[];
    availableCash: number[];
  };
}

export interface ChartSeriesPoint {
  timestamp: string;
  label: string;
  portfolioValue: number;
  portfolioReturnPct: number;
  benchmarkReturnPct: Record<Exclude<BenchmarkId, 'NONE'>, number>;
}

/**
 * Decoupled data interface architected for drop-in integration with
 * TradingView Lightweight Charts (`createChart` / `ISeriesApi`).
 */
export interface LightweightChartAdapterProps {
  data: ChartSeriesPoint[];
  timeRange: TimeRange;
  benchmark: BenchmarkId;
  displayMode: 'NAV' | 'RETURN_PCT';
  portfolioLabel: string;
  marketLabel: string;
  themeTokens: ThemeTokens;
  onTimeRangeChange: (range: TimeRange) => void;
  onBenchmarkChange: (benchmark: BenchmarkId) => void;
  onDisplayModeChange: (mode: 'NAV' | 'RETURN_PCT') => void;
}

export interface AllocationSlice {
  id: string;
  label: string;
  sublabel: string;
  marketValueUsd: number;
  allocationPct: number;
  color: string;
}

export interface MarketIndexQuote {
  id: string;
  symbol: string;
  name: string;
  lastClose: string;
  changePct: number;
  breadthPct: number;
  breadthLabel: string;
}

export interface MarketRegimeGroup {
  market: Exclude<MarketSegment, 'ALL'>;
  title: string;
  regimeTag: string;
  indices: MarketIndexQuote[];
}

export interface WatchlistEntry {
  id: string;
  symbol: string;
  monogram: string;
  name: string;
  market: Exclude<MarketSegment, 'ALL'>;
  priceFormatted: string;
  secondaryPriceNote?: string;
  dailyChangePct: number;
  sparkline: number[];
  pinned: boolean;
  metrics: {
    valuationMetricLabel: string;
    valuationMetricValue: string;
    range52w: string;
    rsi14: number;
    sma50Status: 'Above 50D SMA' | 'Near 50D SMA' | 'Below 50D SMA';
    beta: string;
    analyticalNote: string;
  };
}

export type ActivityCategory =
  | 'ASSET_ADDED'
  | 'TRANSACTION_RECORDED'
  | 'ALLOCATION_REBALANCED'
  | 'WATCHLIST_UPDATED';

export interface ActivityLogEntry {
  id: string;
  category: ActivityCategory;
  title: string;
  description: string;
  portfolioTag: string;
  timestamp: string;
}

// ============================================================================
// 2. DUAL-THEME TOKEN SYSTEM (Obsidian & Slate vs Daylight Paper & Graphite)
// ============================================================================

const THEME_CONFIG: Record<ThemeMode, ThemeTokens> = {
  dark: {
    mode: 'dark',
    canvasBg: '#090B0E',
    cardBg: '#101318',
    secondaryBg: '#151921',
    recessedBg: '#151921',
    hoverBg: '#1B202B',
    borderDefault: '#1F2633',
    borderActive: '#2C3546',
    textPrimary: '#F0F3F8',
    textSecondary: '#94A0B8',
    textMuted: '#636E85',
    gainText: '#3FB950',
    gainBg: '#11261A',
    gainBorder: '#1E462D',
    lossText: '#F85149',
    lossBg: '#2A1418',
    lossBorder: '#522328',
    accentText: '#4F8FF7',
    accentBg: '#132238',
    accentBorder: '#274675',
    chartPalette: ['#4F8FF7', '#14B8A6', '#E59A3C', '#7C8B9E', '#8B5CF6'],
    gridLine: '#1F2633',
    crosshairStroke: '#384459',
    trackBg: '#1B202B',
  },
  light: {
    mode: 'light',
    canvasBg: '#F3F5F8',
    cardBg: '#FFFFFF',
    secondaryBg: '#F8FAFC',
    recessedBg: '#EEF2F7',
    hoverBg: '#F1F5F9',
    borderDefault: '#E2E8F0',
    borderActive: '#CBD5E1',
    textPrimary: '#0F172A',
    textSecondary: '#475569',
    textMuted: '#64748B',
    gainText: '#15803D',
    gainBg: '#DCFCE7',
    gainBorder: '#BBF7D0',
    lossText: '#DC2626',
    lossBg: '#FEE2E2',
    lossBorder: '#FECACA',
    accentText: '#1D4ED8',
    accentBg: '#EFF6FF',
    accentBorder: '#BFDBFE',
    chartPalette: ['#2563EB', '#0D9488', '#D97706', '#64748B', '#7C3AED'],
    gridLine: '#E2E8F0',
    crosshairStroke: '#94A3B8',
    trackBg: '#E2E8F0',
  },
};

// ============================================================================
// 3. SAMPLE MULTI-MARKET DATASET & NAVIGATION DEFINITIONS
// ============================================================================

const USD_TO_IDR_RATE = 15850;

const NAVIGATION_GROUPS: NavGroupConfig[] = [
  {
    id: 'main',
    section: 'Main',
    icon: LayoutDashboard,
    items: [
      {
        id: 'overview',
        label: 'Overview',
        description: 'Consolidated multi-market NAV, P&L & asset allocation',
        icon: LayoutDashboard,
      },
      {
        id: 'markets',
        label: 'Markets',
        description: 'Global indices, FX benchmarks & session liquidity regimes',
        icon: Globe,
      },
      {
        id: 'scanner',
        label: 'Market Scanner',
        description: 'Factor & momentum screening across US, IDX & Crypto',
        icon: Radar,
      },
      {
        id: 'watchlist',
        label: 'Watchlist',
        description: 'Tracked research universe & technical inflection notes',
        icon: Eye,
      },
    ],
  },
  {
    id: 'portfolio',
    section: 'Portfolio',
    icon: Briefcase,
    items: [
      {
        id: 'portfolios',
        label: 'Portfolios',
        description: 'Mandate sleeves, capital targets & sleeve attribution',
        icon: Briefcase,
      },
      {
        id: 'holdings',
        label: 'Holdings',
        description: 'Multi-currency position ledger & unrealized P&L breakdown',
        icon: Layers,
      },
      {
        id: 'transactions',
        label: 'Transactions',
        description: 'Audit trail of lot entries, dividends & cash movements',
        icon: ArrowLeftRight,
      },
      {
        id: 'performance',
        label: 'Performance',
        description: 'Time-weighted return (TWR), alpha spread & drawdowns',
        icon: TrendingUp,
      },
    ],
  },
  {
    id: 'analytics',
    section: 'Analytics',
    icon: PieChart,
    items: [
      {
        id: 'risk',
        label: 'Risk Analysis',
        description: 'Parametric VaR, beta exposure & tail volatility decomposition',
        icon: ShieldAlert,
      },
      {
        id: 'allocation',
        label: 'Asset Allocation',
        description: 'Strategic target vs actual weight drift across sleeves',
        icon: PieChart,
      },
      {
        id: 'correlation',
        label: 'Correlation Analysis',
        description: 'Cross-market covariance matrix & regime sensitivity',
        icon: GitCompare,
      },
      {
        id: 'technical',
        label: 'Technical Analysis',
        description: 'Multi-timeframe trend structure, SMAs & RSI breadth',
        icon: CandlestickChart,
      },
    ],
  },
  {
    id: 'research',
    section: 'Research',
    icon: Sparkles,
    items: [
      {
        id: 'ai-research',
        label: 'AI Research',
        description: 'Quantitative thesis synthesis & filing digest briefs',
        icon: Sparkles,
        badge: 'BETA',
      },
      {
        id: 'intelligence',
        label: 'Market Intelligence',
        description: 'Central bank policy tracker & institutional flow notes',
        icon: Newspaper,
      },
    ],
  },
  {
    id: 'system',
    section: 'System',
    icon: Settings,
    items: [
      {
        id: 'settings',
        label: 'Settings',
        description: 'Base reporting currency, FX reference & data feeds',
        icon: Settings,
      },
    ],
  },
];

const PORTFOLIOS: PortfolioProfile[] = [
  {
    id: 'MASTER',
    name: 'Master Consolidated',
    code: 'PIMS-ALL-01',
    mandate: 'Multi-Asset Global & Domestic Capital Compounding',
    marketsIncluded: ['US', 'IDX', 'CRYPTO'],
  },
  {
    id: 'GLOBAL_EQUITY',
    name: 'US Equities Core',
    code: 'PIMS-US-02',
    mandate: 'US Large-Cap Quality Compounders & Index Beta',
    marketsIncluded: ['US'],
  },
  {
    id: 'IDX_CORE',
    name: 'IDX Value & Dividend',
    code: 'PIMS-IDX-03',
    mandate: 'LQ45 Blue-Chip Banking & Telecom Infrastructure',
    marketsIncluded: ['IDX'],
  },
  {
    id: 'DIGITAL_ALPHA',
    name: 'Digital Assets Sleeve',
    code: 'PIMS-CRY-04',
    mandate: 'Layer-1 Core & Institutional Infrastructure Protocols',
    marketsIncluded: ['CRYPTO'],
  },
];

const SAMPLE_HOLDINGS: HoldingPosition[] = [
  // United States Stocks
  {
    id: 'pos-nvda',
    symbol: 'NVDA',
    name: 'NVIDIA Corporation',
    market: 'US',
    assetClass: 'Equities',
    sector: 'Semiconductors',
    quantity: 420,
    avgCostUsd: 94.5,
    currentPriceUsd: 138.2,
    nativeCurrency: 'USD',
    dayChangePct: 2.14,
    targetWeightPct: 6.5,
    strategyTag: 'Secular AI Compute',
  },
  {
    id: 'pos-msft',
    symbol: 'MSFT',
    name: 'Microsoft Corporation',
    market: 'US',
    assetClass: 'Equities',
    sector: 'Enterprise Software',
    quantity: 145,
    avgCostUsd: 382.0,
    currentPriceUsd: 426.5,
    nativeCurrency: 'USD',
    dayChangePct: 0.68,
    targetWeightPct: 7.0,
    strategyTag: 'Core Quality Compounder',
  },
  {
    id: 'pos-voo',
    symbol: 'VOO',
    name: 'Vanguard S&P 500 ETF',
    market: 'US',
    assetClass: 'Index ETF',
    sector: 'US Broad Index',
    quantity: 180,
    avgCostUsd: 442.0,
    currentPriceUsd: 538.4,
    nativeCurrency: 'USD',
    dayChangePct: 0.52,
    targetWeightPct: 11.5,
    strategyTag: 'Benchmark Beta Anchor',
  },
  {
    id: 'pos-aapl',
    symbol: 'AAPL',
    name: 'Apple Inc.',
    market: 'US',
    assetClass: 'Equities',
    sector: 'Consumer Hardware',
    quantity: 210,
    avgCostUsd: 178.4,
    currentPriceUsd: 228.0,
    nativeCurrency: 'USD',
    dayChangePct: -0.35,
    targetWeightPct: 5.5,
    strategyTag: 'Core Quality Compounder',
  },
  {
    id: 'pos-googl',
    symbol: 'GOOGL',
    name: 'Alphabet Inc. Class A',
    market: 'US',
    assetClass: 'Equities',
    sector: 'Interactive Media',
    quantity: 240,
    avgCostUsd: 146.0,
    currentPriceUsd: 176.8,
    nativeCurrency: 'USD',
    dayChangePct: 1.12,
    targetWeightPct: 5.0,
    strategyTag: 'GARP Large Cap',
  },
  // Indonesian Stocks (IDX) — Reconciled at USD/IDR 15,850
  {
    id: 'pos-bbca',
    symbol: 'BBCA.JK',
    name: 'Bank Central Asia Tbk',
    market: 'IDX',
    assetClass: 'Equities',
    sector: 'Financials · Banking',
    quantity: 145000,
    avgCostUsd: 9000 / USD_TO_IDR_RATE,
    currentPriceUsd: 10025 / USD_TO_IDR_RATE,
    nativeCurrency: 'IDR',
    nativeAvgCostIdr: 9000,
    nativePriceIdr: 10025,
    dayChangePct: 0.75,
    targetWeightPct: 10.5,
    strategyTag: 'IDX Core Franchise',
  },
  {
    id: 'pos-bmri',
    symbol: 'BMRI.JK',
    name: 'Bank Mandiri (Persero) Tbk',
    market: 'IDX',
    assetClass: 'Equities',
    sector: 'Financials · Banking',
    quantity: 160000,
    avgCostUsd: 6000 / USD_TO_IDR_RATE,
    currentPriceUsd: 6625 / USD_TO_IDR_RATE,
    nativeCurrency: 'IDR',
    nativeAvgCostIdr: 6000,
    nativePriceIdr: 6625,
    dayChangePct: -0.45,
    targetWeightPct: 7.5,
    strategyTag: 'Dividend & Wholesale',
  },
  {
    id: 'pos-tlkm',
    symbol: 'TLKM.JK',
    name: 'Telkom Indonesia (Persero) Tbk',
    market: 'IDX',
    assetClass: 'Equities',
    sector: 'Telecom Infrastructure',
    quantity: 220000,
    avgCostUsd: 3400 / USD_TO_IDR_RATE,
    currentPriceUsd: 2910 / USD_TO_IDR_RATE,
    nativeCurrency: 'IDR',
    nativeAvgCostIdr: 3400,
    nativePriceIdr: 2910,
    dayChangePct: -1.02,
    targetWeightPct: 5.0,
    strategyTag: 'Yield & Data Center',
  },
  {
    id: 'pos-asii',
    symbol: 'ASII.JK',
    name: 'Astra International Tbk',
    market: 'IDX',
    assetClass: 'Equities',
    sector: 'Industrials · Conglomerate',
    quantity: 130000,
    avgCostUsd: 5300 / USD_TO_IDR_RATE,
    currentPriceUsd: 5125 / USD_TO_IDR_RATE,
    nativeCurrency: 'IDR',
    nativeAvgCostIdr: 5300,
    nativePriceIdr: 5125,
    dayChangePct: 0.39,
    targetWeightPct: 4.5,
    strategyTag: 'Value Contrarian',
  },
  // Cryptocurrency
  {
    id: 'pos-btc',
    symbol: 'BTC',
    name: 'Bitcoin',
    market: 'CRYPTO',
    assetClass: 'Digital Assets',
    sector: 'Layer-1 Monetary',
    quantity: 1.45,
    avgCostUsd: 54200.0,
    currentPriceUsd: 89400.0,
    nativeCurrency: 'USD',
    dayChangePct: 1.85,
    targetWeightPct: 14.0,
    strategyTag: 'Macro Liquidity Hedge',
  },
  {
    id: 'pos-eth',
    symbol: 'ETH',
    name: 'Ethereum',
    market: 'CRYPTO',
    assetClass: 'Digital Assets',
    sector: 'Smart Contract L1',
    quantity: 18.5,
    avgCostUsd: 2640.0,
    currentPriceUsd: 3180.0,
    nativeCurrency: 'USD',
    dayChangePct: 0.92,
    targetWeightPct: 6.5,
    strategyTag: 'Settlement Infrastructure',
  },
  {
    id: 'pos-sol',
    symbol: 'SOL',
    name: 'Solana',
    market: 'CRYPTO',
    assetClass: 'Digital Assets',
    sector: 'High-Throughput L1',
    quantity: 165,
    avgCostUsd: 118.0,
    currentPriceUsd: 214.0,
    nativeCurrency: 'USD',
    dayChangePct: 3.4,
    targetWeightPct: 3.5,
    strategyTag: 'Asymmetric Beta',
  },
  {
    id: 'pos-link',
    symbol: 'LINK',
    name: 'Chainlink',
    market: 'CRYPTO',
    assetClass: 'Digital Assets',
    sector: 'Oracle Middleware',
    quantity: 1100,
    avgCostUsd: 15.2,
    currentPriceUsd: 14.1,
    nativeCurrency: 'USD',
    dayChangePct: -1.18,
    targetWeightPct: 2.0,
    strategyTag: 'Cross-Chain Data',
  },
];

const CASH_RESERVES_BY_MARKET: Record<Exclude<MarketSegment, 'ALL'>, number> = {
  US: 38500.0,
  IDX: 29200.0,
  CRYPTO: 24800.0,
};

const BENCHMARK_LABELS: Record<BenchmarkId, string> = {
  NONE: 'None',
  SPX: 'S&P 500',
  IHSG: 'IHSG (JKSE)',
  BTC: 'Bitcoin (BTC)',
  BALANCED_60_40: '60/40 Blended',
};

function buildPerformanceSeries(
  range: TimeRange,
  currentNavUsd: number
): ChartSeriesPoint[] {
  const configs: Record<
    TimeRange,
    {
      startMultiplier: number;
      spxEnd: number;
      ihsgEnd: number;
      btcEnd: number;
      balEnd: number;
      labels: string[];
    }
  > = {
    '1D': {
      startMultiplier: 0.9904,
      spxEnd: 0.54,
      ihsgEnd: 0.34,
      btcEnd: 1.85,
      balEnd: 0.38,
      labels: [
        '09:30',
        '10:00',
        '10:30',
        '11:00',
        '11:30',
        '12:00',
        '12:30',
        '13:00',
        '13:30',
        '14:00',
        '14:30',
        '15:00',
        '15:30',
        '16:00',
      ],
    },
    '1W': {
      startMultiplier: 0.9785,
      spxEnd: 1.42,
      ihsgEnd: -0.28,
      btcEnd: 4.15,
      balEnd: 0.94,
      labels: [
        'Nov 10',
        'Nov 11',
        'Nov 12',
        'Nov 13',
        'Nov 14',
        'Nov 15',
        'Nov 16',
      ],
    },
    '1M': {
      startMultiplier: 0.948,
      spxEnd: 3.18,
      ihsgEnd: 1.12,
      btcEnd: 11.4,
      balEnd: 2.15,
      labels: [
        'Oct 18',
        'Oct 20',
        'Oct 22',
        'Oct 24',
        'Oct 26',
        'Oct 28',
        'Oct 30',
        'Nov 01',
        'Nov 03',
        'Nov 05',
        'Nov 07',
        'Nov 09',
        'Nov 11',
        'Nov 14',
        'Nov 16',
      ],
    },
    '3M': {
      startMultiplier: 0.892,
      spxEnd: 6.85,
      ihsgEnd: 2.45,
      btcEnd: 24.6,
      balEnd: 4.8,
      labels: [
        'Aug 18',
        'Aug 25',
        'Sep 01',
        'Sep 08',
        'Sep 15',
        'Sep 22',
        'Sep 29',
        'Oct 06',
        'Oct 13',
        'Oct 20',
        'Oct 27',
        'Nov 06',
        'Nov 16',
      ],
    },
    '6M': {
      startMultiplier: 0.845,
      spxEnd: 11.2,
      ihsgEnd: 4.9,
      btcEnd: 33.8,
      balEnd: 7.9,
      labels: [
        'May 18',
        'Jun 01',
        'Jun 15',
        'Jul 01',
        'Jul 15',
        'Aug 01',
        'Aug 15',
        'Sep 01',
        'Sep 15',
        'Oct 01',
        'Oct 15',
        'Nov 01',
        'Nov 16',
      ],
    },
    YTD: {
      startMultiplier: 0.812,
      spxEnd: 18.4,
      ihsgEnd: 6.15,
      btcEnd: 54.2,
      balEnd: 12.6,
      labels: [
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
        'EOD',
      ],
    },
    '1Y': {
      startMultiplier: 0.785,
      spxEnd: 22.1,
      ihsgEnd: 7.8,
      btcEnd: 62.5,
      balEnd: 15.1,
      labels: [
        'Nov',
        'Dec',
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
      ],
    },
    ALL: {
      startMultiplier: 0.733,
      spxEnd: 29.4,
      ihsgEnd: 11.2,
      btcEnd: 88.0,
      balEnd: 19.8,
      labels: [
        '23 Q1',
        '23 Q2',
        '23 Q3',
        '23 Q4',
        '24 Q1',
        '24 Q2',
        '24 Q3',
        '24 Q4',
        '25 Q1',
        '25 Q2',
        '25 Q3',
        '25 Q4',
        '26 Q1',
        '26 Q2',
        '26 Q3',
        '26 Q4',
      ],
    },
  };

  const cfg = configs[range];
  const startNav = currentNavUsd * cfg.startMultiplier;
  const totalDelta = currentNavUsd - startNav;

  return cfg.labels.map((label, idx) => {
    const t = idx / (cfg.labels.length - 1);
    const wave =
      Math.sin(idx * 1.45) * 0.013 * (1 - Math.abs(2 * t - 1)) +
      Math.cos(idx * 0.85) * 0.005 * t;
    const progress = idx === cfg.labels.length - 1 ? 1 : Math.max(0, t + wave);
    const portfolioValue = startNav + totalDelta * progress;
    const portfolioReturnPct =
      startNav > 0 ? ((portfolioValue - startNav) / startNav) * 100 : 0;

    const benchWave = Math.sin(idx * 1.1) * 0.35 * (1 - t);
    return {
      timestamp: `2026-${String((idx % 12) + 1).padStart(2, '0')}`,
      label,
      portfolioValue,
      portfolioReturnPct,
      benchmarkReturnPct: {
        SPX: Number((cfg.spxEnd * t + benchWave).toFixed(2)),
        IHSG: Number((cfg.ihsgEnd * t - benchWave * 0.7).toFixed(2)),
        BTC: Number((cfg.btcEnd * t + benchWave * 2.1).toFixed(2)),
        BALANCED_60_40: Number((cfg.balEnd * t + benchWave * 0.5).toFixed(2)),
      },
    };
  });
}

const MARKET_REGIME_GROUPS: MarketRegimeGroup[] = [
  {
    market: 'CRYPTO',
    title: 'Cryptocurrency',
    regimeTag: 'EXPANSION',
    indices: [
      {
        id: 'idx-btc',
        symbol: 'BTC',
        name: 'Bitcoin Spot',
        lastClose: '$89,400.00',
        changePct: 1.85,
        breadthPct: 84,
        breadthLabel: 'Momentum 84/100',
      },
      {
        id: 'idx-eth',
        symbol: 'ETH',
        name: 'Ethereum Spot',
        lastClose: '$3,180.00',
        changePct: 0.92,
        breadthPct: 68,
        breadthLabel: 'Momentum 68/100',
      },
    ],
  },
  {
    market: 'US',
    title: 'US Equities',
    regimeTag: 'UPTREND',
    indices: [
      {
        id: 'idx-spx',
        symbol: 'S&P 500',
        name: 'US Large Cap Benchmark',
        lastClose: '5,870.62',
        changePct: 0.54,
        breadthPct: 76,
        breadthLabel: 'Breadth 76% > 50D',
      },
      {
        id: 'idx-ndx',
        symbol: 'NASDAQ 100',
        name: 'US Tech & Growth Index',
        lastClose: '20,394.15',
        changePct: 0.81,
        breadthPct: 79,
        breadthLabel: 'Breadth 79% > 50D',
      },
    ],
  },
  {
    market: 'IDX',
    title: 'Indonesian Stocks',
    regimeTag: 'ACCUMULATION',
    indices: [
      {
        id: 'idx-jkse',
        symbol: 'IHSG / JKSE',
        name: 'Jakarta Composite Index',
        lastClose: '7,284.40',
        changePct: 0.34,
        breadthPct: 58,
        breadthLabel: 'Breadth 58% > 50D',
      },
      {
        id: 'idx-lq45',
        symbol: 'IDX LQ45',
        name: 'Indonesia Blue-Chip 45',
        lastClose: '886.18',
        changePct: -0.18,
        breadthPct: 52,
        breadthLabel: 'Breadth 52% > 50D',
      },
    ],
  },
];

const INITIAL_WATCHLIST: WatchlistEntry[] = [
  {
    id: 'wl-nvda',
    symbol: 'NVDA',
    monogram: 'NV',
    name: 'NVIDIA Corporation',
    market: 'US',
    priceFormatted: '$138.20',
    dailyChangePct: 2.14,
    sparkline: [131.5, 133.2, 132.8, 134.9, 136.4, 137.1, 138.2],
    pinned: true,
    metrics: {
      valuationMetricLabel: 'Fwd P/E',
      valuationMetricValue: '34.2x',
      range52w: '$47.32 — $149.77',
      rsi14: 61.4,
      sma50Status: 'Above 50D SMA',
      beta: '1.68',
      analyticalNote:
        'Hyperscaler data center capex visibility supports forward revenue revisions; watching gross margin stabilization.',
    },
  },
  {
    id: 'wl-bbca',
    symbol: 'BBCA.JK',
    monogram: 'BC',
    name: 'Bank Central Asia Tbk',
    market: 'IDX',
    priceFormatted: '$0.6325',
    secondaryPriceNote: 'Rp 10,025',
    dailyChangePct: 0.75,
    sparkline: [9825, 9850, 9875, 9900, 9950, 9975, 10025],
    pinned: true,
    metrics: {
      valuationMetricLabel: 'P/BV Ratio',
      valuationMetricValue: '4.65x',
      range52w: 'Rp 8,775 — Rp 10,950',
      rsi14: 55.8,
      sma50Status: 'Above 50D SMA',
      beta: '0.84',
      analyticalNote:
        'Industry-leading 81.5% CASA deposit franchise insulates net interest margin against benchmark rate shifts.',
    },
  },
  {
    id: 'wl-sol',
    symbol: 'SOL',
    monogram: 'SL',
    name: 'Solana Spot',
    market: 'CRYPTO',
    priceFormatted: '$214.00',
    dailyChangePct: 3.4,
    sparkline: [194, 198, 201, 199, 206, 210, 214],
    pinned: true,
    metrics: {
      valuationMetricLabel: '30D Fee Rev',
      valuationMetricValue: '$118.4M',
      range52w: '$54.10 — $225.80',
      rsi14: 66.2,
      sma50Status: 'Above 50D SMA',
      beta: '1.92',
      analyticalNote:
        'High-throughput DEX settlement share and active validator stake ratio remain near cycle highs.',
    },
  },
  {
    id: 'wl-msft',
    symbol: 'MSFT',
    monogram: 'MS',
    name: 'Microsoft Corporation',
    market: 'US',
    priceFormatted: '$426.50',
    dailyChangePct: 0.68,
    sparkline: [418, 420.5, 419.8, 422.1, 424.0, 425.2, 426.5],
    pinned: false,
    metrics: {
      valuationMetricLabel: 'Fwd P/E',
      valuationMetricValue: '31.8x',
      range52w: '$366.50 — $468.35',
      rsi14: 53.1,
      sma50Status: 'Near 50D SMA',
      beta: '0.94',
      analyticalNote:
        'Azure commercial cloud backlog growth (+31% YoY) anchors defensive enterprise cash flow compounding.',
    },
  },
  {
    id: 'wl-bmri',
    symbol: 'BMRI.JK',
    monogram: 'BM',
    name: 'Bank Mandiri (Persero) Tbk',
    market: 'IDX',
    priceFormatted: '$0.4180',
    secondaryPriceNote: 'Rp 6,625',
    dailyChangePct: -0.45,
    sparkline: [6725, 6700, 6675, 6650, 6625, 6625, 6625],
    pinned: false,
    metrics: {
      valuationMetricLabel: 'Div Yield',
      valuationMetricValue: '5.42%',
      range52w: 'Rp 5,725 — Rp 7,550',
      rsi14: 44.7,
      sma50Status: 'Below 50D SMA',
      beta: '1.08',
      analyticalNote:
        'Wholesale corporate loan expansion remains resilient; monitoring liquidity cost ahead of year-end.',
    },
  },
  {
    id: 'wl-link',
    symbol: 'LINK',
    monogram: 'LK',
    name: 'Chainlink',
    market: 'CRYPTO',
    priceFormatted: '$14.10',
    dailyChangePct: -1.18,
    sparkline: [14.9, 14.7, 14.5, 14.6, 14.3, 14.2, 14.1],
    pinned: false,
    metrics: {
      valuationMetricLabel: 'CCIP TVE',
      valuationMetricValue: '$26.4B',
      range52w: '$9.45 — $22.85',
      rsi14: 42.9,
      sma50Status: 'Below 50D SMA',
      beta: '1.54',
      analyticalNote:
        'Institutional tokenization & cross-chain interoperability adoption expanding across RWA pilot networks.',
    },
  },
];

const RECENT_ACTIVITIES: ActivityLogEntry[] = [
  {
    id: 'act-1',
    category: 'TRANSACTION_RECORDED',
    title: 'Transaction Recorded · BBCA.JK',
    description: 'Lot entry +15,000 shares @ Rp 9,850 ($9,321.77 cost basis)',
    portfolioTag: 'IDX Value & Dividend',
    timestamp: '16 Nov · 15:42 WIB',
  },
  {
    id: 'act-2',
    category: 'ALLOCATION_REBALANCED',
    title: 'Allocation Rebalanced · Digital Assets',
    description: 'Updated target sleeve weight ceiling from 24.0% to 26.0%',
    portfolioTag: 'Master Consolidated',
    timestamp: '15 Nov · 19:10 WIB',
  },
  {
    id: 'act-3',
    category: 'ASSET_ADDED',
    title: 'Asset Added · VOO',
    description: 'Consolidated 180 units of Vanguard S&P 500 ETF into core',
    portfolioTag: 'US Equities Core',
    timestamp: '14 Nov · 22:05 WIB',
  },
  {
    id: 'act-4',
    category: 'WATCHLIST_UPDATED',
    title: 'Watchlist Updated · NVDA & SOL',
    description: 'Pinned priority research symbols with updated valuation notes',
    portfolioTag: 'Research Universe',
    timestamp: '13 Nov · 11:20 WIB',
  },
  {
    id: 'act-5',
    category: 'TRANSACTION_RECORDED',
    title: 'Dividend Accrual · BMRI.JK',
    description: 'Recorded cash dividend credit (+$1,420.00) into IDX RDN buffer',
    portfolioTag: 'IDX Value & Dividend',
    timestamp: '11 Nov · 16:05 WIB',
  },
];

// ============================================================================
// 4. FORMATTING & UTILITY HELPERS
// ============================================================================

function formatUsd(value: number, compact = false): string {
  if (compact) {
    const abs = Math.abs(value);
    const sign = value < 0 ? '-' : '';
    if (abs >= 1_000_000) {
      return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
    }
    if (abs >= 1_000) {
      return `${sign}$${(abs / 1_000).toFixed(1)}K`;
    }
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatSignedUsd(value: number): string {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${formatUsd(value)}`;
}

function formatSignedPct(value: number): string {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(2)}%`;
}

function formatQuantity(qty: number, market: Exclude<MarketSegment, 'ALL'>): string {
  if (market === 'CRYPTO') {
    return qty >= 100
      ? qty.toLocaleString('en-US', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : qty.toLocaleString('en-US', {
          minimumFractionDigits: 4,
          maximumFractionDigits: 4,
        });
  }
  return qty.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

function getMarketBadgeColors(
  market: Exclude<MarketSegment, 'ALL'>,
  theme: ThemeMode
): { label: string; bg: string; text: string; border: string } {
  if (theme === 'dark') {
    switch (market) {
      case 'US':
        return {
          label: 'US',
          bg: '#132238',
          text: '#4F8FF7',
          border: '#274675',
        };
      case 'IDX':
        return {
          label: 'IDX',
          bg: '#1E1A33',
          text: '#A78BFA',
          border: '#362F5C',
        };
      case 'CRYPTO':
        return {
          label: 'CRYPTO',
          bg: '#0F2624',
          text: '#14B8A6',
          border: '#1D4743',
        };
    }
  }
  switch (market) {
    case 'US':
      return {
        label: 'US',
        bg: '#EFF6FF',
        text: '#1D4ED8',
        border: '#BFDBFE',
      };
    case 'IDX':
      return {
        label: 'IDX',
        bg: '#F5F3FF',
        text: '#6D28D9',
        border: '#DDD6FE',
      };
    case 'CRYPTO':
      return {
        label: 'CRYPTO',
        bg: '#F0FDFA',
        text: '#0F766E',
        border: '#99F6E4',
      };
  }
}

// ============================================================================
// 5. REUSABLE UI SUB-COMPONENTS
// ============================================================================

interface SparklineProps {
  values: number[];
  strokeColor: string;
  dotFillColor: string;
  width?: number;
  height?: number;
  showEndDot?: boolean;
}

const Sparkline: React.FC<SparklineProps> = ({
  values,
  strokeColor,
  dotFillColor,
  width = 88,
  height = 36,
  showEndDot = true,
}) => {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pad = 4;

  const coords = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (width - pad * 2);
    const y = height - pad - ((v - min) / span) * (height - pad * 2);
    return { x, y };
  });

  const points = coords
    .map((pt) => `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`)
    .join(' ');
  const last = coords[coords.length - 1];

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible shrink-0"
      aria-hidden="true"
    >
      <polyline
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
      {showEndDot && last && (
        <circle
          cx={last.x}
          cy={last.y}
          r="2.75"
          fill={dotFillColor}
          stroke={strokeColor}
          strokeWidth="1.75"
        />
      )}
    </svg>
  );
};

// ----------------------------------------------------------------------------
// A. SEGMENTED THEME TOGGLE (Dark / Light)
// ----------------------------------------------------------------------------

interface ThemeToggleProps {
  theme: ThemeMode;
  onChange: (mode: ThemeMode) => void;
  t: ThemeTokens;
}

const ThemeToggle: React.FC<ThemeToggleProps> = ({ theme, onChange, t }) => {
  return (
    <div
      role="group"
      aria-label="Color theme mode"
      style={{
        backgroundColor: t.recessedBg,
        borderColor: t.borderDefault,
      }}
      className="inline-flex items-center p-0.5 rounded border"
    >
      <button
        type="button"
        onClick={() => onChange('dark')}
        aria-pressed={theme === 'dark'}
        style={
          theme === 'dark'
            ? {
                backgroundColor: t.accentBg,
                color: t.accentText,
                borderColor: t.accentBorder,
              }
            : {
                color: t.textSecondary,
                borderColor: 'transparent',
              }
        }
        className="flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium border transition-colors"
      >
        <Moon className="w-3 h-3" />
        <span>Dark</span>
      </button>
      <button
        type="button"
        onClick={() => onChange('light')}
        aria-pressed={theme === 'light'}
        style={
          theme === 'light'
            ? {
                backgroundColor: t.accentBg,
                color: t.accentText,
                borderColor: t.accentBorder,
              }
            : {
                color: t.textSecondary,
                borderColor: 'transparent',
              }
        }
        className="flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium border transition-colors"
      >
        <Sun className="w-3 h-3" />
        <span>Light</span>
      </button>
    </div>
  );
};

// ----------------------------------------------------------------------------
// B. TOP UTILITY HEADER BAR
// ----------------------------------------------------------------------------

interface TopHeaderProps {
  theme: ThemeMode;
  onThemeChange: (mode: ThemeMode) => void;
  t: ThemeTokens;
  selectedPortfolio: PortfolioScopeId;
  onSelectPortfolio: (id: PortfolioScopeId) => void;
  selectedMarket: MarketSegment;
  onSelectMarket: (market: MarketSegment) => void;
  globalSearch: string;
  onGlobalSearchChange: (val: string) => void;
}

const TopHeader: React.FC<TopHeaderProps> = ({
  theme,
  onThemeChange,
  t,
  selectedPortfolio,
  onSelectPortfolio,
  selectedMarket,
  onSelectMarket,
  globalSearch,
  onGlobalSearchChange,
}) => {
  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  const marketTabs: { id: MarketSegment; label: string }[] = [
    { id: 'ALL', label: 'All Markets' },
    { id: 'CRYPTO', label: 'Crypto' },
    { id: 'US', label: 'US Stocks' },
    { id: 'IDX', label: 'IDX' },
  ];

  return (
    <header
      style={{
        backgroundColor: t.cardBg,
        borderColor: t.borderDefault,
      }}
      className="border-b transition-colors duration-150"
    >
      <div className="max-w-[1700px] mx-auto px-4 sm:px-6 min-h-[60px] py-2 flex flex-wrap items-center justify-between gap-3">
        {/* Left: Geometric PIMS Institutional Mark + Wordmark + Sample Data Pill */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-2.5 shrink-0">
            <div
              style={{
                backgroundColor: t.accentBg,
                borderColor: t.accentBorder,
              }}
              className="w-8 h-8 rounded border flex items-center justify-center"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
              >
                <rect
                  x="1.5"
                  y="9"
                  width="2.75"
                  height="5.5"
                  fill={t.accentText}
                />
                <rect
                  x="6.6"
                  y="5"
                  width="2.75"
                  height="9.5"
                  fill={t.textPrimary}
                />
                <rect
                  x="11.75"
                  y="1.5"
                  width="2.75"
                  height="13"
                  fill={t.gainText}
                />
              </svg>
            </div>
            <div className="leading-none">
              <div className="flex items-center gap-2">
                <span
                  style={{ color: t.textPrimary }}
                  className="text-[16px] font-bold tracking-tight"
                >
                  PIMS
                </span>
                <span
                  style={{
                    backgroundColor: t.recessedBg,
                    borderColor: t.borderDefault,
                    color: t.textSecondary,
                  }}
                  className="hidden xl:inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded border tabular-nums"
                >
                  <Clock className="w-2.5 h-2.5" />
                  SAMPLE DATA · USD/IDR 15,850
                </span>
              </div>
              <p
                style={{ color: t.textMuted }}
                className="text-[9.5px] font-semibold tracking-[0.07em] mt-1 hidden sm:block"
              >
                PERSONAL INVESTMENT MANAGEMENT
              </p>
            </div>
          </div>
        </div>

        {/* Center-Right: Portfolio Selector, Market Scope Filter, Global Search */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Portfolio Selector Dropdown */}
          <div className="relative">
            <label htmlFor="pims-portfolio-dropdown" className="sr-only">
              Select Portfolio
            </label>
            <select
              id="pims-portfolio-dropdown"
              value={selectedPortfolio}
              onChange={(e) =>
                onSelectPortfolio(e.target.value as PortfolioScopeId)
              }
              style={{
                backgroundColor: t.recessedBg,
                borderColor: t.borderDefault,
                color: t.textPrimary,
              }}
              className="appearance-none text-[12px] font-medium pl-3 pr-7 py-1.5 rounded border focus:outline-none cursor-pointer"
            >
              {PORTFOLIOS.map((p) => (
                <option
                  key={p.id}
                  value={p.id}
                  style={{
                    backgroundColor: t.cardBg,
                    color: t.textPrimary,
                  }}
                >
                  {p.name}
                </option>
              ))}
            </select>
            <ChevronDown
              style={{ color: t.textSecondary }}
              className="w-3.5 h-3.5 pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2"
            />
          </div>

          {/* Market Scope Segmented Filter */}
          <div
            role="group"
            aria-label="Market scope filter"
            style={{
              backgroundColor: t.recessedBg,
              borderColor: t.borderDefault,
            }}
            className="hidden lg:flex items-center p-0.5 rounded border"
          >
            {marketTabs.map((tab) => {
              const active = selectedMarket === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => onSelectMarket(tab.id)}
                  style={
                    active
                      ? {
                          backgroundColor: t.accentBg,
                          color: t.accentText,
                          borderColor: t.accentBorder,
                        }
                      : {
                          color: t.textSecondary,
                          borderColor: 'transparent',
                        }
                  }
                  className="px-2.5 py-1 rounded text-[11.5px] font-medium border transition-colors whitespace-nowrap"
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Global Symbol Search Input */}
          <div className="relative w-40 sm:w-48 xl:w-52">
            <Search
              style={{ color: t.textMuted }}
              className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none"
            />
            <input
              type="text"
              value={globalSearch}
              onChange={(e) => onGlobalSearchChange(e.target.value)}
              placeholder="Search symbol or asset..."
              aria-label="Global symbol search"
              style={{
                backgroundColor: t.recessedBg,
                borderColor: t.borderDefault,
                color: t.textPrimary,
              }}
              className="w-full text-[12px] pl-8 pr-7 py-1.5 rounded border focus:outline-none"
            />
            {globalSearch && (
              <button
                type="button"
                onClick={() => onGlobalSearchChange('')}
                style={{ color: t.textMuted }}
                className="absolute right-2 top-1/2 -translate-y-1/2"
                aria-label="Clear search"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Far Right: Theme Switcher, Notifications Popover, Institutional Profile */}
          <ThemeToggle theme={theme} onChange={onThemeChange} t={t} />

          {/* Notifications Popover Button */}
          <div className="relative" ref={notifRef}>
            <button
              type="button"
              onClick={() => setNotifOpen((prev) => !prev)}
              style={{
                backgroundColor: t.recessedBg,
                borderColor: t.borderDefault,
                color: t.textSecondary,
              }}
              className="relative p-1.5 rounded border transition-colors"
              aria-label="Audit notifications"
            >
              <Bell className="w-4 h-4" />
              <span
                style={{
                  backgroundColor: t.accentBg,
                  borderColor: t.accentBorder,
                  color: t.accentText,
                }}
                className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 px-1 rounded-full border font-mono text-[9.5px] font-semibold flex items-center justify-center tabular-nums"
              >
                3
              </span>
            </button>

            {notifOpen && (
              <div
                style={{
                  backgroundColor: t.cardBg,
                  borderColor: t.borderActive,
                }}
                className="absolute right-0 mt-2 w-80 border rounded shadow-xl z-40"
              >
                <div
                  style={{ borderColor: t.borderDefault }}
                  className="px-3 py-2 border-b flex items-center justify-between"
                >
                  <span
                    style={{ color: t.textSecondary }}
                    className="text-[11px] font-semibold uppercase tracking-wider"
                  >
                    Audit &amp; System Notices
                  </span>
                  <button
                    type="button"
                    onClick={() => setNotifOpen(false)}
                    style={{ color: t.accentText }}
                    className="text-[11px] font-medium hover:underline"
                  >
                    Close
                  </button>
                </div>
                <div
                  style={{ borderColor: t.borderDefault }}
                  className="divide-y text-[12px]"
                >
                  <div
                    style={{ borderColor: t.borderDefault }}
                    className="p-2.5"
                  >
                    <div className="flex items-center justify-between">
                      <span
                        style={{ color: t.textPrimary }}
                        className="font-medium"
                      >
                        Allocation Drift Check
                      </span>
                      <span
                        style={{ color: t.textMuted }}
                        className="text-[10px] font-mono"
                      >
                        EOD REF
                      </span>
                    </div>
                    <p
                      style={{ color: t.textSecondary }}
                      className="text-[11px] mt-0.5"
                    >
                      Digital Assets Sleeve is +0.71% above target mandate weight.
                    </p>
                  </div>
                  <div
                    style={{ borderColor: t.borderDefault }}
                    className="p-2.5"
                  >
                    <div className="flex items-center justify-between">
                      <span
                        style={{ color: t.textPrimary }}
                        className="font-medium"
                      >
                        USD/IDR Reference Rate
                      </span>
                      <span
                        style={{ color: t.textMuted }}
                        className="text-[10px] font-mono"
                      >
                        IDX FX
                      </span>
                    </div>
                    <p
                      style={{ color: t.textSecondary }}
                      className="text-[11px] mt-0.5"
                    >
                      IDX equity valuations reconciled at 15,850 IDR per USD.
                    </p>
                  </div>
                  <div className="p-2.5">
                    <div className="flex items-center justify-between">
                      <span
                        style={{ color: t.textPrimary }}
                        className="font-medium"
                      >
                        Read-Only Terminal Mode
                      </span>
                      <span
                        style={{ color: t.textMuted }}
                        className="text-[10px] font-mono"
                      >
                        SYS
                      </span>
                    </div>
                    <p
                      style={{ color: t.textSecondary }}
                      className="text-[11px] mt-0.5"
                    >
                      Analytical sample dataset active · Non-brokerage environment.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Institutional Profile Badge */}
          <div
            style={{
              backgroundColor: t.recessedBg,
              borderColor: t.borderDefault,
            }}
            className="flex items-center gap-2 pl-2 pr-2.5 py-1 rounded border"
          >
            <div
              style={{
                backgroundColor: t.accentBg,
                borderColor: t.accentBorder,
                color: t.accentText,
              }}
              className="w-6 h-6 rounded-full border flex items-center justify-center text-[10px] font-bold"
            >
              MH
            </div>
            <div className="hidden sm:block leading-none">
              <div
                style={{ color: t.textPrimary }}
                className="text-[11.5px] font-semibold"
              >
                M. Hafizh
              </div>
              <div
                style={{ color: t.textMuted }}
                className="text-[9.5px] font-mono mt-0.5"
              >
                Quant Ops
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

// ----------------------------------------------------------------------------
// C. CENTERED HORIZONTAL SUB-NAVIGATION BAR
// ----------------------------------------------------------------------------

interface HorizontalNavProps {
  activeRoute: NavRouteId;
  onSelectRoute: (route: NavRouteId) => void;
  t: ThemeTokens;
}

const HorizontalNav: React.FC<HorizontalNavProps> = ({
  activeRoute,
  onSelectRoute,
  t,
}) => {
  const [openGroupId, setOpenGroupId] = useState<NavGroupId | null>(null);
  const navRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setOpenGroupId(null);
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpenGroupId(null);
    };
    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleOutside);
      document.removeEventListener('keydown', handleKey);
    };
  }, []);

  const activeGroupId = useMemo(() => {
    for (const grp of NAVIGATION_GROUPS) {
      if (grp.items.some((i) => i.id === activeRoute)) {
        return grp.id;
      }
    }
    return 'main';
  }, [activeRoute]);

  return (
    <nav
      ref={navRef}
      aria-label="Primary Module Navigation"
      style={{
        backgroundColor: t.cardBg,
        borderColor: t.borderDefault,
      }}
      className="border-b sticky top-0 z-20 transition-colors duration-150"
    >
      <div className="max-w-[1700px] mx-auto px-4 sm:px-6 flex items-center justify-start md:justify-center overflow-x-auto md:overflow-visible">
        <div className="flex items-center gap-1 sm:gap-2">
          {NAVIGATION_GROUPS.map((group) => {
            const GroupIcon = group.icon;
            const isGroupActive = activeGroupId === group.id;
            const isOpen = openGroupId === group.id;
            const hasMultiple = group.items.length > 1;

            return (
              <div
                key={group.id}
                className="relative"
                onMouseEnter={() => setOpenGroupId(group.id)}
                onMouseLeave={() => setOpenGroupId(null)}
              >
                <button
                  type="button"
                  onClick={() => {
                    if (!hasMultiple) {
                      onSelectRoute(group.items[0].id);
                      setOpenGroupId(null);
                    } else {
                      setOpenGroupId((prev) =>
                        prev === group.id ? null : group.id
                      );
                    }
                  }}
                  aria-expanded={hasMultiple ? isOpen : undefined}
                  style={{
                    color: isGroupActive ? t.accentText : t.textSecondary,
                  }}
                  className="relative flex items-center gap-2 px-3.5 py-3 text-[12.5px] font-medium transition-colors whitespace-nowrap"
                >
                  <GroupIcon
                    style={{
                      color: isGroupActive ? t.accentText : t.textMuted,
                    }}
                    className="w-3.5 h-3.5"
                  />
                  <span>{group.section}</span>
                  {hasMultiple && (
                    <ChevronDown
                      style={{
                        color: isOpen ? t.accentText : t.textMuted,
                      }}
                      className={`w-3 h-3 transition-transform duration-150 ${
                        isOpen ? 'rotate-180' : ''
                      }`}
                    />
                  )}

                  {isGroupActive && (
                    <span
                      style={{ backgroundColor: t.accentText }}
                      className="absolute bottom-0 left-2 right-2 h-[2px]"
                    />
                  )}
                </button>

                {hasMultiple && isOpen && (
                  <div
                    style={{
                      backgroundColor: t.cardBg,
                      borderColor: t.borderActive,
                    }}
                    className="absolute left-0 top-full w-64 border rounded-b shadow-xl z-30 py-1.5"
                  >
                    <div
                      style={{
                        color: t.textMuted,
                        borderColor: t.borderDefault,
                      }}
                      className="px-3 py-1 text-[10px] font-mono uppercase tracking-wider border-b mb-1"
                    >
                      {group.section} Modules
                    </div>
                    {group.items.map((item) => {
                      const ItemIcon = item.icon;
                      const isItemActive = activeRoute === item.id;
                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => {
                            onSelectRoute(item.id);
                            setOpenGroupId(null);
                          }}
                          style={
                            isItemActive
                              ? {
                                  backgroundColor: t.accentBg,
                                  color: t.accentText,
                                }
                              : {
                                  color: t.textPrimary,
                                }
                          }
                          className="w-full px-3 py-2 text-left flex items-start gap-2.5 transition-colors"
                        >
                          <ItemIcon
                            style={{
                              color: isItemActive ? t.accentText : t.textMuted,
                            }}
                            className="w-3.5 h-3.5 mt-0.5 shrink-0"
                          />
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-1.5">
                              <span className="text-[12px] font-medium">
                                {item.label}
                              </span>
                              {item.badge && (
                                <span
                                  style={{
                                    backgroundColor: t.recessedBg,
                                    borderColor: t.borderDefault,
                                    color: t.textSecondary,
                                  }}
                                  className="text-[9px] font-mono px-1 rounded border"
                                >
                                  {item.badge}
                                </span>
                              )}
                            </div>
                            <p
                              style={{ color: t.textMuted }}
                              className="text-[10.5px] leading-snug mt-0.5"
                            >
                              {item.description}
                            </p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </nav>
  );
};

// ----------------------------------------------------------------------------
// D. ROW 1 — 5 SPLIT KPI SUMMARY CARDS (Two-Tone Architectural Split)
// ----------------------------------------------------------------------------

interface KpiSplitCardProps {
  title: string;
  dollarValue: string;
  badgeText?: string;
  badgeVariant?: 'gain' | 'loss' | 'neutral';
  secondaryContext: string;
  sparklineValues: number[];
  sparklineColor: string;
  t: ThemeTokens;
}

const KpiSplitCard: React.FC<KpiSplitCardProps> = ({
  title,
  dollarValue,
  badgeText,
  badgeVariant = 'neutral',
  secondaryContext,
  sparklineValues,
  sparklineColor,
  t,
}) => {
  const badgeStyle =
    badgeVariant === 'gain'
      ? {
          color: t.gainText,
          backgroundColor: t.gainBg,
          borderColor: t.gainBorder,
        }
      : badgeVariant === 'loss'
      ? {
          color: t.lossText,
          backgroundColor: t.lossBg,
          borderColor: t.lossBorder,
        }
      : {
          color: t.accentText,
          backgroundColor: t.accentBg,
          borderColor: t.accentBorder,
        };

  const valueColor =
    badgeVariant === 'gain'
      ? t.gainText
      : badgeVariant === 'loss'
      ? t.lossText
      : t.textPrimary;

  return (
    <div
      style={{
        backgroundColor: t.cardBg,
        borderColor: t.borderDefault,
      }}
      className="border rounded overflow-hidden flex items-stretch min-h-[96px] transition-colors duration-150"
    >
      {/* Left Pane: Tinted Secondary Surface with Metric Hierarchy */}
      <div
        style={{ backgroundColor: t.secondaryBg }}
        className="flex-1 min-w-0 px-3.5 py-3 flex flex-col justify-between"
      >
        <div
          style={{ color: t.textMuted }}
          className="text-[10px] font-semibold uppercase tracking-[0.06em] truncate"
        >
          {title}
        </div>

        <div className="my-1 flex items-baseline gap-2 flex-wrap">
          <span
            style={{ color: valueColor }}
            className="text-[18px] xl:text-[19px] font-bold tracking-tight tabular-nums leading-none"
          >
            {dollarValue}
          </span>
          {badgeText && (
            <span
              style={badgeStyle}
              className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded border tabular-nums leading-none"
            >
              {badgeText}
            </span>
          )}
        </div>

        <div
          style={{ color: t.textSecondary }}
          className="text-[10.5px] font-mono tabular-nums truncate"
        >
          {secondaryContext}
        </div>
      </div>

      {/* Right Pane: Primary Surface with SVG Sparkline & End-Point Marker */}
      <div
        style={{
          backgroundColor: t.cardBg,
          borderColor: t.borderDefault,
        }}
        className="w-[98px] xl:w-[106px] shrink-0 border-l px-2.5 py-2 flex items-center justify-center"
      >
        <Sparkline
          values={sparklineValues}
          strokeColor={sparklineColor}
          dotFillColor={t.cardBg}
          width={80}
          height={36}
          showEndDot={true}
        />
      </div>
    </div>
  );
};

// ----------------------------------------------------------------------------
// E. ROW 2 LEFT (8 COLS) — PORTFOLIO PERFORMANCE CHART
// ----------------------------------------------------------------------------

const PerformanceChart: React.FC<LightweightChartAdapterProps> = ({
  data,
  timeRange,
  benchmark,
  displayMode,
  portfolioLabel,
  marketLabel,
  themeTokens: t,
  onTimeRangeChange,
  onBenchmarkChange,
  onDisplayModeChange,
}) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const timeRanges: TimeRange[] = [
    '1D',
    '1W',
    '1M',
    '3M',
    '6M',
    'YTD',
    '1Y',
    'ALL',
  ];

  const width = 820;
  const height = 290;
  const padLeft = 16;
  const padRight = 68;
  const padTop = 18;
  const padBottom = 28;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const activePoint =
    hoverIndex !== null && data[hoverIndex]
      ? data[hoverIndex]
      : data[data.length - 1];

  const periodReturn =
    data.length > 0 ? data[data.length - 1].portfolioReturnPct : 0;
  const lineStroke = periodReturn >= 0 ? t.gainText : t.lossText;
  const areaFill =
    periodReturn >= 0
      ? t.mode === 'dark'
        ? 'rgba(63, 185, 80, 0.09)'
        : 'rgba(21, 128, 61, 0.08)'
      : t.mode === 'dark'
      ? 'rgba(248, 81, 73, 0.09)'
      : 'rgba(220, 38, 38, 0.08)';

  const effectiveMode = benchmark !== 'NONE' ? 'RETURN_PCT' : displayMode;

  const { minVal, maxVal, yTicks } = useMemo(() => {
    if (data.length === 0) {
      return { minVal: 0, maxVal: 100, yTicks: [0, 50, 100] };
    }
    const vals: number[] = [];
    data.forEach((pt) => {
      if (effectiveMode === 'NAV') {
        vals.push(pt.portfolioValue);
      } else {
        vals.push(pt.portfolioReturnPct);
        if (benchmark !== 'NONE') {
          vals.push(pt.benchmarkReturnPct[benchmark]);
        }
      }
    });

    const rawMin = Math.min(...vals);
    const rawMax = Math.max(...vals);
    const span = rawMax - rawMin || 1;
    const paddedMin = rawMin - span * 0.1;
    const paddedMax = rawMax + span * 0.1;

    const tickCount = 5;
    const ticks: number[] = [];
    for (let i = 0; i < tickCount; i++) {
      ticks.push(paddedMin + ((paddedMax - paddedMin) * i) / (tickCount - 1));
    }
    return { minVal: paddedMin, maxVal: paddedMax, yTicks: ticks };
  }, [data, effectiveMode, benchmark]);

  const getX = useCallback(
    (index: number) => {
      if (data.length <= 1) return padLeft;
      return padLeft + (index / (data.length - 1)) * plotW;
    },
    [data.length, plotW]
  );

  const getY = useCallback(
    (val: number) => {
      const span = maxVal - minVal || 1;
      return padTop + plotH - ((val - minVal) / span) * plotH;
    },
    [minVal, maxVal, plotH]
  );

  const portfolioPolyline = useMemo(() => {
    return data
      .map((pt, idx) => {
        const yVal =
          effectiveMode === 'NAV' ? pt.portfolioValue : pt.portfolioReturnPct;
        return `${getX(idx).toFixed(1)},${getY(yVal).toFixed(1)}`;
      })
      .join(' ');
  }, [data, effectiveMode, getX, getY]);

  const portfolioAreaPath = useMemo(() => {
    if (data.length === 0) return '';
    const firstX = getX(0).toFixed(1);
    const lastX = getX(data.length - 1).toFixed(1);
    const bottomY = (padTop + plotH).toFixed(1);
    return `M ${firstX},${bottomY} L ${portfolioPolyline.replace(
      / /g,
      ' L '
    )} L ${lastX},${bottomY} Z`;
  }, [data.length, getX, plotH, portfolioPolyline]);

  const benchmarkPolyline = useMemo(() => {
    if (benchmark === 'NONE') return '';
    return data
      .map((pt, idx) => {
        const yVal = pt.benchmarkReturnPct[benchmark];
        return `${getX(idx).toFixed(1)},${getY(yVal).toFixed(1)}`;
      })
      .join(' ');
  }, [data, benchmark, getX, getY]);

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!containerRef.current || data.length === 0) return;
    const rect = containerRef.current.getBoundingClientRect();
    const relX = ((e.clientX - rect.left) / rect.width) * width;
    const clampedX = Math.max(padLeft, Math.min(padLeft + plotW, relX));
    const ratio = (clampedX - padLeft) / plotW;
    const idx = Math.round(ratio * (data.length - 1));
    setHoverIndex(Math.max(0, Math.min(data.length - 1, idx)));
  };

  const activeX =
    hoverIndex !== null ? getX(hoverIndex) : getX(data.length - 1);
  const activeYVal = activePoint
    ? effectiveMode === 'NAV'
      ? activePoint.portfolioValue
      : activePoint.portfolioReturnPct
    : 0;
  const activeY = getY(activeYVal);

  return (
    <div
      style={{
        backgroundColor: t.cardBg,
        borderColor: t.borderDefault,
      }}
      className="border rounded flex flex-col h-full transition-colors duration-150"
    >
      {/* Header & Controls */}
      <div
        style={{ borderColor: t.borderDefault }}
        className="px-4 py-3 border-b flex flex-wrap items-center justify-between gap-2.5"
      >
        <div>
          <h2
            style={{ color: t.textPrimary }}
            className="text-[13.5px] font-semibold tracking-tight"
          >
            Portfolio Performance
          </h2>
          <p
            style={{ color: t.textSecondary }}
            className="text-[11px] mt-0.5"
          >
            {portfolioLabel} · {marketLabel} · Time-weighted trajectory
          </p>
        </div>

        {/* Unit Mode, Benchmark Dropdown, Timeframe Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* NAV ($) vs RETURN (%) Toggle */}
          <div
            style={{
              backgroundColor: t.recessedBg,
              borderColor: t.borderDefault,
            }}
            className="flex items-center p-0.5 rounded border"
          >
            <button
              type="button"
              onClick={() => {
                if (benchmark !== 'NONE') onBenchmarkChange('NONE');
                onDisplayModeChange('NAV');
              }}
              style={
                effectiveMode === 'NAV'
                  ? {
                      backgroundColor: t.accentBg,
                      color: t.accentText,
                    }
                  : { color: t.textSecondary }
              }
              className="px-2 py-0.5 rounded text-[11px] font-mono font-medium transition-colors"
            >
              NAV ($)
            </button>
            <button
              type="button"
              onClick={() => onDisplayModeChange('RETURN_PCT')}
              style={
                effectiveMode === 'RETURN_PCT'
                  ? {
                      backgroundColor: t.accentBg,
                      color: t.accentText,
                    }
                  : { color: t.textSecondary }
              }
              className="px-2 py-0.5 rounded text-[11px] font-mono font-medium transition-colors"
            >
              RETURN (%)
            </button>
          </div>

          {/* Benchmark Comparison Dropdown */}
          <div className="relative">
            <label htmlFor="pims-benchmark-dropdown" className="sr-only">
              Benchmark Comparison
            </label>
            <select
              id="pims-benchmark-dropdown"
              value={benchmark}
              onChange={(e) => onBenchmarkChange(e.target.value as BenchmarkId)}
              style={{
                backgroundColor: t.recessedBg,
                borderColor: t.borderDefault,
                color: t.textPrimary,
              }}
              className="appearance-none text-[11.5px] font-medium pl-2.5 pr-6 py-1 rounded border focus:outline-none cursor-pointer"
            >
              {(Object.keys(BENCHMARK_LABELS) as BenchmarkId[]).map((bId) => (
                <option
                  key={bId}
                  value={bId}
                  style={{
                    backgroundColor: t.cardBg,
                    color: t.textPrimary,
                  }}
                >
                  Benchmark: {BENCHMARK_LABELS[bId]}
                </option>
              ))}
            </select>
            <ChevronDown
              style={{ color: t.textSecondary }}
              className="w-3 h-3 pointer-events-none absolute right-2 top-1/2 -translate-y-1/2"
            />
          </div>

          {/* Timeframe Selector Buttons */}
          <div
            role="group"
            aria-label="Chart timeframe"
            style={{
              backgroundColor: t.recessedBg,
              borderColor: t.borderDefault,
            }}
            className="flex items-center p-0.5 rounded border"
          >
            {timeRanges.map((tf) => {
              const active = timeRange === tf;
              return (
                <button
                  key={tf}
                  type="button"
                  onClick={() => onTimeRangeChange(tf)}
                  style={
                    active
                      ? {
                          backgroundColor: t.accentBg,
                          color: t.accentText,
                        }
                      : { color: t.textSecondary }
                  }
                  className="px-2 py-0.5 rounded text-[11px] font-mono font-medium transition-colors"
                >
                  {tf}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Crosshair Readout Bar */}
      {activePoint && (
        <div
          style={{
            backgroundColor: t.secondaryBg,
            borderColor: t.borderDefault,
          }}
          className="px-4 py-2 border-b flex flex-wrap items-center justify-between gap-3 text-[11.5px] tabular-nums"
        >
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <span style={{ color: t.textMuted }} className="mr-1.5 font-mono">
                DATE:
              </span>
              <span
                style={{ color: t.textPrimary }}
                className="font-mono font-semibold"
              >
                {activePoint.label}
              </span>
            </div>
            <div>
              <span style={{ color: t.textMuted }} className="mr-1.5 font-mono">
                PORTFOLIO NAV:
              </span>
              <span
                style={{ color: t.textPrimary }}
                className="font-mono font-semibold"
              >
                {formatUsd(activePoint.portfolioValue)}
              </span>
            </div>
            <div>
              <span style={{ color: t.textMuted }} className="mr-1.5 font-mono">
                {timeRange} RETURN:
              </span>
              <span
                style={{
                  color:
                    activePoint.portfolioReturnPct >= 0
                      ? t.gainText
                      : t.lossText,
                }}
                className="font-mono font-semibold"
              >
                {formatSignedPct(activePoint.portfolioReturnPct)}
              </span>
            </div>
            {benchmark !== 'NONE' && (
              <>
                <div>
                  <span
                    style={{ color: t.textMuted }}
                    className="mr-1.5 font-mono"
                  >
                    {BENCHMARK_LABELS[benchmark].toUpperCase()}:
                  </span>
                  <span
                    style={{ color: t.textSecondary }}
                    className="font-mono font-medium"
                  >
                    {formatSignedPct(activePoint.benchmarkReturnPct[benchmark])}
                  </span>
                </div>
                <div>
                  <span
                    style={{ color: t.textMuted }}
                    className="mr-1.5 font-mono"
                  >
                    ALPHA SPREAD:
                  </span>
                  {(() => {
                    const alpha =
                      activePoint.portfolioReturnPct -
                      activePoint.benchmarkReturnPct[benchmark];
                    return (
                      <span
                        style={{
                          color: alpha >= 0 ? t.gainText : t.lossText,
                        }}
                        className="font-mono font-semibold"
                      >
                        {formatSignedPct(alpha)}
                      </span>
                    );
                  })()}
                </div>
              </>
            )}
          </div>

          <div className="flex items-center gap-3 text-[11px]">
            <span
              style={{ color: t.textSecondary }}
              className="flex items-center gap-1.5"
            >
              <span
                className="w-2.5 h-0.5 inline-block"
                style={{ backgroundColor: lineStroke }}
              />
              Portfolio
            </span>
            {benchmark !== 'NONE' && (
              <span
                style={{ color: t.textMuted }}
                className="flex items-center gap-1.5"
              >
                <span
                  style={{ borderColor: t.textMuted }}
                  className="w-2.5 h-0 border-t border-dashed inline-block"
                />
                {BENCHMARK_LABELS[benchmark]}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Main SVG Performance Canvas */}
      <div
        ref={containerRef}
        className="relative flex-1 min-h-[260px] px-2 py-2 select-none"
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full cursor-crosshair"
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setHoverIndex(null)}
          role="img"
          aria-label="Portfolio performance historical chart"
        >
          {/* Dashed Horizontal Gridlines */}
          {yTicks.map((tick, idx) => {
            const y = getY(tick);
            const label =
              effectiveMode === 'NAV'
                ? formatUsd(tick, true)
                : `${tick >= 0 ? '+' : ''}${tick.toFixed(1)}%`;
            return (
              <g key={idx}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={padLeft + plotW}
                  y2={y}
                  stroke={t.gridLine}
                  strokeWidth="1"
                  strokeDasharray="3 3"
                />
                <text
                  x={padLeft + plotW + 8}
                  y={y + 3.5}
                  fill={t.textMuted}
                  fontSize="10"
                  fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace"
                >
                  {label}
                </text>
              </g>
            );
          })}

          {/* Zero Reference Line */}
          {effectiveMode === 'RETURN_PCT' && minVal < 0 && maxVal > 0 && (
            <line
              x1={padLeft}
              y1={getY(0)}
              x2={padLeft + plotW}
              y2={getY(0)}
              stroke={t.borderActive}
              strokeWidth="1"
            />
          )}

          {/* X-Axis Labels */}
          {data.map((pt, idx) => {
            const step = Math.max(1, Math.floor(data.length / 6));
            if (idx % step !== 0 && idx !== data.length - 1) return null;
            const x = getX(idx);
            return (
              <text
                key={pt.label + idx}
                x={x}
                y={height - 8}
                textAnchor={
                  idx === 0
                    ? 'start'
                    : idx === data.length - 1
                    ? 'end'
                    : 'middle'
                }
                fill={t.textMuted}
                fontSize="10"
                fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace"
              >
                {pt.label}
              </text>
            );
          })}

          {/* Area Fill */}
          <path d={portfolioAreaPath} fill={areaFill} />

          {/* Dashed Benchmark Comparison Curve */}
          {benchmark !== 'NONE' && (
            <polyline
              fill="none"
              stroke={t.textMuted}
              strokeWidth="1.5"
              strokeDasharray="4 3"
              points={benchmarkPolyline}
            />
          )}

          {/* Portfolio Trajectory Curve */}
          <polyline
            fill="none"
            stroke={lineStroke}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={portfolioPolyline}
          />

          {/* Vertical Crosshair & Data Node */}
          {hoverIndex !== null && activePoint && (
            <g>
              <line
                x1={activeX}
                y1={padTop}
                x2={activeX}
                y2={padTop + plotH}
                stroke={t.crosshairStroke}
                strokeWidth="1"
                strokeDasharray="3 3"
              />
              <circle
                cx={activeX}
                cy={activeY}
                r="4"
                fill={t.cardBg}
                stroke={lineStroke}
                strokeWidth="2"
              />
            </g>
          )}
        </svg>

        {/* Floating Hover Tooltip */}
        {hoverIndex !== null && activePoint && (
          <div
            style={{
              backgroundColor: t.cardBg,
              borderColor: t.borderActive,
            }}
            className="pointer-events-none absolute top-3.5 left-5 border rounded px-3 py-2 text-[11px] shadow-lg tabular-nums"
          >
            <div
              style={{
                color: t.textSecondary,
                borderColor: t.borderDefault,
              }}
              className="font-mono border-b pb-1 mb-1"
            >
              {activePoint.label}
            </div>
            <div className="flex items-center justify-between gap-4">
              <span style={{ color: t.textSecondary }}>Portfolio NAV:</span>
              <span
                style={{ color: t.textPrimary }}
                className="font-mono font-semibold"
              >
                {formatUsd(activePoint.portfolioValue)}
              </span>
            </div>
            <div className="flex items-center justify-between gap-4 mt-0.5">
              <span style={{ color: t.textSecondary }}>
                {timeRange} Return:
              </span>
              <span
                style={{
                  color:
                    activePoint.portfolioReturnPct >= 0
                      ? t.gainText
                      : t.lossText,
                }}
                className="font-mono font-semibold"
              >
                {formatSignedPct(activePoint.portfolioReturnPct)}
              </span>
            </div>
            {benchmark !== 'NONE' && (
              <>
                <div className="flex items-center justify-between gap-4 mt-0.5">
                  <span style={{ color: t.textSecondary }}>
                    {BENCHMARK_LABELS[benchmark]}:
                  </span>
                  <span
                    style={{ color: t.textPrimary }}
                    className="font-mono"
                  >
                    {formatSignedPct(
                      activePoint.benchmarkReturnPct[benchmark]
                    )}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4 mt-0.5">
                  <span style={{ color: t.textSecondary }}>Alpha Spread:</span>
                  {(() => {
                    const alpha =
                      activePoint.portfolioReturnPct -
                      activePoint.benchmarkReturnPct[benchmark];
                    return (
                      <span
                        style={{
                          color: alpha >= 0 ? t.gainText : t.lossText,
                        }}
                        className="font-mono font-semibold"
                      >
                        {formatSignedPct(alpha)}
                      </span>
                    );
                  })()}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ----------------------------------------------------------------------------
// F. ROW 2 RIGHT (4 COLS) — MARKET OVERVIEW STACKED PANEL
// ----------------------------------------------------------------------------

interface MarketOverviewPanelProps {
  selectedMarket: MarketSegment;
  onSelectMarket: (market: MarketSegment) => void;
  t: ThemeTokens;
}

const MarketOverviewPanel: React.FC<MarketOverviewPanelProps> = ({
  selectedMarket,
  onSelectMarket,
  t,
}) => {
  return (
    <div
      style={{
        backgroundColor: t.cardBg,
        borderColor: t.borderDefault,
      }}
      className="border rounded flex flex-col h-full transition-colors duration-150"
    >
      {/* Header */}
      <div
        style={{ borderColor: t.borderDefault }}
        className="px-4 py-3 border-b flex items-center justify-between gap-2"
      >
        <div>
          <h2
            style={{ color: t.textPrimary }}
            className="text-[13.5px] font-semibold tracking-tight"
          >
            Market Regimes &amp; Indices
          </h2>
          <p style={{ color: t.textSecondary }} className="text-[11px] mt-0.5">
            Sample EOD benchmarks &amp; breadth strength
          </p>
        </div>

        {selectedMarket !== 'ALL' && (
          <button
            type="button"
            onClick={() => onSelectMarket('ALL')}
            style={{
              backgroundColor: t.accentBg,
              color: t.accentText,
              borderColor: t.accentBorder,
            }}
            className="text-[10.5px] font-mono px-2 py-0.5 rounded border"
          >
            All Markets
          </button>
        )}
      </div>

      {/* Stacked Market Sections: Cryptocurrency, US Equities, Indonesian Stocks */}
      <div
        style={{ borderColor: t.borderDefault }}
        className="flex-1 divide-y flex flex-col justify-between"
      >
        {MARKET_REGIME_GROUPS.map((group) => {
          const isSelected = selectedMarket === group.market;
          const marketBadge = getMarketBadgeColors(group.market, t.mode);

          return (
            <div
              key={group.market}
              onClick={() =>
                onSelectMarket(isSelected ? 'ALL' : group.market)
              }
              style={{
                borderColor: t.borderDefault,
                backgroundColor: isSelected ? t.secondaryBg : 'transparent',
              }}
              className="px-4 py-3 flex-1 flex flex-col justify-center cursor-pointer transition-colors"
            >
              {/* Market Group Title + Regime Pill */}
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <span
                    style={{
                      backgroundColor: marketBadge.bg,
                      color: marketBadge.text,
                      borderColor: marketBadge.border,
                    }}
                    className="text-[9.5px] font-mono font-semibold px-1.5 py-0.5 rounded border"
                  >
                    {marketBadge.label}
                  </span>
                  <span
                    style={{ color: t.textPrimary }}
                    className="text-[12px] font-semibold"
                  >
                    {group.title}
                  </span>
                </div>
                <span
                  style={{
                    backgroundColor: t.recessedBg,
                    borderColor: t.borderDefault,
                    color: t.textMuted,
                  }}
                  className="text-[9.5px] font-mono px-1.5 py-0.5 rounded border"
                >
                  {group.regimeTag}
                </span>
              </div>

              {/* 2 Representative Indices / Benchmarks per Market */}
              <div className="space-y-2">
                {group.indices.map((idx) => {
                  const isPos = idx.changePct >= 0;
                  return (
                    <div key={idx.id}>
                      <div className="flex items-center justify-between gap-2 text-[11.5px] tabular-nums">
                        <div className="min-w-0">
                          <span
                            style={{ color: t.textPrimary }}
                            className="font-mono font-semibold"
                          >
                            {idx.symbol}
                          </span>
                          <span
                            style={{ color: t.textMuted }}
                            className="text-[10.5px] ml-1.5 hidden sm:inline"
                          >
                            {idx.name}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0 font-mono">
                          <span
                            style={{ color: t.textPrimary }}
                            className="font-medium"
                          >
                            {idx.lastClose}
                          </span>
                          <span
                            style={{
                              color: isPos ? t.gainText : t.lossText,
                              backgroundColor: isPos ? t.gainBg : t.lossBg,
                              borderColor: isPos ? t.gainBorder : t.lossBorder,
                            }}
                            className="text-[10px] font-semibold px-1.5 py-0.2 rounded border min-w-[56px] text-right"
                          >
                            {formatSignedPct(idx.changePct)}
                          </span>
                        </div>
                      </div>

                      {/* Horizontal Market Breadth / Momentum Strength Bar */}
                      <div className="mt-1 flex items-center gap-2">
                        <div
                          style={{ backgroundColor: t.trackBg }}
                          className="flex-1 h-1.5 rounded-xs overflow-hidden"
                        >
                          <div
                            style={{
                              width: `${idx.breadthPct}%`,
                              backgroundColor: isSelected
                                ? t.accentText
                                : isPos
                                ? t.gainText
                                : t.lossText,
                            }}
                            className="h-full transition-all duration-200"
                          />
                        </div>
                        <span
                          style={{ color: t.textMuted }}
                          className="text-[9.5px] font-mono tabular-nums shrink-0"
                        >
                          {idx.breadthLabel}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ----------------------------------------------------------------------------
// G. ROW 3 LEFT (4 COLS) — ASSET ALLOCATION CARD
// ----------------------------------------------------------------------------

interface AssetAllocationCardProps {
  slices: AllocationSlice[];
  totalValueUsd: number;
  dimension: AllocationDimension;
  onDimensionChange: (dim: AllocationDimension) => void;
  t: ThemeTokens;
}

const AssetAllocationCard: React.FC<AssetAllocationCardProps> = ({
  slices,
  totalValueUsd,
  dimension,
  onDimensionChange,
  t,
}) => {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const activeSlice = useMemo(
    () => slices.find((s) => s.id === hoveredId) ?? null,
    [slices, hoveredId]
  );

  const size = 156;
  const center = size / 2;
  const radius = 58;
  const strokeWidth = 16;
  const circumference = 2 * Math.PI * radius;

  const segments = useMemo(() => {
    let cumulativePct = 0;
    return slices.map((slice) => {
      const pct = Math.max(0, slice.allocationPct);
      const dashLength = (pct / 100) * circumference;
      const dashOffset = -((cumulativePct / 100) * circumference);
      cumulativePct += pct;
      return {
        ...slice,
        dashLength,
        dashOffset,
      };
    });
  }, [slices, circumference]);

  const dimensionTabs: { id: AllocationDimension; label: string }[] = [
    { id: 'ASSET_CLASS', label: 'Asset Class' },
    { id: 'MARKET', label: 'Market' },
    { id: 'TOP_ASSETS', label: 'Top Assets' },
  ];

  return (
    <div
      style={{
        backgroundColor: t.cardBg,
        borderColor: t.borderDefault,
      }}
      className="border rounded flex flex-col h-full transition-colors duration-150"
    >
      {/* Header + Segmented Tabs */}
      <div
        style={{ borderColor: t.borderDefault }}
        className="px-4 py-3 border-b flex items-center justify-between gap-2"
      >
        <div>
          <h2
            style={{ color: t.textPrimary }}
            className="text-[13.5px] font-semibold tracking-tight"
          >
            Asset Allocation
          </h2>
          <p style={{ color: t.textSecondary }} className="text-[10.5px]">
            NAV weight breakdown
          </p>
        </div>

        <div
          role="group"
          aria-label="Asset allocation breakdown dimension"
          style={{
            backgroundColor: t.recessedBg,
            borderColor: t.borderDefault,
          }}
          className="flex items-center p-0.5 rounded border"
        >
          {dimensionTabs.map((tab) => {
            const active = dimension === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => onDimensionChange(tab.id)}
                style={
                  active
                    ? {
                        backgroundColor: t.accentBg,
                        color: t.accentText,
                      }
                    : { color: t.textSecondary }
                }
                className="px-2 py-0.5 rounded text-[10.5px] font-medium transition-colors"
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* SVG Donut Chart + Structured Legend Table */}
      <div className="p-4 flex-1 flex flex-col justify-between gap-3">
        <div className="flex items-center justify-center py-1">
          <div className="relative w-[156px] h-[156px]">
            <svg
              width={size}
              height={size}
              viewBox={`0 0 ${size} ${size}`}
              className="-rotate-90"
              role="img"
              aria-label="Asset allocation donut chart"
            >
              <circle
                cx={center}
                cy={center}
                r={radius}
                fill="transparent"
                stroke={t.trackBg}
                strokeWidth={strokeWidth}
              />
              {segments.map((seg) => {
                const isDimmed = hoveredId !== null && hoveredId !== seg.id;
                return (
                  <circle
                    key={seg.id}
                    cx={center}
                    cy={center}
                    r={radius}
                    fill="transparent"
                    stroke={seg.color}
                    strokeWidth={
                      hoveredId === seg.id ? strokeWidth + 2.5 : strokeWidth
                    }
                    strokeDasharray={`${Math.max(
                      0,
                      seg.dashLength - 1.5
                    )} ${circumference}`}
                    strokeDashoffset={seg.dashOffset}
                    opacity={isDimmed ? 0.35 : 1}
                    className="transition-opacity duration-150 cursor-pointer"
                    onMouseEnter={() => setHoveredId(seg.id)}
                    onMouseLeave={() => setHoveredId(null)}
                  />
                );
              })}
            </svg>

            {/* Center Readout */}
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-3 pointer-events-none">
              <span
                style={{ color: t.textMuted }}
                className="text-[9.5px] font-semibold uppercase tracking-wider truncate max-w-[96px]"
              >
                {activeSlice ? activeSlice.label : 'Total NAV'}
              </span>
              <span
                style={{ color: t.textPrimary }}
                className="text-[15px] font-bold tabular-nums mt-0.5"
              >
                {activeSlice
                  ? `${activeSlice.allocationPct.toFixed(1)}%`
                  : formatUsd(totalValueUsd, true)}
              </span>
              <span
                style={{ color: t.textSecondary }}
                className="text-[10px] font-mono tabular-nums"
              >
                {activeSlice
                  ? formatUsd(activeSlice.marketValueUsd, true)
                  : `${slices.length} Sleeves`}
              </span>
            </div>
          </div>
        </div>

        {/* Structured Legend Table */}
        <div
          style={{ borderColor: t.borderDefault }}
          className="divide-y border-t"
        >
          {slices.map((slice) => {
            const isHovered = hoveredId === slice.id;
            return (
              <div
                key={slice.id}
                onMouseEnter={() => setHoveredId(slice.id)}
                onMouseLeave={() => setHoveredId(null)}
                style={{
                  borderColor: t.borderDefault,
                  backgroundColor: isHovered ? t.hoverBg : 'transparent',
                }}
                className="py-1.5 px-1.5 flex items-center justify-between gap-2 text-[11.5px] transition-colors cursor-default"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="w-2.5 h-2.5 rounded-xs shrink-0"
                    style={{ backgroundColor: slice.color }}
                  />
                  <span
                    style={{ color: t.textPrimary }}
                    className="font-medium truncate"
                  >
                    {slice.label}
                  </span>
                </div>

                <div className="flex items-center gap-3 shrink-0 tabular-nums font-mono">
                  <span
                    style={{ color: t.textSecondary }}
                    className="w-12 text-right"
                  >
                    {slice.allocationPct.toFixed(1)}%
                  </span>
                  <span
                    style={{ color: t.textPrimary }}
                    className="w-20 text-right font-medium"
                  >
                    {formatUsd(slice.marketValueUsd, true)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

// ----------------------------------------------------------------------------
// H. ROW 3 CENTER (4 COLS) — WATCHLIST CARD WITH INLINE RESEARCH DRAWER
// ----------------------------------------------------------------------------

interface WatchlistCardProps {
  selectedMarket: MarketSegment;
  searchQuery: string;
  t: ThemeTokens;
}

const WatchlistCard: React.FC<WatchlistCardProps> = ({
  selectedMarket,
  searchQuery,
  t,
}) => {
  const [items, setItems] = useState<WatchlistEntry[]>(INITIAL_WATCHLIST);
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);

  const visibleItems = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return items
      .filter((item) => {
        const matchesMarket =
          selectedMarket === 'ALL' ? true : item.market === selectedMarket;
        const matchesSearch =
          !q ||
          item.symbol.toLowerCase().includes(q) ||
          item.name.toLowerCase().includes(q);
        return matchesMarket && matchesSearch;
      })
      .sort((a, b) => Number(b.pinned) - Number(a.pinned));
  }, [items, selectedMarket, searchQuery]);

  const togglePin = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, pinned: !item.pinned } : item
      )
    );
  };

  return (
    <div
      style={{
        backgroundColor: t.cardBg,
        borderColor: t.borderDefault,
      }}
      className="border rounded flex flex-col h-full transition-colors duration-150"
    >
      {/* Header */}
      <div
        style={{ borderColor: t.borderDefault }}
        className="px-4 py-3 border-b flex items-center justify-between gap-2"
      >
        <div>
          <h2
            style={{ color: t.textPrimary }}
            className="text-[13.5px] font-semibold tracking-tight"
          >
            Watchlist
          </h2>
          <p style={{ color: t.textSecondary }} className="text-[10.5px]">
            Click symbol for fundamental &amp; technical snapshot
          </p>
        </div>
        <span
          style={{
            backgroundColor: t.recessedBg,
            borderColor: t.borderDefault,
            color: t.textSecondary,
          }}
          className="text-[10px] font-mono px-1.5 py-0.5 rounded border tabular-nums"
        >
          {visibleItems.length} SYMBOLS
        </span>
      </div>

      {/* Watchlist Rows */}
      <div
        style={{ borderColor: t.borderDefault }}
        className="divide-y flex-1"
      >
        {visibleItems.length === 0 ? (
          <div
            style={{ color: t.textMuted }}
            className="p-6 text-center text-[12px]"
          >
            No watchlist symbols match the active filter.
          </div>
        ) : (
          visibleItems.map((item) => {
            const isPos = item.dailyChangePct >= 0;
            const badge = getMarketBadgeColors(item.market, t.mode);
            const isOpen = selectedEntryId === item.id;

            return (
              <div
                key={item.id}
                onClick={() => setSelectedEntryId(isOpen ? null : item.id)}
                style={{
                  borderColor: t.borderDefault,
                  backgroundColor: isOpen ? t.secondaryBg : 'transparent',
                }}
                className="px-4 py-2.5 transition-colors cursor-pointer"
              >
                <div className="flex items-center justify-between gap-2.5">
                  {/* Left: Monogram + Symbol + Market Badge + Name */}
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div
                      style={{
                        backgroundColor: t.recessedBg,
                        borderColor: t.borderDefault,
                        color: t.textPrimary,
                      }}
                      className="w-8 h-8 rounded-full border flex items-center justify-center font-mono text-[10.5px] font-bold shrink-0"
                    >
                      {item.monogram}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span
                          style={{ color: t.textPrimary }}
                          className="font-mono text-[12px] font-semibold"
                        >
                          {item.symbol}
                        </span>
                        <span
                          style={{
                            backgroundColor: badge.bg,
                            color: badge.text,
                            borderColor: badge.border,
                          }}
                          className="text-[9px] font-mono font-semibold px-1 rounded border"
                        >
                          {badge.label}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => togglePin(e, item.id)}
                          aria-label={`Pin ${item.symbol}`}
                          title={item.pinned ? 'Unpin symbol' : 'Pin symbol'}
                        >
                          <Star
                            style={{
                              color: item.pinned ? t.accentText : t.textMuted,
                              fill: item.pinned ? t.accentText : 'none',
                            }}
                            className="w-3 h-3"
                          />
                        </button>
                      </div>
                      <div
                        style={{ color: t.textSecondary }}
                        className="text-[11px] truncate"
                      >
                        {item.name}
                      </div>
                    </div>
                  </div>

                  {/* Right: Sparkline + Sample Price & Daily % Change */}
                  <div className="flex items-center gap-2.5 shrink-0">
                    <Sparkline
                      values={item.sparkline}
                      strokeColor={isPos ? t.gainText : t.lossText}
                      dotFillColor={t.cardBg}
                      width={52}
                      height={22}
                      showEndDot={false}
                    />
                    <div className="text-right font-mono tabular-nums min-w-[78px]">
                      <div
                        style={{ color: t.textPrimary }}
                        className="text-[12px] font-semibold"
                      >
                        {item.priceFormatted}
                      </div>
                      {item.secondaryPriceNote && (
                        <div
                          style={{ color: t.textMuted }}
                          className="text-[9.5px]"
                        >
                          {item.secondaryPriceNote}
                        </div>
                      )}
                      <div
                        style={{ color: isPos ? t.gainText : t.lossText }}
                        className="text-[10.5px] font-medium"
                      >
                        {formatSignedPct(item.dailyChangePct)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Inline Non-Trading Fundamental & Technical Metric Drawer */}
                {isOpen && (
                  <div
                    style={{
                      backgroundColor: t.cardBg,
                      borderColor: t.borderActive,
                    }}
                    className="mt-2.5 p-2.5 rounded border text-[11px] space-y-2"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex items-center justify-between">
                      <span
                        style={{ color: t.accentText }}
                        className="font-mono text-[10px] font-semibold uppercase tracking-wider flex items-center gap-1"
                      >
                        <BarChart3 className="w-3 h-3" />
                        Research Snapshot (Read-Only)
                      </span>
                      <button
                        type="button"
                        onClick={() => setSelectedEntryId(null)}
                        style={{ color: t.textMuted }}
                        aria-label="Close snapshot"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-2 font-mono text-[10.5px] tabular-nums">
                      <div
                        style={{
                          backgroundColor: t.secondaryBg,
                          borderColor: t.borderDefault,
                        }}
                        className="px-2 py-1 rounded border"
                      >
                        <div style={{ color: t.textMuted }}>
                          {item.metrics.valuationMetricLabel}
                        </div>
                        <div
                          style={{ color: t.textPrimary }}
                          className="font-semibold"
                        >
                          {item.metrics.valuationMetricValue}
                        </div>
                      </div>
                      <div
                        style={{
                          backgroundColor: t.secondaryBg,
                          borderColor: t.borderDefault,
                        }}
                        className="px-2 py-1 rounded border"
                      >
                        <div style={{ color: t.textMuted }}>
                          RSI (14) / Beta
                        </div>
                        <div
                          style={{ color: t.textPrimary }}
                          className="font-semibold"
                        >
                          {item.metrics.rsi14.toFixed(1)} · β {item.metrics.beta}
                        </div>
                      </div>
                    </div>

                    <div
                      style={{ color: t.textSecondary }}
                      className="flex items-center justify-between text-[10px] font-mono"
                    >
                      <span>52W: {item.metrics.range52w}</span>
                      <span style={{ color: t.accentText }}>
                        {item.metrics.sma50Status}
                      </span>
                    </div>

                    <p
                      style={{ color: t.textSecondary }}
                      className="text-[10.5px] leading-snug"
                    >
                      {item.metrics.analyticalNote}
                    </p>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

// ----------------------------------------------------------------------------
// I. ROW 3 RIGHT (4 COLS) — RECENT ACTIVITY AUDIT LOG CARD
// ----------------------------------------------------------------------------

interface RecentActivityCardProps {
  activities: ActivityLogEntry[];
  t: ThemeTokens;
}

const RecentActivityCard: React.FC<RecentActivityCardProps> = ({
  activities,
  t,
}) => {
  const getBadgeMeta = (category: ActivityCategory) => {
    switch (category) {
      case 'TRANSACTION_RECORDED':
        return {
          icon: CheckCircle2,
          label: 'TXN RECORDED',
          color: t.gainText,
          bg: t.gainBg,
          border: t.gainBorder,
        };
      case 'ALLOCATION_REBALANCED':
        return {
          icon: PieChart,
          label: 'REBALANCED',
          color: t.accentText,
          bg: t.accentBg,
          border: t.accentBorder,
        };
      case 'ASSET_ADDED':
        return {
          icon: FileText,
          label: 'ASSET ADDED',
          color: t.chartPalette[1],
          bg: t.secondaryBg,
          border: t.borderActive,
        };
      case 'WATCHLIST_UPDATED':
        return {
          icon: Eye,
          label: 'WATCHLIST',
          color: t.textSecondary,
          bg: t.recessedBg,
          border: t.borderDefault,
        };
    }
  };

  return (
    <div
      style={{
        backgroundColor: t.cardBg,
        borderColor: t.borderDefault,
      }}
      className="border rounded flex flex-col h-full transition-colors duration-150"
    >
      {/* Header */}
      <div
        style={{ borderColor: t.borderDefault }}
        className="px-4 py-3 border-b flex items-center justify-between gap-2"
      >
        <div>
          <h2
            style={{ color: t.textPrimary }}
            className="text-[13.5px] font-semibold tracking-tight"
          >
            Recent Activity
          </h2>
          <p style={{ color: t.textSecondary }} className="text-[10.5px]">
            Chronological portfolio audit log
          </p>
        </div>
        <span
          style={{
            backgroundColor: t.recessedBg,
            borderColor: t.borderDefault,
            color: t.textSecondary,
          }}
          className="text-[10px] font-mono px-1.5 py-0.5 rounded border"
        >
          AUDIT LEDGER
        </span>
      </div>

      {/* Audit Log Rows */}
      <div
        style={{ borderColor: t.borderDefault }}
        className="divide-y flex-1"
      >
        {activities.map((act) => {
          const meta = getBadgeMeta(act.category);
          const Icon = meta.icon;

          return (
            <div
              key={act.id}
              style={{ borderColor: t.borderDefault }}
              className="px-4 py-2.5 flex items-start gap-2.5 transition-colors"
            >
              <div
                style={{
                  backgroundColor: meta.bg,
                  borderColor: meta.border,
                  color: meta.color,
                }}
                className="w-7 h-7 rounded border flex items-center justify-center shrink-0 mt-0.5"
              >
                <Icon className="w-3.5 h-3.5" />
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span
                    style={{ color: t.textPrimary }}
                    className="text-[12px] font-semibold truncate"
                  >
                    {act.title}
                  </span>
                </div>
                <p
                  style={{ color: t.textSecondary }}
                  className="text-[11px] mt-0.5 leading-snug line-clamp-1"
                >
                  {act.description}
                </p>
                <div className="flex flex-wrap items-center gap-1.5 mt-1">
                  <span
                    style={{
                      backgroundColor: meta.bg,
                      borderColor: meta.border,
                      color: meta.color,
                    }}
                    className="text-[9px] font-mono font-semibold px-1.5 py-0.2 rounded border"
                  >
                    {meta.label}
                  </span>
                  <span
                    style={{
                      backgroundColor: t.recessedBg,
                      borderColor: t.borderDefault,
                      color: t.textSecondary,
                    }}
                    className="text-[9.5px] font-mono px-1.5 py-0.2 rounded border"
                  >
                    {act.portfolioTag}
                  </span>
                  <span
                    style={{ color: t.textMuted }}
                    className="text-[10px] font-mono tabular-nums"
                  >
                    {act.timestamp}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ----------------------------------------------------------------------------
// J. ROW 4 — FULL-WIDTH HOLDINGS TABLE WITH RECONCILED SUMMARY FOOTER
// ----------------------------------------------------------------------------

interface HoldingsTableProps {
  holdings: ComputedHolding[];
  selectedMarket: MarketSegment;
  onSelectMarket: (m: MarketSegment) => void;
  searchQuery: string;
  onSearchQueryChange: (q: string) => void;
  t: ThemeTokens;
}

const HoldingsTable: React.FC<HoldingsTableProps> = ({
  holdings,
  selectedMarket,
  onSelectMarket,
  searchQuery,
  onSearchQueryChange,
  t,
}) => {
  const [sortField, setSortField] = useState<SortField>('marketValue');
  const [sortDir, setSortDir] = useState<SortDirection>('desc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir(
        field === 'name' || field === 'symbol' || field === 'market'
          ? 'asc'
          : 'desc'
      );
    }
  };

  const filteredAndSorted = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return holdings
      .filter((h) => {
        if (!q) return true;
        return (
          h.symbol.toLowerCase().includes(q) ||
          h.name.toLowerCase().includes(q) ||
          h.sector.toLowerCase().includes(q)
        );
      })
      .sort((a, b) => {
        let cmp = 0;
        switch (sortField) {
          case 'name':
            cmp = a.name.localeCompare(b.name);
            break;
          case 'symbol':
            cmp = a.symbol.localeCompare(b.symbol);
            break;
          case 'market':
            cmp = a.market.localeCompare(b.market);
            break;
          case 'quantity':
            cmp = a.quantity - b.quantity;
            break;
          case 'avgCost':
            cmp = a.avgCostUsd - b.avgCostUsd;
            break;
          case 'currentPrice':
            cmp = a.currentPriceUsd - b.currentPriceUsd;
            break;
          case 'marketValue':
            cmp = a.marketValueUsd - b.marketValueUsd;
            break;
          case 'unrealizedPnL':
            cmp = a.unrealizedPnLUsd - b.unrealizedPnLUsd;
            break;
          case 'allocationPct':
            cmp = a.allocationPct - b.allocationPct;
            break;
        }
        return sortDir === 'asc' ? cmp : -cmp;
      });
  }, [holdings, searchQuery, sortField, sortDir]);

  // Reconciled Footer Totals for displayed rows
  const footerTotals = useMemo(() => {
    const totalCost = filteredAndSorted.reduce(
      (s, r) => s + r.costBasisUsd,
      0
    );
    const totalMarketVal = filteredAndSorted.reduce(
      (s, r) => s + r.marketValueUsd,
      0
    );
    const totalUnrealized = totalMarketVal - totalCost;
    const totalUnrealizedPct =
      totalCost > 0 ? (totalUnrealized / totalCost) * 100 : 0;
    const totalAlloc = filteredAndSorted.reduce(
      (s, r) => s + r.allocationPct,
      0
    );

    return {
      totalCost,
      totalMarketVal,
      totalUnrealized,
      totalUnrealizedPct,
      totalAlloc,
    };
  }, [filteredAndSorted]);

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return (
        <ArrowUpDown
          style={{ color: t.textMuted }}
          className="w-3 h-3 inline ml-1 opacity-60"
        />
      );
    }
    return sortDir === 'asc' ? (
      <ArrowUp
        style={{ color: t.accentText }}
        className="w-3 h-3 inline ml-1"
      />
    ) : (
      <ArrowDown
        style={{ color: t.accentText }}
        className="w-3 h-3 inline ml-1"
      />
    );
  };

  const marketPills: { id: MarketSegment; label: string }[] = [
    { id: 'ALL', label: 'All' },
    { id: 'US', label: 'US' },
    { id: 'IDX', label: 'IDX' },
    { id: 'CRYPTO', label: 'Crypto' },
  ];

  return (
    <section
      aria-label="Portfolio Holdings Table"
      style={{
        backgroundColor: t.cardBg,
        borderColor: t.borderDefault,
      }}
      className="border rounded flex flex-col transition-colors duration-150"
    >
      {/* Header Bar */}
      <div
        style={{ borderColor: t.borderDefault }}
        className="px-4 py-3 border-b flex flex-wrap items-center justify-between gap-2.5"
      >
        <div className="flex items-center gap-2.5">
          <h2
            style={{ color: t.textPrimary }}
            className="text-[13.5px] font-semibold tracking-tight"
          >
            Portfolio Holdings
          </h2>
          <span
            style={{
              backgroundColor: t.recessedBg,
              borderColor: t.borderDefault,
              color: t.textSecondary,
            }}
            className="text-[11px] font-mono px-2 py-0.5 rounded border tabular-nums"
          >
            {filteredAndSorted.length} POSITIONS
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Market Filter Pills */}
          <div
            style={{
              backgroundColor: t.recessedBg,
              borderColor: t.borderDefault,
            }}
            className="flex items-center p-0.5 rounded border text-[11px]"
          >
            {marketPills.map((pill) => {
              const active = selectedMarket === pill.id;
              return (
                <button
                  key={pill.id}
                  type="button"
                  onClick={() => onSelectMarket(pill.id)}
                  style={
                    active
                      ? {
                          backgroundColor: t.accentBg,
                          color: t.accentText,
                        }
                      : { color: t.textSecondary }
                  }
                  className="px-2.5 py-0.5 rounded font-medium transition-colors"
                >
                  {pill.label}
                </button>
              );
            })}
          </div>

          {/* Quick Search Input */}
          <div className="relative w-48">
            <SlidersHorizontal
              style={{ color: t.textMuted }}
              className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchQueryChange(e.target.value)}
              placeholder="Filter ticker or sector..."
              aria-label="Filter holdings table"
              style={{
                backgroundColor: t.recessedBg,
                borderColor: t.borderDefault,
                color: t.textPrimary,
              }}
              className="w-full text-[11.5px] pl-7 pr-2.5 py-1 rounded border focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Horizontal Scroll Container */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr
              style={{
                backgroundColor: t.secondaryBg,
                borderColor: t.borderDefault,
                color: t.textSecondary,
              }}
              className="border-b text-[10.5px] font-semibold uppercase tracking-[0.06em] select-none"
            >
              <th className="py-2.5 pl-4 pr-2 whitespace-nowrap">
                <button
                  type="button"
                  onClick={() => handleSort('name')}
                  className="hover:opacity-80"
                >
                  Asset {renderSortIcon('name')}
                </button>
              </th>
              <th className="py-2.5 px-2 whitespace-nowrap">
                <button
                  type="button"
                  onClick={() => handleSort('symbol')}
                  className="hover:opacity-80"
                >
                  Symbol {renderSortIcon('symbol')}
                </button>
              </th>
              <th className="py-2.5 px-2 whitespace-nowrap">
                <button
                  type="button"
                  onClick={() => handleSort('market')}
                  className="hover:opacity-80"
                >
                  Market {renderSortIcon('market')}
                </button>
              </th>
              <th className="py-2.5 px-2 text-right whitespace-nowrap">
                <button
                  type="button"
                  onClick={() => handleSort('quantity')}
                  className="hover:opacity-80"
                >
                  Quantity {renderSortIcon('quantity')}
                </button>
              </th>
              <th className="py-2.5 px-2 text-right whitespace-nowrap">
                <button
                  type="button"
                  onClick={() => handleSort('avgCost')}
                  className="hover:opacity-80"
                >
                  Avg Cost {renderSortIcon('avgCost')}
                </button>
              </th>
              <th className="py-2.5 px-2 text-right whitespace-nowrap">
                <button
                  type="button"
                  onClick={() => handleSort('currentPrice')}
                  className="hover:opacity-80"
                >
                  Current Price {renderSortIcon('currentPrice')}
                </button>
              </th>
              <th className="py-2.5 px-2 text-right whitespace-nowrap">
                <button
                  type="button"
                  onClick={() => handleSort('marketValue')}
                  className="hover:opacity-80"
                >
                  Market Value {renderSortIcon('marketValue')}
                </button>
              </th>
              <th className="py-2.5 px-2 text-right whitespace-nowrap">
                <button
                  type="button"
                  onClick={() => handleSort('unrealizedPnL')}
                  className="hover:opacity-80"
                >
                  Unrealized P&amp;L {renderSortIcon('unrealizedPnL')}
                </button>
              </th>
              <th className="py-2.5 pl-2 pr-4 text-right whitespace-nowrap">
                <button
                  type="button"
                  onClick={() => handleSort('allocationPct')}
                  className="hover:opacity-80"
                >
                  Allocation {renderSortIcon('allocationPct')}
                </button>
              </th>
            </tr>
          </thead>

          <tbody
            style={{ borderColor: t.borderDefault }}
            className="divide-y text-[12px]"
          >
            {filteredAndSorted.length === 0 ? (
              <tr>
                <td
                  colSpan={9}
                  style={{ color: t.textMuted }}
                  className="py-8 text-center text-[12px]"
                >
                  No holdings match the active portfolio, market, or search filter.
                </td>
              </tr>
            ) : (
              filteredAndSorted.map((row) => {
                const badge = getMarketBadgeColors(row.market, t.mode);
                const isGain = row.unrealizedPnLUsd >= 0;

                return (
                  <tr
                    key={row.id}
                    style={{ borderColor: t.borderDefault }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = t.hoverBg;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                    className="transition-colors"
                  >
                    {/* Asset */}
                    <td className="py-2.5 pl-4 pr-2 min-w-[180px]">
                      <div
                        style={{ color: t.textPrimary }}
                        className="font-medium truncate"
                      >
                        {row.name}
                      </div>
                      <div
                        style={{ color: t.textMuted }}
                        className="text-[10.5px] truncate"
                      >
                        {row.sector}
                      </div>
                    </td>

                    {/* Symbol */}
                    <td
                      style={{ color: t.textPrimary }}
                      className="py-2.5 px-2 font-mono font-semibold whitespace-nowrap"
                    >
                      {row.symbol}
                    </td>

                    {/* Market */}
                    <td className="py-2.5 px-2 whitespace-nowrap">
                      <span
                        style={{
                          backgroundColor: badge.bg,
                          color: badge.text,
                          borderColor: badge.border,
                        }}
                        className="inline-block text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded border"
                      >
                        {badge.label}
                      </span>
                    </td>

                    {/* Quantity */}
                    <td
                      style={{ color: t.textSecondary }}
                      className="py-2.5 px-2 text-right font-mono tabular-nums whitespace-nowrap"
                    >
                      {formatQuantity(row.quantity, row.market)}
                    </td>

                    {/* Avg Cost */}
                    <td
                      style={{ color: t.textSecondary }}
                      className="py-2.5 px-2 text-right font-mono tabular-nums whitespace-nowrap"
                    >
                      <div>
                        {row.avgCostUsd < 1
                          ? `$${row.avgCostUsd.toFixed(4)}`
                          : formatUsd(row.avgCostUsd)}
                      </div>
                      {row.nativeCurrency === 'IDR' && row.nativeAvgCostIdr && (
                        <div
                          style={{ color: t.textMuted }}
                          className="text-[10px]"
                        >
                          Rp {row.nativeAvgCostIdr.toLocaleString('en-US')}
                        </div>
                      )}
                    </td>

                    {/* Current Price */}
                    <td className="py-2.5 px-2 text-right font-mono tabular-nums whitespace-nowrap">
                      <div
                        style={{ color: t.textPrimary }}
                        className="font-medium"
                      >
                        {row.currentPriceUsd < 1
                          ? `$${row.currentPriceUsd.toFixed(4)}`
                          : formatUsd(row.currentPriceUsd)}
                      </div>
                      {row.nativeCurrency === 'IDR' && row.nativePriceIdr && (
                        <div
                          style={{ color: t.textMuted }}
                          className="text-[10px]"
                        >
                          Rp {row.nativePriceIdr.toLocaleString('en-US')}
                        </div>
                      )}
                    </td>

                    {/* Market Value */}
                    <td
                      style={{ color: t.textPrimary }}
                      className="py-2.5 px-2 text-right font-mono font-semibold tabular-nums whitespace-nowrap"
                    >
                      {formatUsd(row.marketValueUsd)}
                    </td>

                    {/* Unrealized P&L */}
                    <td className="py-2.5 px-2 text-right font-mono tabular-nums whitespace-nowrap">
                      <div
                        style={{
                          color: isGain ? t.gainText : t.lossText,
                        }}
                        className="font-semibold"
                      >
                        {formatSignedUsd(row.unrealizedPnLUsd)}
                      </div>
                      <div
                        style={{
                          color: isGain ? t.gainText : t.lossText,
                        }}
                        className="text-[10.5px] opacity-90"
                      >
                        {formatSignedPct(row.unrealizedPnLPct)}
                      </div>
                    </td>

                    {/* Allocation + Visual Progress Bar */}
                    <td className="py-2.5 pl-2 pr-4 text-right font-mono tabular-nums whitespace-nowrap">
                      <div className="flex items-center justify-end gap-2">
                        <div
                          style={{ backgroundColor: t.trackBg }}
                          className="w-14 h-1.5 rounded-xs overflow-hidden hidden sm:block"
                        >
                          <div
                            style={{
                              width: `${Math.min(100, row.allocationPct * 4)}%`,
                              backgroundColor: t.accentText,
                            }}
                            className="h-full"
                          />
                        </div>
                        <span
                          style={{ color: t.textPrimary }}
                          className="w-12 font-medium"
                        >
                          {row.allocationPct.toFixed(2)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>

          {/* Reconciled Summary Footer Row */}
          {filteredAndSorted.length > 0 && (
            <tfoot>
              <tr
                style={{
                  backgroundColor: t.secondaryBg,
                  borderColor: t.borderActive,
                  color: t.textPrimary,
                }}
                className="border-t-2 text-[11.5px] font-mono tabular-nums"
              >
                <td
                  colSpan={4}
                  className="py-2.5 pl-4 pr-2 font-sans font-semibold"
                >
                  Reconciled Holdings Subtotal ({filteredAndSorted.length}{' '}
                  Positions)
                </td>
                <td
                  style={{ color: t.textSecondary }}
                  className="py-2.5 px-2 text-right whitespace-nowrap"
                >
                  Basis: {formatUsd(footerTotals.totalCost)}
                </td>
                <td className="py-2.5 px-2 text-right" />
                <td className="py-2.5 px-2 text-right font-bold whitespace-nowrap">
                  {formatUsd(footerTotals.totalMarketVal)}
                </td>
                <td
                  style={{
                    color:
                      footerTotals.totalUnrealized >= 0
                        ? t.gainText
                        : t.lossText,
                  }}
                  className="py-2.5 px-2 text-right font-bold whitespace-nowrap"
                >
                  {formatSignedUsd(footerTotals.totalUnrealized)} (
                  {formatSignedPct(footerTotals.totalUnrealizedPct)})
                </td>
                <td className="py-2.5 pl-2 pr-4 text-right font-bold whitespace-nowrap">
                  {footerTotals.totalAlloc.toFixed(2)}%
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </section>
  );
};

// ============================================================================
// 6. MAIN OVERVIEW DASHBOARD & ROOT APPLICATION EXPORT
// ============================================================================

export default function App() {
  // Dual-Theme State (Defaults to Dark Mode: "Obsidian & Slate Precision")
  const [theme, setTheme] = useState<ThemeMode>('dark');
  const t = THEME_CONFIG[theme];

  // Navigation & Portfolio Scope State
  const [activeRoute, setActiveRoute] = useState<NavRouteId>('overview');
  const [selectedPortfolio, setSelectedPortfolio] =
    useState<PortfolioScopeId>('MASTER');
  const [selectedMarket, setSelectedMarket] = useState<MarketSegment>('ALL');
  const [globalSearch, setGlobalSearch] = useState<string>('');

  // Chart & Allocation Controls State
  const [timeRange, setTimeRange] = useState<TimeRange>('YTD');
  const [benchmark, setBenchmark] = useState<BenchmarkId>('SPX');
  const [chartDisplayMode, setChartDisplayMode] = useState<
    'NAV' | 'RETURN_PCT'
  >('RETURN_PCT');
  const [allocationDimension, setAllocationDimension] =
    useState<AllocationDimension>('ASSET_CLASS');

  const activePortfolioProfile = useMemo(
    () =>
      PORTFOLIOS.find((p) => p.id === selectedPortfolio) ?? PORTFOLIOS[0],
    [selectedPortfolio]
  );

  // Scope holdings by Portfolio Mandate + Market Filter
  const scopedRawHoldings = useMemo(() => {
    return SAMPLE_HOLDINGS.filter((h) => {
      const inPortfolio = activePortfolioProfile.marketsIncluded.includes(
        h.market
      );
      const inMarket =
        selectedMarket === 'ALL' ? true : h.market === selectedMarket;
      return inPortfolio && inMarket;
    });
  }, [activePortfolioProfile, selectedMarket]);

  // Scope cash reserves by Portfolio Mandate + Market Filter
  const scopedCashUsd = useMemo(() => {
    const markets = activePortfolioProfile.marketsIncluded.filter((m) =>
      selectedMarket === 'ALL' ? true : m === selectedMarket
    );
    return markets.reduce((sum, m) => sum + CASH_RESERVES_BY_MARKET[m], 0);
  }, [activePortfolioProfile, selectedMarket]);

  // Reconciled KPIs & Position Metrics
  const { computedHoldings, summaryMetrics } = useMemo(() => {
    let totalCost = 0;
    let totalHoldingsValue = 0;
    let totalDailyPnL = 0;

    const prelim = scopedRawHoldings.map((h) => {
      const costBasisUsd = h.quantity * h.avgCostUsd;
      const marketValueUsd = h.quantity * h.currentPriceUsd;
      const unrealizedPnLUsd = marketValueUsd - costBasisUsd;
      const unrealizedPnLPct =
        costBasisUsd > 0 ? (unrealizedPnLUsd / costBasisUsd) * 100 : 0;
      const prevCloseVal =
        marketValueUsd / (1 + h.dayChangePct / 100 || 1);
      const dailyPnLUsd = marketValueUsd - prevCloseVal;

      totalCost += costBasisUsd;
      totalHoldingsValue += marketValueUsd;
      totalDailyPnL += dailyPnLUsd;

      return {
        ...h,
        costBasisUsd,
        marketValueUsd,
        unrealizedPnLUsd,
        unrealizedPnLPct,
        dailyPnLUsd,
      };
    });

    const totalValueUsd = totalHoldingsValue + scopedCashUsd;
    const totalReturnUsd = totalHoldingsValue - totalCost;
    const totalReturnPct =
      totalCost > 0 ? (totalReturnUsd / totalCost) * 100 : 0;
    const prevTotalValue = totalValueUsd - totalDailyPnL;
    const dailyPnLPct =
      prevTotalValue > 0 ? (totalDailyPnL / prevTotalValue) * 100 : 0;
    const cashWeightPct =
      totalValueUsd > 0 ? (scopedCashUsd / totalValueUsd) * 100 : 0;

    const enriched: ComputedHolding[] = prelim.map((item) => ({
      ...item,
      allocationPct:
        totalValueUsd > 0 ? (item.marketValueUsd / totalValueUsd) * 100 : 0,
      holdingsWeightPct:
        totalHoldingsValue > 0
          ? (item.marketValueUsd / totalHoldingsValue) * 100
          : 0,
    }));

    const metrics: PortfolioSummaryMetrics = {
      totalValueUsd,
      totalReturnUsd,
      totalReturnPct,
      dailyPnLUsd: totalDailyPnL,
      dailyPnLPct,
      investedCapitalUsd: totalCost,
      holdingsMarketValueUsd: totalHoldingsValue,
      availableCashUsd: scopedCashUsd,
      cashWeightPct,
      positionCount: enriched.length,
      sparklines: {
        totalValue: [
          totalValueUsd * 0.89,
          totalValueUsd * 0.91,
          totalValueUsd * 0.905,
          totalValueUsd * 0.94,
          totalValueUsd * 0.96,
          totalValueUsd * 0.985,
          totalValueUsd,
        ],
        totalReturn: [
          totalReturnUsd * 0.62,
          totalReturnUsd * 0.68,
          totalReturnUsd * 0.65,
          totalReturnUsd * 0.79,
          totalReturnUsd * 0.86,
          totalReturnUsd * 0.94,
          totalReturnUsd,
        ],
        dailyPnL: [
          totalDailyPnL * 0.35,
          totalDailyPnL * 0.55,
          totalDailyPnL * 0.42,
          totalDailyPnL * 0.74,
          totalDailyPnL * 0.68,
          totalDailyPnL * 0.88,
          totalDailyPnL,
        ],
        investedCapital: [
          totalCost * 0.92,
          totalCost * 0.92,
          totalCost * 0.95,
          totalCost * 0.95,
          totalCost * 0.98,
          totalCost * 0.98,
          totalCost,
        ],
        availableCash: [
          scopedCashUsd * 1.18,
          scopedCashUsd * 1.18,
          scopedCashUsd * 1.1,
          scopedCashUsd * 1.1,
          scopedCashUsd * 1.04,
          scopedCashUsd * 1.04,
          scopedCashUsd,
        ],
      },
    };

    return { computedHoldings: enriched, summaryMetrics: metrics };
  }, [scopedRawHoldings, scopedCashUsd]);

  const chartSeries = useMemo(
    () => buildPerformanceSeries(timeRange, summaryMetrics.totalValueUsd),
    [timeRange, summaryMetrics.totalValueUsd]
  );

  // Asset Allocation Slices using Multi-Series Palette
  const allocationSlices = useMemo((): AllocationSlice[] => {
    const totalNav = summaryMetrics.totalValueUsd || 1;
    const [c0, c1, c2, c3, c4] = t.chartPalette;

    if (allocationDimension === 'ASSET_CLASS') {
      const equitiesVal = computedHoldings
        .filter((h) => h.assetClass === 'Equities')
        .reduce((s, h) => s + h.marketValueUsd, 0);
      const cryptoVal = computedHoldings
        .filter((h) => h.assetClass === 'Digital Assets')
        .reduce((s, h) => s + h.marketValueUsd, 0);
      const etfVal = computedHoldings
        .filter((h) => h.assetClass === 'Index ETF')
        .reduce((s, h) => s + h.marketValueUsd, 0);

      const raw: AllocationSlice[] = [
        {
          id: 'ac-equities',
          label: 'Equities',
          sublabel: 'US & IDX Common Stock',
          marketValueUsd: equitiesVal,
          allocationPct: (equitiesVal / totalNav) * 100,
          color: c0,
        },
        {
          id: 'ac-crypto',
          label: 'Digital Assets',
          sublabel: 'Layer-1 & Protocol Spot',
          marketValueUsd: cryptoVal,
          allocationPct: (cryptoVal / totalNav) * 100,
          color: c1,
        },
        {
          id: 'ac-etf',
          label: 'Index ETFs',
          sublabel: 'Broad Benchmark Vehicles',
          marketValueUsd: etfVal,
          allocationPct: (etfVal / totalNav) * 100,
          color: c4,
        },
        {
          id: 'ac-cash',
          label: 'Cash Reserves',
          sublabel: 'USD, IDR RDN & USDC',
          marketValueUsd: summaryMetrics.availableCashUsd,
          allocationPct: (summaryMetrics.availableCashUsd / totalNav) * 100,
          color: c3,
        },
      ];
      return raw.filter((s) => s.marketValueUsd > 0);
    }

    if (allocationDimension === 'MARKET') {
      const usVal =
        computedHoldings
          .filter((h) => h.market === 'US')
          .reduce((s, h) => s + h.marketValueUsd, 0) +
        ((selectedMarket === 'ALL' || selectedMarket === 'US') &&
        activePortfolioProfile.marketsIncluded.includes('US')
          ? CASH_RESERVES_BY_MARKET.US
          : 0);

      const idxVal =
        computedHoldings
          .filter((h) => h.market === 'IDX')
          .reduce((s, h) => s + h.marketValueUsd, 0) +
        ((selectedMarket === 'ALL' || selectedMarket === 'IDX') &&
        activePortfolioProfile.marketsIncluded.includes('IDX')
          ? CASH_RESERVES_BY_MARKET.IDX
          : 0);

      const cryVal =
        computedHoldings
          .filter((h) => h.market === 'CRYPTO')
          .reduce((s, h) => s + h.marketValueUsd, 0) +
        ((selectedMarket === 'ALL' || selectedMarket === 'CRYPTO') &&
        activePortfolioProfile.marketsIncluded.includes('CRYPTO')
          ? CASH_RESERVES_BY_MARKET.CRYPTO
          : 0);

      const raw: AllocationSlice[] = [
        {
          id: 'mk-us',
          label: 'US Stocks',
          sublabel: 'NYSE & NASDAQ + USD Cash',
          marketValueUsd: usVal,
          allocationPct: (usVal / totalNav) * 100,
          color: c0,
        },
        {
          id: 'mk-idx',
          label: 'Indonesian Stocks (IDX)',
          sublabel: 'BEI Equities + IDR RDN',
          marketValueUsd: idxVal,
          allocationPct: (idxVal / totalNav) * 100,
          color: c4,
        },
        {
          id: 'mk-crypto',
          label: 'Cryptocurrency',
          sublabel: 'Spot Assets + Stablecoins',
          marketValueUsd: cryVal,
          allocationPct: (cryVal / totalNav) * 100,
          color: c1,
        },
      ];
      return raw.filter((s) => s.marketValueUsd > 0);
    }

    // Top Assets
    const sorted = [...computedHoldings].sort(
      (a, b) => b.marketValueUsd - a.marketValueUsd
    );
    const top4 = sorted.slice(0, 4);
    const othersVal = sorted
      .slice(4)
      .reduce((s, h) => s + h.marketValueUsd, 0);
    const topPalette = [c0, c1, c4, c2];

    const slices: AllocationSlice[] = top4.map((h, i) => ({
      id: h.id,
      label: h.symbol,
      sublabel: h.name,
      marketValueUsd: h.marketValueUsd,
      allocationPct: (h.marketValueUsd / totalNav) * 100,
      color: topPalette[i % topPalette.length],
    }));

    if (othersVal > 0) {
      slices.push({
        id: 'asset-other',
        label: `Other (${sorted.length - 4})`,
        sublabel: 'Remaining Active Holdings',
        marketValueUsd: othersVal,
        allocationPct: (othersVal / totalNav) * 100,
        color: c3,
      });
    }
    return slices;
  }, [
    allocationDimension,
    computedHoldings,
    summaryMetrics,
    selectedMarket,
    activePortfolioProfile,
    t.chartPalette,
  ]);

  const currentPageTitle = useMemo(() => {
    for (const group of NAVIGATION_GROUPS) {
      const found = group.items.find((item) => item.id === activeRoute);
      if (found) return found.label;
    }
    return 'Overview';
  }, [activeRoute]);

  const marketScopeLabel =
    selectedMarket === 'ALL'
      ? 'All Markets'
      : selectedMarket === 'US'
      ? 'US Stocks'
      : selectedMarket === 'IDX'
      ? 'IDX'
      : 'Crypto';

  const totalReturnPos = summaryMetrics.totalReturnUsd >= 0;
  const dailyPnLPos = summaryMetrics.dailyPnLUsd >= 0;

  return (
    <div
      style={{
        backgroundColor: t.canvasBg,
        color: t.textPrimary,
      }}
      className="min-h-screen flex flex-col font-sans antialiased transition-colors duration-150"
    >
      {/* 1. Top Utility Header Bar */}
      <TopHeader
        theme={theme}
        onThemeChange={setTheme}
        t={t}
        selectedPortfolio={selectedPortfolio}
        onSelectPortfolio={setSelectedPortfolio}
        selectedMarket={selectedMarket}
        onSelectMarket={setSelectedMarket}
        globalSearch={globalSearch}
        onGlobalSearchChange={setGlobalSearch}
      />

      {/* 2. Centered Horizontal Sub-Navigation Bar */}
      <HorizontalNav
        activeRoute={activeRoute}
        onSelectRoute={setActiveRoute}
        t={t}
      />

      {/* Responsive Market Filter Strip (< lg viewports) */}
      <div
        style={{
          backgroundColor: t.cardBg,
          borderColor: t.borderDefault,
        }}
        className="lg:hidden border-b px-4 py-2 flex items-center gap-1.5 overflow-x-auto"
      >
        {(
          [
            { id: 'ALL', label: 'All Markets' },
            { id: 'CRYPTO', label: 'Crypto' },
            { id: 'US', label: 'US Stocks' },
            { id: 'IDX', label: 'IDX' },
          ] as const
        ).map((tab) => {
          const active = selectedMarket === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setSelectedMarket(tab.id)}
              style={
                active
                  ? {
                      backgroundColor: t.accentBg,
                      color: t.accentText,
                      borderColor: t.accentBorder,
                    }
                  : {
                      backgroundColor: t.recessedBg,
                      color: t.textSecondary,
                      borderColor: t.borderDefault,
                    }
              }
              className="px-2.5 py-1 rounded text-[11px] font-medium border whitespace-nowrap"
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Main Analytical Workspace */}
      <main className="flex-1 w-full max-w-[1700px] mx-auto px-4 sm:px-6 py-5 space-y-4">
        {/* Sub-Route Context Banner when navigating secondary dropdown items */}
        {activeRoute !== 'overview' && (
          <div
            style={{
              backgroundColor: t.cardBg,
              borderColor: t.accentBorder,
            }}
            className="px-4 py-2.5 border rounded flex flex-wrap items-center justify-between gap-2 text-[12px]"
          >
            <div className="flex items-center gap-2">
              <Info
                style={{ color: t.accentText }}
                className="w-4 h-4 shrink-0"
              />
              <span style={{ color: t.textSecondary }}>
                <strong style={{ color: t.textPrimary }}>
                  {currentPageTitle}
                </strong>{' '}
                module active — displaying consolidated Overview telemetry for{' '}
                <span
                  style={{ color: t.textPrimary }}
                  className="font-mono font-medium"
                >
                  {activePortfolioProfile.name}
                </span>
                .
              </span>
            </div>
            <button
              type="button"
              onClick={() => setActiveRoute('overview')}
              style={{
                backgroundColor: t.accentBg,
                color: t.accentText,
                borderColor: t.accentBorder,
              }}
              className="px-2.5 py-1 rounded border text-[11px] font-medium"
            >
              Return to Overview
            </button>
          </div>
        )}

        {/* 3. Row 1 — 5 Split KPI Summary Cards */}
        <section aria-label="Portfolio Summary Metrics">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
            <KpiSplitCard
              title="Total Portfolio Value"
              dollarValue={formatUsd(summaryMetrics.totalValueUsd)}
              badgeText={`${summaryMetrics.positionCount} POS`}
              badgeVariant="neutral"
              secondaryContext={`${activePortfolioProfile.code} · EOD NAV`}
              sparklineValues={summaryMetrics.sparklines.totalValue}
              sparklineColor={t.accentText}
              t={t}
            />

            <KpiSplitCard
              title="Total Return"
              dollarValue={formatSignedUsd(summaryMetrics.totalReturnUsd)}
              badgeText={formatSignedPct(summaryMetrics.totalReturnPct)}
              badgeVariant={totalReturnPos ? 'gain' : 'loss'}
              secondaryContext="Cumulative Unrealized Gain"
              sparklineValues={summaryMetrics.sparklines.totalReturn}
              sparklineColor={totalReturnPos ? t.gainText : t.lossText}
              t={t}
            />

            <KpiSplitCard
              title="Daily P&L"
              dollarValue={formatSignedUsd(summaryMetrics.dailyPnLUsd)}
              badgeText={formatSignedPct(summaryMetrics.dailyPnLPct)}
              badgeVariant={dailyPnLPos ? 'gain' : 'loss'}
              secondaryContext="Session EOD Mark-to-Market"
              sparklineValues={summaryMetrics.sparklines.dailyPnL}
              sparklineColor={dailyPnLPos ? t.gainText : t.lossText}
              t={t}
            />

            <KpiSplitCard
              title="Invested Capital"
              dollarValue={formatUsd(summaryMetrics.investedCapitalUsd)}
              badgeText={`${(100 - summaryMetrics.cashWeightPct).toFixed(1)}%`}
              badgeVariant="neutral"
              secondaryContext="Reconciled Cost Basis"
              sparklineValues={summaryMetrics.sparklines.investedCapital}
              sparklineColor={t.chartPalette[1]}
              t={t}
            />

            <KpiSplitCard
              title="Available Cash"
              dollarValue={formatUsd(summaryMetrics.availableCashUsd)}
              badgeText={`${summaryMetrics.cashWeightPct.toFixed(1)}%`}
              badgeVariant="neutral"
              secondaryContext="USD, IDR RDN & Stablecoins"
              sparklineValues={summaryMetrics.sparklines.availableCash}
              sparklineColor={t.chartPalette[3]}
              t={t}
            />
          </div>
        </section>

        {/* 4. Row 2 — 8/4 Primary Analytical Split */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 items-stretch">
          <div className="xl:col-span-8">
            <PerformanceChart
              data={chartSeries}
              timeRange={timeRange}
              benchmark={benchmark}
              displayMode={chartDisplayMode}
              portfolioLabel={activePortfolioProfile.name}
              marketLabel={marketScopeLabel}
              themeTokens={t}
              onTimeRangeChange={setTimeRange}
              onBenchmarkChange={setBenchmark}
              onDisplayModeChange={setChartDisplayMode}
            />
          </div>

          <div className="xl:col-span-4">
            <MarketOverviewPanel
              selectedMarket={selectedMarket}
              onSelectMarket={setSelectedMarket}
              t={t}
            />
          </div>
        </div>

        {/* 5. Row 3 — 3-Column Mid-Tier Analytical Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
          <div className="lg:col-span-4">
            <AssetAllocationCard
              slices={allocationSlices}
              totalValueUsd={summaryMetrics.totalValueUsd}
              dimension={allocationDimension}
              onDimensionChange={setAllocationDimension}
              t={t}
            />
          </div>

          <div className="lg:col-span-4">
            <WatchlistCard
              selectedMarket={selectedMarket}
              searchQuery={globalSearch}
              t={t}
            />
          </div>

          <div className="lg:col-span-4">
            <RecentActivityCard activities={RECENT_ACTIVITIES} t={t} />
          </div>
        </div>

        {/* 6. Row 4 — Full-Width Institutional Holdings Table */}
        <HoldingsTable
          holdings={computedHoldings}
          selectedMarket={selectedMarket}
          onSelectMarket={setSelectedMarket}
          searchQuery={globalSearch}
          onSearchQueryChange={setGlobalSearch}
          t={t}
        />
      </main>

      {/* Institutional Terminal Status Footer */}
      <footer
        style={{
          backgroundColor: t.cardBg,
          borderColor: t.borderDefault,
          color: t.textMuted,
        }}
        className="border-t px-4 sm:px-6 py-2.5 text-[10.5px] transition-colors duration-150"
      >
        <div className="max-w-[1700px] mx-auto flex flex-wrap items-center justify-between gap-2 font-mono">
          <span className="flex items-center gap-1.5">
            <Activity className="w-3 h-3" />
            PIMS · PERSONAL INVESTMENT MANAGEMENT SYSTEM (NON-BROKERAGE TERMINAL)
          </span>
          <span>
            SAMPLE DATA · EOD / REF · USD/IDR 15,850 ·{' '}
            {theme === 'dark'
              ? 'OBSIDIAN & SLATE THEME'
              : 'DAYLIGHT PAPER & GRAPHITE THEME'}
          </span>
        </div>
      </footer>
    </div>
  );
}