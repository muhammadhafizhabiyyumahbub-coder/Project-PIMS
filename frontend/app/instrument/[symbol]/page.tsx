import { Suspense } from "react";

import InstrumentDetail from "@/features/instrument/InstrumentDetail";

export default function InstrumentPage({
  params,
  searchParams,
}: {
  params: Promise<{ symbol: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  return (
    <Suspense
      fallback={
        <main className="mx-auto max-w-[1700px] px-4 py-6 sm:px-6">
          <div className="bg-card border border-line rounded-lg px-4 py-10 text-center text-[12px] text-ink3" aria-live="polite">
            Loading instrument…
          </div>
        </main>
      }
    >
      <InstrumentContent params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function InstrumentContent({
  params,
  searchParams,
}: {
  params: Promise<{ symbol: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { symbol } = await params;
  const { timeframe } = await searchParams;
  const timeframeValue = Array.isArray(timeframe) ? timeframe[0] : timeframe;

  return <InstrumentDetail symbol={symbol.toUpperCase()} timeframe={timeframeValue} />;
}
