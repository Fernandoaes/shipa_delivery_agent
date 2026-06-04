import type { Metadata } from "next";
import { Jost, Geist_Mono } from "next/font/google";
import AutoRefresh from "@/components/AutoRefresh";
import SideRail from "@/components/SideRail";
import "./globals.css";

// Jost = Shipa's brand typeface (verified from shipa.com). Geist Mono for telemetry/data.
const jost = Jost({ subsets: ["latin"], variable: "--font-jost" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: "SHIPA · Command Center",
  description: "Real-time last-mile delivery monitoring",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${jost.variable} ${geistMono.variable}`}>
      <body>
        <AutoRefresh />
        <SideRail />
        <main className="min-h-screen pl-16">{children}</main>
      </body>
    </html>
  );
}
