import { Reveal } from "@/components/reveal";

export function About() {
  return (
    <section id="about" className="border-b border-rule bg-surface-raised">
      <div className="mx-auto grid w-full max-w-5xl gap-8 px-6 py-20 sm:py-28 md:grid-cols-[7.5rem_1fr] md:gap-6">
        <Reveal>
          <h2 className="field-label md:pt-2.5">About</h2>
        </Reveal>

        <div className="max-w-2xl">
          <Reveal delay={80}>
            <p className="text-lg leading-relaxed sm:text-xl">
              I build full-stack software from the problem up, turning ideas
              and real-world needs into products people can actually use.
            </p>
          </Reveal>

          <Reveal delay={160}>
            <blockquote className="my-9 border-l-2 border-foreground pl-6">
              <p
                className="font-display text-2xl leading-[1.2] font-semibold tracking-tight text-balance sm:text-3xl"
                style={{ fontStretch: "90%" }}
              >
                Not just &ldquo;How do we build this?&rdquo; but &ldquo;Why
                does it matter?&rdquo; and &ldquo;Who does it help?&rdquo;
              </p>
            </blockquote>
          </Reveal>

          <Reveal delay={240}>
            <p className="text-lg leading-relaxed text-dim sm:text-xl">
              I work from the requirements up, translating business needs
              into structured requirements, and rapidly prototyping and
              iterating until the idea becomes working software. I also
              explore AI and agentic systems through hands-on projects.
            </p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
