import OpportunitiesSection from "@/features/dashboard/OpportunitiesSection";

export default function Home() {
  return (
    <main className="mx-auto max-w-[1700px] px-4 py-6 sm:px-6 flex flex-col gap-5">
      <header>
        <h1 className="text-[20px] font-bold tracking-tight">Dashboard</h1>
        <p className="text-[12px] text-ink3">
          Market overview and scanner results. Portfolio widgets appear once portfolio data exists (Phase 4).
        </p>
      </header>
      <OpportunitiesSection />
    </main>
  );
}
