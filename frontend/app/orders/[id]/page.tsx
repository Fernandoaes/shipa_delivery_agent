import Link from "next/link";
import type { ReactNode } from "react";
import BackButton from "@/components/BackButton";
import MapClient from "@/components/MapClient";
import StatusBadge from "@/components/StatusBadge";
import { getOrder } from "@/lib/api";

type LatLng = [number, number];

function pair(lat: number | null, lng: number | null): LatLng | null {
  return lat != null && lng != null ? [lat, lng] : null;
}

function fmt(ts: string | null): string {
  return ts ? new Date(ts).toLocaleString() : "—";
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-hairline bg-panel p-5">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-txt-faint">{title}</h2>
      {children}
    </div>
  );
}

export default async function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const o = await getOrder(id);
  const rows: [string, string][] = [
    ["Merchant", o.merchant],
    ["Delivery address", o.delivery_address],
    ["Area", o.delivery_area ?? "—"],
    ["Window", o.delivery_window ?? "—"],
    ["Driver", o.assigned_driver ?? "—"],
    ["Pieces", o.expected_pieces?.toString() ?? "—"],
    ["Attempts", o.attempt_count.toString()],
    ["SLA due", fmt(o.sla_due_at)],
    ["Delivered", fmt(o.delivered_at)],
  ];
  return (
    <div className="px-8 py-8">
      <BackButton href="/orders" label="Orders" />
      <div className="mb-6 mt-3 flex items-center gap-3">
        <h1 className="text-2xl font-bold text-txt">{o.twin_order_ref}</h1>
        <StatusBadge status={o.status} />
        {o.attempt_count > 1 && (
          <span className="rounded-full bg-warn/15 px-2.5 py-0.5 text-xs font-medium text-warn">
            attempt {o.attempt_count}
          </span>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-hairline bg-panel p-5">
          <dl className="divide-y divide-hairline">
            {rows.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4 py-2.5 text-sm">
                <dt className="text-txt-dim">{k}</dt>
                <dd className="text-right font-medium text-txt">{v}</dd>
              </div>
            ))}
            <div className="flex justify-between gap-4 py-2.5 text-sm">
              <dt className="text-txt-dim">Customer</dt>
              <dd className="text-right font-medium">
                <Link href={`/customers/${o.customer.customer_id}`} className="text-shipa-blue hover:underline">
                  {o.customer.full_name}
                </Link>
                <span className="text-txt-dim"> · {o.customer.primary_phone}</span>
              </dd>
            </div>
          </dl>
        </div>
        <MapClient
          merchant={o.merchant}
          deliveryAddress={o.delivery_address}
          status={o.status}
          merchantLatLng={pair(o.merchant_lat, o.merchant_lng)}
          deliveryLatLng={pair(o.delivery_lat, o.delivery_lng)}
        />
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        {o.escalations.length > 0 && (
          <Section title="Escalations">
            <ul className="space-y-2 text-sm">
              {o.escalations.map((e) => (
                <li key={e.escalation_id} className="flex items-start justify-between gap-3">
                  <span className="text-txt">{e.category}{e.reason ? ` — ${e.reason}` : ""}</span>
                  <StatusBadge status={e.status} />
                </li>
              ))}
            </ul>
          </Section>
        )}

        {o.reschedules.length > 0 && (
          <Section title="Reschedules">
            <ul className="space-y-2 text-sm">
              {o.reschedules.map((r) => (
                <li key={r.reschedule_id} className="flex items-start justify-between gap-3">
                  <span className="text-txt">requested {r.requested_date}</span>
                  <StatusBadge status={r.status} />
                </li>
              ))}
            </ul>
          </Section>
        )}

        {o.address_flags.length > 0 && (
          <Section title="Address flags">
            <ul className="space-y-2 text-sm">
              {o.address_flags.map((f) => (
                <li key={f.flag_id} className="flex items-start justify-between gap-3">
                  <span className="text-txt">{f.correction_text}</span>
                  <StatusBadge status={f.status} />
                </li>
              ))}
            </ul>
          </Section>
        )}

        {o.investigations.length > 0 && (
          <Section title="Investigations">
            <ul className="space-y-2 text-sm">
              {o.investigations.map((i) => (
                <li key={i.investigation_id} className="flex items-start justify-between gap-3">
                  <span className="text-txt">{i.type}</span>
                  <StatusBadge status={i.status} />
                </li>
              ))}
            </ul>
          </Section>
        )}

        {o.calls.length > 0 && (
          <Section title="Recent calls">
            <ul className="space-y-3 text-sm">
              {o.calls.map((c) => (
                <li key={c.call_id} className="border-b border-hairline pb-2 last:border-0 last:pb-0">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-txt">{c.intent ?? c.direction}{c.disposition ? ` · ${c.disposition}` : ""}</span>
                    <span className="font-mono text-xs text-txt-faint">{fmt(c.started_at)}</span>
                  </div>
                  {c.csat_score != null && <div className="mt-1 text-xs text-txt-dim">CSAT {c.csat_score}</div>}
                </li>
              ))}
            </ul>
          </Section>
        )}
      </div>
    </div>
  );
}
