"use client";

import dynamic from "next/dynamic";
import type { DeliveryMapProps } from "@/components/DeliveryMap";

const DeliveryMap = dynamic(() => import("@/components/DeliveryMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[420px] items-center justify-center rounded-xl border border-shipa-sky-accent bg-shipa-sky text-shipa-ink/60">
      Loading map…
    </div>
  ),
});

export default function MapClient(props: DeliveryMapProps) {
  return <DeliveryMap {...props} />;
}
