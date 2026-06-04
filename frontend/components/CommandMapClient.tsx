"use client";

import dynamic from "next/dynamic";
import type { CommandMapProps } from "@/components/CommandMap";

const CommandMap = dynamic(() => import("@/components/CommandMap"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center rounded-2xl border border-hairline bg-panel text-txt-dim" style={{ height: "68vh" }}>
      Loading live map…
    </div>
  ),
});

export default function CommandMapClient(props: CommandMapProps) {
  return <CommandMap {...props} />;
}
