import Link from "next/link";
import AgentStats from "@/components/AgentStats";
import BarChart from "@/components/BarChart";
import CommandMapClient from "@/components/CommandMapClient";
import KpiStat from "@/components/KpiStat";
import RecentCalls from "@/components/RecentCalls";
import StackedBarChart from "@/components/StackedBarChart";
import WorkQueue from "@/components/WorkQueue";
import { Activity, Package, TrendingUp, TriangleAlert } from "@/components/icons";
import { getCalls, getInsights, getMetrics, getOrders } from "@/lib/api";
import { buildDriverRoutes } from "@/lib/insights";

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

const WISMO = new Set(["track", "status", "wismo", "where_is_my_order", "tracking"]);

const RANGES: { label: string; days: number }[] = [
  { label: "1d", days: 1 },
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
];

export default async function CommandCenter({
  searchParams,
}: {
  searchParams: Promise<{ range?: string }>;
}) {
  const { range } = await searchParams;
  const selected = RANGES.find((r) => r.label === range) ?? RANGES[1];
  const [metrics, insights, calls, orders] = await Promise.all([
    getMetrics(selected.days),
    getInsights(selected.days),
    getCalls(),
    getOrders(),
  ]);

  const drivers = buildDriverRoutes(orders, insights.map_points);
  const intentMix = insights.intent_mix.map((d) => ({
    label: d.intent,
    value: d.count,
    accent: WISMO.has(d.intent.toLowerCase()),
  }));
  const areaFailures = insights.failures_by_area.map((a) => ({ label: a.area, value: a.count }));

  return (
    <div className="space-y-6 px-6 pb-6">
      <div className="sticky top-0 z-30 -mx-6 flex items-end justify-between border-b border-hairline bg-ink/95 px-6 py-4 backdrop-blur">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-txt">Shipa Delivery</h1>
          <div className="font-mono text-xs uppercase tracking-[0.3em] text-txt-faint">Operations</div>
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
        <KpiStat label="First-Attempt Success" value={pct(metrics.first_attempt_success)} sub="delivered on attempt 1" tone="ok" Icon={Activity} />
        <KpiStat label="On-Time Rate" value={pct(metrics.on_time_rate)} sub="within promised window" tone="ok" Icon={TrendingUp} />
        <KpiStat label="Active Deliveries" value={metrics.active_deliveries.toString()} sub="out for delivery" Icon={Package} />
        <KpiStat label="At-Risk" value={metrics.at_risk.toString()} sub="failed / returned" tone={metrics.at_risk > 0 ? "bad" : "ok"} Icon={TriangleAlert} href="/orders?risk=1" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <CommandMapClient points={insights.map_points} drivers={drivers} />
        <WorkQueue
          openEscalations={insights.needs_attention.open_escalations}
          overdueCallbacks={insights.needs_attention.overdue_callbacks}
          pendingReschedules={insights.needs_attention.pending_reschedules}
          pendingAddressFlags={insights.needs_attention.pending_address_flags}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <AgentStats
          containment={metrics.containment_rate}
          recovery={metrics.recovery_rate}
          csat={metrics.avg_csat}
          handleTimeSeconds={metrics.avg_handle_time_seconds}
        />
        <StackedBarChart title={`Interactions per day (${selected.label})`} data={insights.interactions_per_day} />
        <BarChart title={`Voice intents (${selected.label})`} data={intentMix} orientation="horizontal" />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <BarChart title="Failures by area" data={areaFailures} orientation="horizontal" />
        <RecentCalls calls={calls.slice(0, 10)} />
      </div>
    </div>
  );
}
