import type { WorkRecord } from "@/lib/content";

export const locales = ["en", "ar"] as const;
export type Locale = (typeof locales)[number];

export const dirOf = (locale: Locale): "ltr" | "rtl" =>
  locale === "ar" ? "rtl" : "ltr";

/** English stays at `/` (the live URL, its canonical and OG links unchanged);
    Arabic lives at `/ar`. */
export const homePath = (locale: Locale): string =>
  locale === "ar" ? "/ar" : "/";

/** Fills `{name}` placeholders. Messages are plain strings, not functions, so
    they can cross from server components to client ones. */
export function format(
  template: string,
  values: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (_, key) =>
    key in values ? String(values[key]) : `{${key}}`,
  );
}

type Display = Pick<WorkRecord, "title" | "org" | "period" | "summary">;

/** A record's display fields in `locale`; any Arabic field left blank in
    content/ falls back to English. */
export function localize(record: WorkRecord, locale: Locale): Display {
  const ar = locale === "ar" ? record.ar : undefined;
  return {
    title: ar?.title ?? record.title,
    org: ar?.org ?? record.org,
    period: ar?.period ?? record.period,
    summary: ar?.summary ?? record.summary,
  };
}
