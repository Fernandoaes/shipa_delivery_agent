export type Bar = { label: string; value: number };

export default function BarChart({
  title, data, orientation = "vertical",
}: { title: string; data: Bar[]; orientation?: "vertical" | "horizontal" }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="rounded-2xl border border-hairline bg-panel p-5">
      <h2 className="mb-4 text-sm font-semibold text-txt">{title}</h2>
      {orientation === "vertical" ? (
        <div className="flex h-40 items-stretch gap-1">
          {data.map((d) => (
            <div key={d.label} className="flex h-full flex-1 flex-col items-center gap-1" title={`${d.label}: ${d.value}`}>
              <div className="flex w-full flex-1 items-end">
                <div className="w-full rounded-t bg-shipa-blue" style={{ height: `${(d.value / max) * 100}%` }} />
              </div>
              <div className="text-[10px] text-txt-faint">{d.label}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {data.map((d) => (
            <div key={d.label} className="flex items-center gap-2 text-sm">
              <div className="w-28 truncate text-txt-dim" title={d.label}>{d.label}</div>
              <div className="h-4 flex-1 rounded bg-panel-2">
                <div className="h-4 rounded bg-shipa-blue" style={{ width: `${(d.value / max) * 100}%` }} />
              </div>
              <div className="w-8 text-right text-txt-dim">{d.value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
