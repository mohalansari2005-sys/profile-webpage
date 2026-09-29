import { Reveal } from "@/components/reveal";
import type { Messages } from "@/messages";

export function About({ t }: { t: Messages["about"] }) {
  return (
    <section id="about" className="border-b border-rule bg-surface-raised">
      <div className="mx-auto grid w-full max-w-5xl gap-8 px-6 py-20 sm:py-28 md:grid-cols-[7.5rem_1fr] md:gap-6">
        <Reveal>
          <h2 className="field-label md:pt-2.5">{t.label}</h2>
        </Reveal>

        <div className="max-w-2xl">
          <Reveal delay={80}>
            <p className="text-lg leading-relaxed sm:text-xl">
              {t.intro}
            </p>
          </Reveal>

          <Reveal delay={160}>
            <blockquote className="my-9 border-s-2 border-foreground ps-6">
              <p
                className="font-display text-2xl leading-[1.2] font-semibold tracking-tight text-balance sm:text-3xl"
                style={{ fontStretch: "90%" }}
              >
                {t.quote}
              </p>
            </blockquote>
          </Reveal>

          <Reveal delay={240}>
            <p className="text-lg leading-relaxed text-dim sm:text-xl">
              {t.body}
            </p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
