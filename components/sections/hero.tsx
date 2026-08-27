import type { CSSProperties } from "react";

/** The record's own fields. Labels are attributes, not decoration. */
const fields = [
  { label: "Role", value: "Product Engineer at Majara" },
  { label: "Focus", value: "Computer Information Systems, King Saud University" },
  { label: "Based", value: "Riyadh, Saudi Arabia" },
];

function stagger(ms: number) {
  return { "--stagger": `${ms}ms` } as CSSProperties;
}

export function Hero() {
  return (
    <section className="border-b border-rule">
      <div className="mx-auto w-full max-w-5xl px-6 pt-24 pb-20 sm:pt-32 sm:pb-28">
        <div className="flex items-start gap-5 sm:gap-7">
          {/* The monogram is the record's key. TODO: to use a photo instead,
              drop profile.jpg in /public and replace this div with:
              <img src="/profile.jpg" alt="Mohammed Alansari" className="size-14 sm:size-20 shrink-0 rounded-sm object-cover" /> */}
          <div
            className="field-in mt-1 flex size-14 shrink-0 items-center justify-center rounded-sm bg-foreground sm:size-20"
            style={stagger(0)}
            aria-hidden="true"
          >
            <span
              className="font-display text-xl font-semibold tracking-tight text-background sm:text-3xl"
              style={{ fontStretch: "88%" }}
            >
              MA
            </span>
          </div>

          <h1
            className="field-in font-display text-[clamp(2.75rem,11vw,6.5rem)] leading-[0.86] font-extrabold tracking-[-0.035em]"
            style={{ ...stagger(60), fontStretch: "85%" }}
          >
            Mohammed
            <br />
            Alansari
          </h1>
        </div>

        <div
          className="rule-draw mt-12 h-px bg-foreground sm:mt-16"
          style={stagger(220)}
        />

        <dl className="grid">
          {fields.map((field, index) => (
            <div
              key={field.label}
              className="field-in grid gap-1 border-b border-rule py-4 sm:grid-cols-[7.5rem_1fr] sm:gap-6 sm:py-5"
              style={stagger(300 + index * 90)}
            >
              <dt className="field-label sm:pt-1.5">{field.label}</dt>
              <dd className="text-lg text-balance sm:text-xl">
                {field.label === "Based" ? (
                  <span className="flex items-baseline gap-2.5">
                    <span
                      className="size-2 shrink-0 translate-y-[-0.15em] rounded-full bg-signal"
                      aria-hidden="true"
                    />
                    {field.value}
                  </span>
                ) : (
                  field.value
                )}
              </dd>
            </div>
          ))}
        </dl>

        <p
          className="field-in mt-10 max-w-2xl text-lg leading-relaxed text-balance sm:text-xl"
          style={stagger(600)}
        >
          Computer Information Systems student at King Saud University,
          building backend systems, data pipelines, and AI-enabled
          applications.
        </p>

        <div className="field-in mt-9" style={stagger(700)}>
          <a
            href="#about"
            className="group inline-flex items-center gap-3 rounded-sm bg-foreground px-5 py-3 text-background transition-colors hover:bg-signal"
          >
            <span className="font-mono text-xs font-medium tracking-[0.14em] uppercase">
              See where the work connects
            </span>
            <span
              className="transition-transform group-hover:translate-y-0.5"
              aria-hidden="true"
            >
              ↓
            </span>
          </a>
        </div>
      </div>
    </section>
  );
}
