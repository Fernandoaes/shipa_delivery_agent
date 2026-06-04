"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Polls server components on an interval so agent-driven DB changes
// (new calls, reschedules, escalations) surface without a manual reload.
export default function AutoRefresh({ intervalMs = 15000 }: { intervalMs?: number }) {
  const router = useRouter();
  useEffect(() => {
    const id = setInterval(() => router.refresh(), intervalMs);
    return () => clearInterval(id);
  }, [router, intervalMs]);
  return null;
}
