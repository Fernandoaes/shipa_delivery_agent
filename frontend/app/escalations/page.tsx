import { Suspense } from "react";
import EscalationsTable from "@/components/EscalationsTable";
import { getEscalations } from "@/lib/api";

export default async function EscalationsPage() {
  const rows = await getEscalations();
  return (
    <div className="px-8 py-8">
      <h1 className="mb-6 text-2xl font-bold text-txt">Escalations</h1>
      <Suspense fallback={<div className="text-sm text-txt-dim">Loading…</div>}>
        <EscalationsTable rows={rows} />
      </Suspense>
    </div>
  );
}
