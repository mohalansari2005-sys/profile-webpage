import { Reveal } from "@/components/reveal";

const links = [
  {
    label: "Email",
    value: "moh.alansari2005@gmail.com",
    href: "mailto:moh.alansari2005@gmail.com",
  },
  {
    label: "GitHub",
    value: "github.com/mohalansari2005-sys",
    href: "https://github.com/mohalansari2005-sys",
  },
  {
    label: "LinkedIn",
    value: "linkedin.com/in/mohammed-m-al-ansari",
    href: "https://www.linkedin.com/in/mohammed-m-al-ansari",
  },
];

export function Contact() {
  return (
    <footer id="contact">
      <div className="mx-auto grid w-full max-w-5xl gap-8 px-6 py-20 sm:py-28 md:grid-cols-[7.5rem_1fr] md:gap-6">
        <Reveal>
          <h2 className="field-label md:pt-2.5">Contact</h2>
        </Reveal>

        <div className="max-w-2xl">
          <Reveal delay={80}>
            <p
              className="font-display text-2xl leading-[1.15] font-semibold tracking-tight text-balance sm:text-4xl"
              style={{ fontStretch: "88%" }}
            >
              If any of this connects to what you&rsquo;re building, I&rsquo;d
              like to hear about it.
            </p>
          </Reveal>

          <dl className="mt-10">
            {links.map((link, index) => (
              <Reveal key={link.label} delay={160 + index * 70}>
                <div className="grid gap-1 border-t border-rule py-4 sm:grid-cols-[7.5rem_1fr] sm:gap-6">
                  <dt className="field-label sm:pt-1">{link.label}</dt>
                  <dd>
                    <a
                      href={link.href}
                      className="rounded-sm underline decoration-rule decoration-1 underline-offset-4 transition-colors hover:decoration-signal hover:text-signal"
                    >
                      {link.value}
                    </a>
                  </dd>
                </div>
              </Reveal>
            ))}
          </dl>

          <p className="mt-12 font-mono text-[0.6875rem] tracking-[0.1em] text-dim uppercase">
            Mohammed Alansari — 2026
          </p>
        </div>
      </div>
    </footer>
  );
}
