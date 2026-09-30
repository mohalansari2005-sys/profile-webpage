# Icon toggles for language and theme

## Why
The two top-bar controls were text chips ("Theme: System", "العربية"). On a phone they were wide and cramped; the owner asked for icons — a translate icon for language and sun/moon for theme — taken from an existing icon set, not drawn by hand.

## What
- **Icons:** `lucide-react` (already a dependency, the same family as the GitHub/email marks; no new dependency, nothing hand-drawn): `Languages` for the language switch; `Monitor` / `Sun` / `Moon` for the theme's system / light / dark states. The cycle is unchanged (system -> light -> dark); the monitor is kept for "system" so the third state has an honest icon rather than being hidden.
- **Chip:** `lib/icon-chip.ts` holds the one class both controls share — the skill chips' border and fill, square, 44px on phones (touch target) and 36px from `sm` up.
- **Accessibility:** the visible text is gone, so each control keeps its full accessible name and a tooltip (`title`) from the message dictionaries: "Theme: Dark. Switch to System." / "Switch to Arabic" / their Arabic equivalents. The now-unused `theme.label` and `lang.switchLabel` message keys were removed from both dictionaries. The icon is `aria-hidden`.
- **Unchanged:** the language link's `href` still carries the `#section` and `?lang=en`; the theme storage and no-flash script.

## Tests
`theme.spec.ts`: the toggle has no visible text, its aria-label and icon (`lucide-monitor` -> `lucide-sun` -> `lucide-moon`) follow the cycle, the cycle and persistence still hold. `i18n.spec.ts`: the language link is an icon (`lucide-languages`, no text); the Arabic theme label is asserted on `aria-label`. Full suite 49 tests x3 repeats.
