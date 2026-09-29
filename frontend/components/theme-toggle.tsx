"use client";

import { useSyncExternalStore } from "react";

type Theme = "system" | "light" | "dark";

const KEY = "theme";
const ORDER: Theme[] = ["system", "light", "dark"];
const LABEL: Record<Theme, string> = {
  system: "System",
  light: "Light",
  dark: "Dark",
};

function read(): Theme {
  try {
    const stored = localStorage.getItem(KEY);
    return stored === "light" || stored === "dark" ? stored : "system";
  } catch {
    return "system";
  }
}

/** Mirrors the inline script in layout.tsx, which sets the first paint. */
function apply(theme: Theme) {
  const dark =
    theme === "dark" ||
    (theme === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  const root = document.documentElement;
  root.classList.toggle("dark", dark);
  root.classList.toggle("light", theme === "light");
}

const listeners = new Set<() => void>();

function subscribe(onChange: () => void) {
  listeners.add(onChange);
  // Another tab changed the choice, or the OS flipped while on "system".
  const media = matchMedia("(prefers-color-scheme: dark)");
  const sync = () => {
    apply(read());
    onChange();
  };
  window.addEventListener("storage", sync);
  media.addEventListener("change", sync);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", sync);
    media.removeEventListener("change", sync);
  };
}

function choose(theme: Theme) {
  try {
    if (theme === "system") localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, theme);
  } catch {
    // Storage blocked: the choice still applies for this page view.
  }
  apply(theme);
  listeners.forEach((notify) => notify());
}

export function ThemeToggle() {
  // The server (and first client render) say "system"; the real choice lands
  // right after hydration, so the markup never mismatches.
  const theme = useSyncExternalStore(subscribe, read, () => "system" as Theme);
  const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];

  return (
    <button
      type="button"
      onClick={() => choose(next)}
      aria-label={`Theme: ${LABEL[theme]}. Switch to ${LABEL[next]}.`}
      className="field-label cursor-pointer rounded-sm px-1 transition-colors hover:text-foreground"
    >
      Theme: {LABEL[theme]}
    </button>
  );
}
