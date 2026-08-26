import { Separator } from "@/components/ui/separator";

export function About() {
  return (
    <section id="about" className="mx-auto max-w-2xl px-6 py-24">
      <h2 className="font-heading text-2xl font-semibold tracking-tight">
        About Me
      </h2>
      <Separator className="my-6" />
      <div className="flex flex-col gap-4 text-muted-foreground">
        <p>
          I enjoy turning ideas and real-world problems into practical
          products, from developing full-stack applications to exploring
          AI-powered solutions. My experience spans software development,
          data, product thinking, and client-facing work, which has shaped
          how I approach technology: not just by asking &ldquo;How do we
          build this?&rdquo; but also &ldquo;Why does it matter, and who does
          it help?&rdquo;
        </p>
        <p>
          I&rsquo;m currently focused on growing as a software and AI
          engineer, building real-world projects, and learning how to use
          data and technology to create meaningful impact.
        </p>
      </div>
    </section>
  );
}
