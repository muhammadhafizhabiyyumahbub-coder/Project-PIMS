import PortfolioList from "@/features/portfolio/PortfolioList";

export default function PortfoliosPage() {
  return (
    <main className="mx-auto max-w-[1700px] px-4 py-6 sm:px-6 flex flex-col gap-5">
      <header>
        <h1 className="text-[20px] font-bold tracking-tight">Portfolios</h1>
        <p className="text-[12px] text-ink3">
          Separately tracked portfolios with their own transactions, holdings, and valuation.
        </p>
      </header>
      <PortfolioList />
    </main>
  );
}
