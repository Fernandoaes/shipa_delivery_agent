import Link from "next/link";
import BarChart from "@/components/BarChart";
import DeliveriesMapClient from "@/components/DeliveriesMapClient";
import KpiCard from "@/components/KpiCard";
import NeedsAttention from "@/components/NeedsAttention";
import RecentCalls from "@/components/RecentCalls";
import { getCalls, getInsights, getMetrics } from "@/lib/api";

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

const RANGES: { label: string; days: number }[] = [
  { label: "1d", days: 1 },
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
];

export default async function OverviewPage({
  searchParams,
}: {
  searchParams: Promise<{ range?: string }>;
}) {
  const { range } = await searchParams;
  const selected = RANGES.find((r) => r.label === range) ?? RANGES[1]; // default 7d
  const [metrics, insights, calls] = await Promise.all([
    getMetrics(),
    getInsights(selected.days),
    getCalls(),
  ]);
  const callsPerDay = insights.calls_per_day.map((d) => ({
    // d.date is "YYYY-MM-DD"; slice the day directly to avoid UTC-parse drift.
    label: String(Number(d.date.slice(8, 10))),
    value: d.count,
  }));
  const intentMix = insights.intent_mix.map((d) => ({ label: d.intent, value: d.count }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-shipa-ink">Overview</h1>
        <div className="flex gap-1 rounded-lg border border-shipa-sky-accent bg-white p-1">
          {RANGES.map((r) => (
            <Link
              key={r.label}
              href={`/?range=${r.label}`}
              className={`rounded-md px-3 py-1 text-sm font-medium ${
                r.label === selected.label
                  ? "bg-shipa-blue text-white"
                  : "text-shipa-ink/60 hover:bg-shipa-sky"
              }`}
            >
              {r.label}
            </Link>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <KpiCard label="Total calls" value={metrics.total_calls.toString()} />
        <KpiCard label="First-attempt" value={pct(metrics.first_attempt_rate)} />
        <KpiCard label="Deflection" value={pct(metrics.deflection_rate)} />
        <KpiCard label="Avg CSAT" value={metrics.avg_csat?.toFixed(1) ?? "—"} sub="of 5" />
        <KpiCard label="Avg handle"
          value={metrics.avg_handle_time_seconds ? `${Math.round(metrics.avg_handle_time_seconds)}s` : "—"} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <BarChart title={`Calls per day (${selected.label})`} data={callsPerDay} />
        <BarChart title={`Intent mix (${selected.label})`} data={intentMix} orientation="horizontal" />
      </div>

      <div className="rounded-xl border border-shipa-sky-accent bg-white p-3">
        <h2 className="mb-2 px-2 pt-1 text-sm font-semibold text-shipa-ink">
          Live deliveries ({insights.map_points.length})
        </h2>
        <DeliveriesMapClient points={insights.map_points} />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="md:col-span-1">
          <NeedsAttention
            openEscalations={insights.needs_attention.open_escalations}
            pendingReschedules={insights.needs_attention.pending_reschedules}
            failedOrders={insights.needs_attention.failed_orders}
          />
        </div>
        <div className="md:col-span-2"><RecentCalls calls={calls.slice(0, 10)} /></div>
      </div>
    </div>
  );
}
