"use client";

import type { MouseEvent } from "react";
import { useI18n } from "@/components/i18n-provider";
import { homePath, type Locale } from "@/lib/i18n";

/** A plain link to the other language's page (a full navigation: the two
    languages are separate root layouts). It remembers the choice, so a
    reader who picked Arabic is sent to /ar when they return to `/`, and it
    carries the current #section across. */
export function LanguageToggle() {
  const { locale, t } = useI18n();
  const other: Locale = locale === "ar" ? "en" : "ar";

  function onClick(event: MouseEvent<HTMLAnchorElement>) {
    try {
      localStorage.setItem("lang", other);
    } catch {
      // Storage blocked: the link still works, it just isn't remembered.
    }
    if (location.hash) {
      event.currentTarget.href = homePath(other) + location.hash;
    }
  }

  return (
    <a
      href={homePath(other)}
      hrefLang={other}
      lang={other}
      onClick={onClick}
      aria-label={t.lang.switchAria}
      className="cursor-pointer rounded-sm border border-rule bg-foreground/[0.04] px-2.5 py-1.5 font-mono text-xs tracking-[0.04em] whitespace-nowrap text-foreground transition-colors duration-200 hover:border-foreground"
    >
      {t.lang.switchLabel}
    </a>
  );
}
