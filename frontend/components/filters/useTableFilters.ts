"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

// Uses useSearchParams: any component calling this must sit inside a <Suspense>
// boundary, or static rendering of its page fails the Next build.
export function useTableFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const get = useCallback((key: string) => params.get(key) ?? "", [params]);

  const set = useCallback(
    (key: string, value: string) => {
      const next = new URLSearchParams(params.toString());
      if (value) next.set(key, value);
      else next.delete(key);
      router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    },
    [params, pathname, router],
  );

  return { get, set };
}

// Generic client-side filter: case-insensitive text match across `textFields`,
// plus exact-match for each provided equality filter.
export function applyFilters<T>(
  rows: T[],
  opts: {
    query: string;
    textFields: (keyof T)[];
    equals?: Partial<Record<keyof T, string>>;
    predicate?: (row: T) => boolean;
  },
): T[] {
  const q = opts.query.trim().toLowerCase();
  return rows.filter((row) => {
    if (opts.predicate && !opts.predicate(row)) return false;
    for (const [k, v] of Object.entries(opts.equals ?? {})) {
      if (v && String((row as Record<string, unknown>)[k] ?? "") !== v) return false;
    }
    if (!q) return true;
    return opts.textFields.some((f) =>
      String(row[f] ?? "").toLowerCase().includes(q),
    );
  });
}

export function optionsFor<T>(rows: T[], field: keyof T): string[] {
  return Array.from(new Set(rows.map((r) => String(r[field] ?? "")).filter(Boolean))).sort();
}
