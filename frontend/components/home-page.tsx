import { About } from "@/components/sections/about";
import { Ask } from "@/components/sections/ask";
import { Contact } from "@/components/sections/contact";
import { Hero } from "@/components/sections/hero";
import { Work } from "@/components/sections/work";
import { I18nProvider } from "@/components/i18n-provider";
import { JoinProvider } from "@/components/join-context";
import { TopBar } from "@/components/top-bar";
import type { Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";

// Inlined at build time. Unset — which is production today — means the section
// is never rendered, so the live site's markup and behaviour are unchanged
// until a backend exists for it to talk to.
//
// Note this gates rendering, not bundling: Turbopack keeps ask.tsx in a chunk
// either way, including behind a conditional next/dynamic import. The module
// is then unreachable dead code — no markup, no fetch, and nothing to
// configure it with, since NEXT_PUBLIC_CHAT_API_URL is what is missing.
const chatEnabled = Boolean(process.env.NEXT_PUBLIC_CHAT_API_URL);

/** The whole page in one language; both routes render this. */
export function HomePage({ locale }: { locale: Locale }) {
  const t = getMessages(locale);
  return (
    <I18nProvider locale={locale} messages={t}>
      <main className="relative">
        <TopBar />
        <Hero t={t.hero} />
        <About t={t.about} />
        <JoinProvider>
          <Work />
          {chatEnabled && <Ask />}
        </JoinProvider>
        <Contact t={t.contact} />
      </main>
    </I18nProvider>
  );
}
