import Link from "next/link";
import type { MapPoint } from "@/lib/types";

const DOT: Record<string, string> = {
  out_for_delivery: "bg-[#3b82f6]",
  pending: "bg-warn",
  failed: "bg-bad",
  rescheduled: "bg-muted",
};

export default function LiveOrdersPanel({ points }: { points: MapPoint[] }) {
  return (
    <div className="flex h-full flex-col rounded-2xl border border-hairline bg-panel">
      <div className="flex items-center justify-between border-b border-hairline px-5 py-4">
        <div>
          <h2 className="text-base font-semibold text-txt">Live Orders</h2>
          <div className="font-mono text-[10px] uppercase tracking-widest text-txt-faint">Shipa Delivery</div>
        </div>
        <span className="flex items-center gap-1.5 text-[11px] font-medium text-ok">
          <span className="live-dot inline-block h-2 w-2 rounded-full bg-ok" /> LIVE
        </span>
      </div>
      <div className="flex items-center gap-3 border-b border-hairline px-5 py-2 font-mono text-[10px] uppercase tracking-widest text-txt-faint">
        <span className="flex-1">Route</span>
        <span className="w-24">Area</span>
      </div>
      <ul className="flex-1 overflow-y-auto">
        {points.map((p) => (
          <li key={p.order_id}>
            <Link
              href={`/orders/${p.order_id}`}
              className="flex items-center gap-3 border-b border-hairline/60 px-5 py-3 text-sm transition-colors hover:bg-panel-2"
            >
              <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[p.status] ?? "bg-muted"}`} />
              <span className="flex-1 truncate font-mono text-txt">{p.twin_order_ref}</span>
              <span className="w-24 truncate text-txt-dim">{p.delivery_area ?? "—"}</span>
            </Link>
          </li>
        ))}
        {points.length === 0 && (
          <li className="px-5 py-6 text-center text-sm text-txt-dim">No active orders</li>
        )}
      </ul>
    </div>
  );
}
