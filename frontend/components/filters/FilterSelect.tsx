"use client";

export default function FilterSelect({
  value, onChange, options, allLabel,
}: {
  value: string; onChange: (v: string) => void; options: string[]; allLabel: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-hairline bg-panel-2 px-3 py-2 text-sm text-txt"
    >
      <option value="">{allLabel}</option>
      {options.map((o) => (
        <option key={o} value={o}>{o.replace(/_/g, " ")}</option>
      ))}
    </select>
  );
}
