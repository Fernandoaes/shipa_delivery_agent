"use client";

import dynamic from "next/dynamic";
import type { DeliveriesMapProps } from "@/components/DeliveriesMap";

const DeliveriesMap = dynamic(() => import("@/components/DeliveriesMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[460px] items-center justify-center rounded-xl border border-shipa-sky-accent bg-shipa-sky text-shipa-ink/60">
      Loading map…
    </div>
  ),
});

export default function DeliveriesMapClient(props: DeliveriesMapProps) {
  return <DeliveriesMap {...props} />;
}
