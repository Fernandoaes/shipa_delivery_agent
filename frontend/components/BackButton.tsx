import Link from "next/link";
import { ArrowLeft } from "@/components/icons";

export default function BackButton({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1.5 rounded-lg border border-hairline bg-panel px-3 py-1.5 text-sm font-medium text-txt-dim transition-colors hover:bg-panel-2 hover:text-txt"
    >
      <ArrowLeft size={16} /> {label}
    </Link>
  );
}
