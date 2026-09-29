"use client";

import { useSyncExternalStore } from "react";
import { useI18n } from "@/components/i18n-provider";
import { homePath, type Locale } from "@/lib/i18n";

function subscribe(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

/** A plain link to the other language's page (a full navigation: the two
    languages are separate root layouts).

    The current #section rides in the href itself, and the choice rides in the
    URL (`?lang=en` on the way to English), so both survive middle-click and
    "open in new tab", which never fire a click handler. The English page reads
    `?lang=en` to remember English; /ar remembers Arabic on load (see
    components/site-head.tsx). */
export function LanguageToggle() {
  const { locale, t } = useI18n();
  const other: Locale = locale === "ar" ? "en" : "ar";
  // "" on the server and first client render, so the markup never mismatches.
  const hash = useSyncExternalStore(subscribe, () => location.hash, () => "");
  const href = homePath(other) + (other === "en" ? "?lang=en" : "") + hash;

  return (
    <a
      href={href}
      hrefLang={other}
      lang={other}
      aria-label={t.lang.switchAria}
      className="cursor-pointer rounded-sm border border-rule bg-foreground/[0.04] px-2.5 py-1.5 font-mono text-xs tracking-[0.04em] whitespace-nowrap text-foreground transition-colors duration-200 hover:border-foreground"
    >
      {t.lang.switchLabel}
    </a>
  );
}
