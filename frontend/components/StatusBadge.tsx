// Translucent status pills tuned for the dark theme.
const STYLES: Record<string, string> = {
  delivered: "bg-ok/15 text-ok",
  out_for_delivery: "bg-[#3b82f6]/15 text-[#7eb0ff]",
  failed: "bg-bad/15 text-[#ff8585]",
  pending: "bg-ok/15 text-ok",
  rescheduled: "bg-warn/15 text-warn",
  returned: "bg-muted/15 text-muted",
  cancelled: "bg-muted/15 text-muted",
  passed: "bg-ok/15 text-ok",
  partial: "bg-warn/15 text-warn",
  open: "bg-warn/15 text-warn",
};

export default function StatusBadge({ status }: { status: string }) {
  const cls = STYLES[status] ?? "bg-muted/15 text-muted";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
