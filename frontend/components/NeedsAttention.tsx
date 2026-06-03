import Link from "next/link";

type Item = { label: string; count: number; href: string; tone: string };

export default function NeedsAttention({
  openEscalations, pendingReschedules, failedOrders,
}: { openEscalations: number; pendingReschedules: number; failedOrders: number }) {
  const items: Item[] = [
    { label: "Open escalations", count: openEscalations, href: "/escalations", tone: "text-red-700" },
    { label: "Pending reschedules", count: pendingReschedules, href: "/reschedules", tone: "text-amber-700" },
    { label: "Failed / returned orders", count: failedOrders, href: "/orders", tone: "text-red-700" },
  ];
  return (
    <div className="rounded-xl border border-shipa-sky-accent bg-white p-5">
      <h2 className="mb-3 text-sm font-semibold text-shipa-ink">Needs attention</h2>
      <ul className="space-y-2">
        {items.map((it) => (
          <li key={it.label}>
            <Link href={it.href} className="flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-shipa-sky/60">
              <span className="text-sm text-shipa-ink/70">{it.label}</span>
              <span className={`text-lg font-bold ${it.count > 0 ? it.tone : "text-shipa-ink/30"}`}>{it.count}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
