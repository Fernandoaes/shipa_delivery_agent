"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Overview" },
  { href: "/orders", label: "Orders" },
  { href: "/customers", label: "Customers" },
  { href: "/calls", label: "Calls" },
  { href: "/reschedules", label: "Reschedules" },
  { href: "/investigations", label: "Investigations" },
  { href: "/escalations", label: "Escalations" },
];

export default function TopBar() {
  const pathname = usePathname();
  return (
    <header className="flex items-center gap-8 border-b border-shipa-sky-accent bg-white px-6 py-4">
      <Link href="/" className="flex items-center">
        <Image src="/shipa-logo.svg" alt="SHIPA" width={120} height={28} priority />
      </Link>
      <nav className="flex gap-6">
        {links.map((l) => {
          const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
          return (
            <Link
              key={l.href}
              href={l.href}
              className={
                active
                  ? "font-semibold text-shipa-blue"
                  : "font-medium text-shipa-ink/70 hover:text-shipa-ink"
              }
            >
              {l.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
