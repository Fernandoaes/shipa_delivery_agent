import CallsTable from "@/components/CallsTable";
import { getCalls } from "@/lib/api";

export default async function CallsPage() {
  const calls = await getCalls();
  return (
    <div className="px-8 py-8">
      <h1 className="mb-6 text-2xl font-bold text-txt">Calls</h1>
      <CallsTable calls={calls} />
    </div>
  );
}
