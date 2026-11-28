import type { Metadata } from "next";

import WatchlistPanel from "@/features/watchlist/WatchlistPanel";

export const metadata: Metadata = {
  title: "Watchlists | PIMS",
};

export default function WatchlistRoute() {
  return (
    <main className="mx-auto max-w-[1700px] px-4 py-6 sm:px-6 flex flex-col gap-5">
      <header>
        <h1 className="text-[20px] font-bold tracking-tight">Watchlists</h1>
        <p className="text-[12px] text-ink3">
          Tracked instruments per watchlist. Membership never touches portfolio holdings.
        </p>
      </header>
      <WatchlistPanel />
    </main>
  );
}
