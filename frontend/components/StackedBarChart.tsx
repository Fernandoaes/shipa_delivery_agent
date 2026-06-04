"use client";

import { useMemo } from "react";
import type { ChannelDay } from "@/lib/types";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#a855f7", "#ef4444", "#14b8a6"];

export default function StackedBarChart({ title, data }: { title: string; data: ChannelDay[] }) {
  const channels = useMemo(() => {
    const set = new Set<string>();
    data.forEach((d) => Object.keys(d.channels).forEach((c) => set.add(c)));
    return Array.from(set).sort();
  }, [data]);
  const color = (c: string) => COLORS[channels.indexOf(c) % COLORS.length];
  const max = Math.max(1, ...data.map((d) => Object.values(d.channels).reduce((a, b) => a + b, 0)));

  return (
    <div className="rounded-xl border border-hairline bg-panel p-4">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-txt-faint">{title}</h2>
      <div className="flex h-40 items-end gap-1">
        {data.map((d) => (
          <div key={d.date} className="flex h-full flex-1 flex-col-reverse" title={d.date}>
            {channels.map((c) => {
              const v = d.channels[c] ?? 0;
              return v ? (
                <div key={c} style={{ height: `${(v / max) * 100}%`, background: color(c) }} />
              ) : null;
            })}
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-3">
        {channels.map((c) => (
          <span key={c} className="flex items-center gap-1.5 text-xs text-txt-dim">
            <span className="inline-block h-2 w-2 rounded-sm" style={{ background: color(c) }} />
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}
