const STYLES: Record<string, string> = {
  delivered: "bg-green-100 text-green-800",
  out_for_delivery: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  pending: "bg-amber-100 text-amber-800",
  rescheduled: "bg-slate-100 text-slate-700",
  returned: "bg-slate-100 text-slate-700",
  cancelled: "bg-slate-100 text-slate-700",
};

export default function StatusBadge({ status }: { status: string }) {
  const cls = STYLES[status] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
