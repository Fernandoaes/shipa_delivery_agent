import Link from "next/link";
import BarChart from "@/components/BarChart";
import CommandMapClient from "@/components/CommandMapClient";
import KpiStat from "@/components/KpiStat";
import LiveOrdersPanel from "@/components/LiveOrdersPanel";
import NeedsAttention from "@/components/NeedsAttention";
import RecentCalls from "@/components/RecentCalls";
import { Activity, Package, TrendingUp, TriangleAlert } from "@/components/icons";
import { getCalls, getInsights, getMetrics, getOrders } from "@/lib/api";
import { activeOrders, buildDriverRoutes, networkRisk } from "@/lib/insights";

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

const RANGES: { label: string; days: number }[] = [
  { label: "1d", days: 1 },
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
];

const RISK_TONE = { LOW: "ok", MED: "warn", HIGH: "bad" } as const;

export default async function CommandCenter({
  searchParams,
}: {
  searchParams: Promise<{ range?: string }>;
}) {
  const { range } = await searchParams;
  const selected = RANGES.find((r) => r.label === range) ?? RANGES[1];
  const [metrics, insights, calls, orders] = await Promise.all([
    getMetrics(),
    getInsights(selected.days),
    getCalls(),
    getOrders(),
  ]);

  const active = activeOrders(insights.map_points);
  const drivers = buildDriverRoutes(orders, insights.map_points);
  const risk = networkRisk(insights.needs_attention);
  const callsPerDay = insights.calls_per_day.map((d) => ({
    label: String(Number(d.date.slice(8, 10))),
    value: d.count,
  }));
  const intentMix = insights.intent_mix.map((d) => ({ label: d.intent, value: d.count }));

  return (
    <div className="space-y-6 px-6 pb-6">
      <div className="sticky top-0 z-30 -mx-6 flex items-end justify-between border-b border-hairline bg-ink/95 px-6 py-4 backdrop-blur">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-txt">Shipa Delivery</h1>
          <div className="font-mono text-xs uppercase tracking-[0.3em] text-txt-faint">Real-time monitoring</div>
        </div>
        <div className="flex gap-1 rounded-lg border border-hairline bg-panel p-1">
          {RANGES.map((r) => (
            <Link
              key={r.label}
              href={`/?range=${r.label}`}
              className={`rounded-md px-3 py-1 text-sm font-medium ${
                r.label === selected.label ? "bg-shipa-blue text-white" : "text-txt-dim hover:bg-panel-2"
              }`}
            >
              {r.label}
            </Link>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiStat label="Service Level" value={pct(metrics.first_attempt_rate)} sub="first-attempt" tone="ok" Icon={Activity} />
        <KpiStat label="Active Orders" value={active.length.toString()} sub="out for delivery" Icon={Package} />
        <KpiStat label="Deflection" value={pct(metrics.deflection_rate)} sub="self-served" Icon={TrendingUp} />
        <KpiStat label="Network Risk" value={risk} tone={RISK_TONE[risk]} Icon={TriangleAlert} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <CommandMapClient points={insights.map_points} drivers={drivers} />
        <div className="h-[68vh]">
          <LiveOrdersPanel points={active} />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <BarChart title={`Calls per day (${selected.label})`} data={callsPerDay} />
        <BarChart title={`Intent mix (${selected.label})`} data={intentMix} orientation="horizontal" />
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
