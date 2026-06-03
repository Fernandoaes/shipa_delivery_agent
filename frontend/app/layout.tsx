import type { Metadata } from "next";
import AutoRefresh from "@/components/AutoRefresh";
import TopBar from "@/components/TopBar";
import "./globals.css";

export const metadata: Metadata = {
  title: "SHIPA Ops Dashboard",
  description: "Orders, customers, and delivery map",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AutoRefresh />
        <TopBar />
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
