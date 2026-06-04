import { Suspense } from "react";
import InvestigationsTable from "@/components/InvestigationsTable";
import { getInvestigations } from "@/lib/api";

export default async function InvestigationsPage() {
  const rows = await getInvestigations();
  // renderTime is a stable ISO string captured at server-render time, passed to the
  // client table so it can filter overdue callbacks without calling Date.now() during render.
  const renderTime = new Date().toISOString();
  return (
    <div className="px-8 py-8">
      <h1 className="mb-6 text-2xl font-bold text-txt">Investigations</h1>
      <Suspense fallback={<div className="text-sm text-txt-dim">Loading…</div>}>
        <InvestigationsTable rows={rows} renderTime={renderTime} />
      </Suspense>
    </div>
  );
}
