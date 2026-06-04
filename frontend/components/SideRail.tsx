"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutGrid, Package, Users, Phone, CalendarClock, Search, TriangleAlert,
} from "@/components/icons";

const links = [
  { href: "/", label: "Overview", Icon: LayoutGrid },
  { href: "/orders", label: "Orders", Icon: Package },
  { href: "/customers", label: "Customers", Icon: Users },
  { href: "/calls", label: "Calls", Icon: Phone },
  { href: "/reschedules", label: "Reschedules", Icon: CalendarClock },
  { href: "/investigations", label: "Investigations", Icon: Search },
  { href: "/escalations", label: "Escalations", Icon: TriangleAlert },
];

export default function SideRail() {
  const pathname = usePathname();
  return (
    <aside className="fixed left-0 top-0 z-[1100] flex h-screen w-16 flex-col items-center gap-1 border-r border-hairline bg-panel py-4">
      <Link href="/" className="mb-4 grid h-10 w-10 place-items-center rounded-lg bg-shipa-blue" aria-label="SHIPA home">
        <Image src="/shipa-logo.svg" alt="SHIPA" width={22} height={22} priority />
      </Link>
      <nav className="flex flex-1 flex-col items-center gap-1">
        {links.map(({ href, label, Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              title={label}
              aria-label={label}
              className={`group relative grid h-11 w-11 place-items-center rounded-xl transition-colors ${
                active ? "bg-shipa-blue text-white" : "text-txt-dim hover:bg-panel-2 hover:text-txt"
              }`}
            >
              <Icon size={20} strokeWidth={active ? 2.4 : 2} />
              <span className="pointer-events-none absolute left-14 z-50 whitespace-nowrap rounded-md border border-hairline bg-panel-2 px-2 py-1 text-xs text-txt opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                {label}
              </span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
