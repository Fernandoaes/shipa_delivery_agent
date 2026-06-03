export default function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-shipa-sky-accent bg-white p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-shipa-ink/50">{label}</div>
      <div className="mt-1 text-2xl font-bold text-shipa-ink">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-shipa-ink/50">{sub}</div>}
    </div>
  );
}
