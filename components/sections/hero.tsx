import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
      <Avatar size="lg" className="size-24">
        <AvatarImage src="/profile.jpg" alt="Mohammed Alansari" />
        <AvatarFallback className="text-xl">MA</AvatarFallback>
      </Avatar>

      <div className="flex flex-col gap-3">
        <h1 className="font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
          Mohammed Alansari
        </h1>
        <p className="text-lg font-medium text-primary">
          Product Engineering Intern / Aspiring Software Engineer
        </p>
        <p className="mx-auto max-w-xl text-balance text-muted-foreground">
          Information Systems student specializing in Data Science &amp;
          Management, passionate about building at the intersection of
          technology, AI, data, and business.
        </p>
      </div>

      <div className="flex flex-col items-center gap-2">
        <Button render={<a href="#about" />} nativeButton={false}>
          Explore my work, experience, and journey below
        </Button>
      </div>
    </section>
  );
}
