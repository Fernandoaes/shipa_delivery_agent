import Link from "next/link";
import type { ComponentType } from "react";

type Tone = "neutral" | "ok" | "warn" | "bad";

const TONE: Record<Tone, string> = {
  neutral: "text-txt",
  ok: "text-ok",
  warn: "text-warn",
  bad: "text-bad",
};
const ICON_TONE: Record<Tone, string> = {
  neutral: "bg-panel-2 text-txt-dim",
  ok: "bg-ok/10 text-ok",
  warn: "bg-warn/10 text-warn",
  bad: "bg-bad/10 text-bad",
};

export default function KpiStat({
  label, value, sub, tone = "neutral", Icon, href,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: Tone;
  Icon: ComponentType<{ size?: number; className?: string }>;
  href?: string;
}) {
  const inner = (
    <>
      <div>
        <div className="font-mono text-[11px] uppercase tracking-widest text-txt-faint">{label}</div>
        <div className={`mt-2 text-3xl font-semibold ${TONE[tone]}`}>{value}</div>
        {sub && <div className="mt-1 text-xs text-txt-dim">{sub}</div>}
      </div>
      <span className={`grid h-9 w-9 place-items-center rounded-lg ${ICON_TONE[tone]}`}>
        <Icon size={18} />
      </span>
    </>
  );
  const base = "flex items-start justify-between rounded-2xl border border-hairline bg-panel p-5";
  if (href) {
    return (
      <Link href={href} className={`${base} transition-colors hover:border-shipa-blue hover:bg-panel-2`}>
        {inner}
      </Link>
    );
  }
  return <div className={base}>{inner}</div>;
}
