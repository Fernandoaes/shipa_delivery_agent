import Link from "next/link";

type Item = { label: string; count: number; href: string; tone: string };

export default function NeedsAttention({
  openEscalations, pendingReschedules, failedOrders,
}: { openEscalations: number; pendingReschedules: number; failedOrders: number }) {
  const items: Item[] = [
    { label: "Open escalations", count: openEscalations, href: "/escalations", tone: "text-bad" },
    { label: "Pending reschedules", count: pendingReschedules, href: "/reschedules", tone: "text-warn" },
    { label: "Failed / returned orders", count: failedOrders, href: "/orders", tone: "text-bad" },
  ];
  return (
    <div className="rounded-2xl border border-hairline bg-panel p-5">
      <h2 className="mb-3 text-sm font-semibold text-txt">Needs attention</h2>
      <ul className="space-y-2">
        {items.map((it) => (
          <li key={it.label}>
            <Link href={it.href} className="flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-panel-2">
              <span className="text-sm text-txt-dim">{it.label}</span>
              <span className={`text-lg font-bold ${it.count > 0 ? it.tone : "text-txt-faint"}`}>{it.count}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
