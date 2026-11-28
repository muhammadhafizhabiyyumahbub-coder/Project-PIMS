import Link from "next/link";

import OpportunitiesSection from "@/features/dashboard/OpportunitiesSection";
import PortfolioWidget from "@/features/dashboard/PortfolioWidget";

export default function Home() {
  return (
    <main className="mx-auto max-w-[1700px] px-4 py-6 sm:px-6 flex flex-col gap-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[20px] font-bold tracking-tight">Dashboard</h1>
          <p className="text-[12px] text-ink3">
            Market overview and scanner results. Portfolio values come from the Portfolio Engine.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/scanner"
            className="text-[11px] text-accent underline underline-offset-2 focus-visible:outline focus-visible:outline-accent"
          >
            Scanner
          </Link>
          <Link
            href="/portfolios"
            className="text-[11px] text-accent underline underline-offset-2 focus-visible:outline focus-visible:outline-accent"
          >
            Portfolios
          </Link>
          <Link
            href="/watchlist"
            className="text-[11px] text-accent underline underline-offset-2 focus-visible:outline focus-visible:outline-accent"
          >
            Watchlists
          </Link>
        </div>
      </header>
      <PortfolioWidget />
      <OpportunitiesSection />
    </main>
  );
}
