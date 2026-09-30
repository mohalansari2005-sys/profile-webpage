"use client";

import { useSyncExternalStore } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { useI18n } from "@/components/i18n-provider";
import { format } from "@/lib/i18n";
import { iconChip } from "@/lib/icon-chip";

type Theme = "system" | "light" | "dark";

const KEY = "theme";
const ORDER: Theme[] = ["system", "light", "dark"];
const ICON = { system: Monitor, light: Sun, dark: Moon } as const;

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
  const { t } = useI18n();

  const Icon = ICON[theme];
  const label = format(t.theme.aria, {
    current: t.theme[theme],
    next: t.theme[next],
  });

  return (
    <button
      type="button"
      onClick={() => choose(next)}
      aria-label={label}
      title={label}
      data-mode={theme}
      className={iconChip}
    >
      <Icon className="size-4" aria-hidden="true" />
    </button>
  );
}
