import Link from "next/link";

type Row = { label: string; value: number; href: string };

export default function WorkQueue({
  openEscalations, overdueCallbacks, pendingReschedules, pendingAddressFlags,
}: {
  openEscalations: number; overdueCallbacks: number;
  pendingReschedules: number; pendingAddressFlags: number;
}) {
  const rows: Row[] = [
    { label: "Open escalations", value: openEscalations, href: "/escalations?status=open" },
    { label: "Overdue callbacks", value: overdueCallbacks, href: "/investigations?overdue=1" },
    { label: "Unsynced reschedules", value: pendingReschedules, href: "/reschedules" },
    { label: "Pending address flags", value: pendingAddressFlags, href: "/orders" },
  ];
  return (
    <div className="rounded-xl border border-hairline bg-panel p-4">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-txt-faint">Work queue</h2>
      <ul className="space-y-1">
        {rows.map((r) => (
          <li key={r.label}>
            <Link href={r.href}
              className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-panel-2">
              <span className="text-sm text-txt-dim">{r.label}</span>
              <span className={`font-mono text-lg font-semibold ${r.value > 0 ? "text-amber-400" : "text-txt-faint"}`}>
                {r.value}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
