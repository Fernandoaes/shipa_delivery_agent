function fmtPct(n: number) { return `${Math.round(n * 100)}%`; }

export default function AgentStats({
  containment, recovery, csat, handleTimeSeconds,
}: {
  containment: number; recovery: number; csat: number | null; handleTimeSeconds: number | null;
}) {
  const items = [
    { label: "Containment", value: fmtPct(containment) },
    { label: "Recovery", value: fmtPct(recovery) },
    { label: "CSAT", value: csat != null ? csat.toFixed(1) : "—" },
    { label: "Avg handle", value: handleTimeSeconds != null ? `${Math.round(handleTimeSeconds)}s` : "—" },
  ];
  return (
    <div className="rounded-xl border border-hairline bg-panel p-4">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-txt-faint">Agent performance</h2>
      <div className="grid grid-cols-2 gap-3">
        {items.map((i) => (
          <div key={i.label}>
            <div className="font-mono text-2xl font-semibold text-ok">{i.value}</div>
            <div className="text-xs text-txt-dim">{i.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
