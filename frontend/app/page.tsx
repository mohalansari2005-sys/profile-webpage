import { Hero } from "@/components/sections/hero";
import { About } from "@/components/sections/about";
import { Work } from "@/components/sections/work";
import { Ask } from "@/components/sections/ask";
import { Contact } from "@/components/sections/contact";
import { JoinProvider } from "@/components/join-context";

// Inlined at build time. Unset — which is production today — means the section
// is never rendered, so the live site's markup and behaviour are unchanged
// until a backend exists for it to talk to.
//
// Note this gates rendering, not bundling: Turbopack keeps ask.tsx in a chunk
// either way, including behind a conditional next/dynamic import. The module
// is then unreachable dead code — no markup, no fetch, and nothing to
// configure it with, since NEXT_PUBLIC_CHAT_API_URL is what is missing.
const chatEnabled = Boolean(process.env.NEXT_PUBLIC_CHAT_API_URL);

export default function Home() {
  return (
    <main>
      <Hero />
      <About />
      <JoinProvider>
        <Work />
        {chatEnabled && <Ask />}
      </JoinProvider>
      <Contact />
    </main>
  );
}
