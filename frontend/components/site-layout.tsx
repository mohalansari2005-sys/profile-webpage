import type { ReactNode } from "react";
import { SiteHead } from "@/components/site-head";
import { baseFontClass } from "@/lib/fonts";
import { dirOf, type Locale } from "@/lib/i18n";
import "@/app/globals.css";

/** The <html> shell for one language. Each language is its own root layout
    (app/(en) and app/(ar)) that renders this, so `lang` and `dir` are on the
    element from the first byte of HTML, with no client-side switch. */
export function SiteLayout({
  locale,
  fontClass = "",
  children,
}: {
  locale: Locale;
  /** Extra font variables for this language (the Arabic face on /ar). */
  fontClass?: string;
  children: ReactNode;
}) {
  return (
    <html
      lang={locale}
      dir={dirOf(locale)}
      suppressHydrationWarning
      className={`${baseFontClass} ${fontClass} h-full antialiased`}
    >
      {/* eslint-disable-next-line @next/next/no-head-element -- this is the app-router root shell, where <head> is correct; the rule only knows layout.tsx */}
      <head>
        <SiteHead restoreArabic={locale === "en"} />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
