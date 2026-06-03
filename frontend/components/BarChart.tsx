export type Bar = { label: string; value: number };

export default function BarChart({
  title, data, orientation = "vertical",
}: { title: string; data: Bar[]; orientation?: "vertical" | "horizontal" }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="rounded-xl border border-shipa-sky-accent bg-white p-5">
      <h2 className="mb-4 text-sm font-semibold text-shipa-ink">{title}</h2>
      {orientation === "vertical" ? (
        <div className="flex h-40 items-end gap-1">
          {data.map((d) => (
            <div key={d.label} className="flex flex-1 flex-col items-center justify-end gap-1" title={`${d.label}: ${d.value}`}>
              <div className="w-full rounded-t bg-shipa-blue/80" style={{ height: `${(d.value / max) * 100}%` }} />
              <div className="text-[10px] text-shipa-ink/40">{d.label}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {data.map((d) => (
            <div key={d.label} className="flex items-center gap-2 text-sm">
              <div className="w-28 truncate text-shipa-ink/70" title={d.label}>{d.label}</div>
              <div className="h-4 flex-1 rounded bg-shipa-sky">
                <div className="h-4 rounded bg-shipa-blue/80" style={{ width: `${(d.value / max) * 100}%` }} />
              </div>
              <div className="w-8 text-right text-shipa-ink/60">{d.value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
