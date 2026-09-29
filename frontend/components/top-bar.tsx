import { ThemeToggle } from "@/components/theme-toggle";

/** Site-wide controls. Absolutely positioned over the hero's top padding, so it
    adds nothing to the layout and scrolls away with the page. */
export function TopBar() {
  return (
    <header className="absolute inset-x-0 top-0 z-10">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-end gap-4 px-6 pt-6">
        <ThemeToggle />
      </div>
    </header>
  );
}
