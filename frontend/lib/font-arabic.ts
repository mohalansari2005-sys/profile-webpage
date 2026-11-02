import { IBM_Plex_Sans_Arabic } from "next/font/google";

// Only the /ar layout applies it. It is not a variable font, hence the explicit
// weights (regular body, semibold and bold headings). The latin subset keeps
// Latin names inside Arabic text in the same family instead of falling back to
// another face.
//
// Preloaded, on /ar only. Next preloads the fonts in a page's stylesheets, and
// nothing in the English layout imports this file: `/` used to preload Plex
// too because Turbopack's default CSS chunking merged these @font-face rules
// into the stylesheet both layouts share. next.config.ts keeps them apart.
const plexArabic = IBM_Plex_Sans_Arabic({
  variable: "--font-arabic",
  subsets: ["arabic", "latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const arabicFontClass = plexArabic.variable;
