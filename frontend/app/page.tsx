import { Hero } from "@/components/sections/hero";
import { About } from "@/components/sections/about";
import { Work } from "@/components/sections/work";
import { Contact } from "@/components/sections/contact";
import { JoinProvider } from "@/components/join-context";

export default function Home() {
  return (
    <main>
      <Hero />
      <About />
      <JoinProvider>
        <Work />
      </JoinProvider>
      <Contact />
    </main>
  );
}
