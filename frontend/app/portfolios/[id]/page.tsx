import { Suspense } from "react";

import PortfolioDetail from "@/features/portfolio/PortfolioDetail";

export default function PortfolioPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense
      fallback={
        <main className="mx-auto max-w-[1700px] px-4 py-6 sm:px-6">
          <div className="bg-card border border-line rounded-lg px-4 py-10 text-center text-[12px] text-ink3" aria-live="polite">
            Loading portfolio…
          </div>
        </main>
      }
    >
      <PortfolioContent params={params} />
    </Suspense>
  );
}

async function PortfolioContent({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="mx-auto max-w-[1700px] px-4 py-6 sm:px-6 flex flex-col gap-5">
      <PortfolioDetail portfolioId={id} />
    </main>
  );
}
