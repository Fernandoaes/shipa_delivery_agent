"use client";

export default function SearchInput({
  value, onChange, placeholder,
}: {
  value: string; onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <input
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder ?? "Search…"}
      className="w-64 rounded-lg border border-hairline bg-panel-2 px-3 py-2 text-sm text-txt placeholder:text-txt-faint"
    />
  );
}
