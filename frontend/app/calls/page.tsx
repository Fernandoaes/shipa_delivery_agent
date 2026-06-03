import CallsTable from "@/components/CallsTable";
import { getCalls } from "@/lib/api";

export default async function CallsPage() {
  const calls = await getCalls();
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-shipa-ink">Calls</h1>
      <CallsTable calls={calls} />
    </div>
  );
}
